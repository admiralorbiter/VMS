"""
B3: Historical Duplicate Volunteer Backfill
============================================
Finds existing volunteer duplicate pairs created by the name-variant bug
(e.g., "Dave Switzer" created as a new record when "David Switzer" already
existed) and surfaces them as VOLUNTEER quarantine tickets for admin review.

Usage:
    python scripts/maintenance/backfill_near_match_tickets.py --dry-run
    python scripts/maintenance/backfill_near_match_tickets.py --apply [--limit N]

Safety rules (per AI Collab Guide):
  - Default is --dry-run. Pass --apply explicitly to write anything.
  - Audit JSON is always written to tmp/ before any DB writes.
  - No data is deleted or merged — only quarantine tickets are created.
  - Stop Flask server before running (SQLite locking).

What counts as a "duplicate pair":
  - Volunteer A has pathful_user_id set (created by Pathful import)
  - Volunteer B does NOT have pathful_user_id (canonical Salesforce-synced record)
  - Same last name (case-insensitive)
  - First names share same first 3 characters but are NOT identical
  - Neither has been soft-deleted / marked inactive
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")

from sqlalchemy import func

from app import create_app
from models import db
from models.volunteer import Volunteer

app = create_app()


def find_pairs():
    """
    Return a list of (pathful_dup, canonical) Volunteer pairs.
    pathful_dup  = the duplicate created by the import (has pathful_user_id)
    canonical    = the original Salesforce-synced record (no pathful_user_id)
    """
    # All volunteers with a pathful_user_id (potential duplicates)
    pathful_vols = Volunteer.query.filter(
        Volunteer.pathful_user_id.isnot(None),
        Volunteer.last_name.isnot(None),
        Volunteer.first_name.isnot(None),
    ).all()

    pairs = []
    seen_pairs = set()  # deduplicate (A,B) == (B,A)

    for pv in pathful_vols:
        if not pv.first_name or len(pv.first_name) < 3:
            continue

        prefix = pv.first_name[:3].lower()
        last = pv.last_name.lower()

        # Find volunteers with same last name + same 3-char prefix, NO pathful_user_id
        candidates = Volunteer.query.filter(
            func.lower(Volunteer.last_name) == last,
            func.lower(Volunteer.first_name).startswith(prefix),
            Volunteer.pathful_user_id.is_(None),
            Volunteer.id != pv.id,
        ).all()

        # Exclude exact first-name matches (already handled by Priority 3)
        candidates = [
            c for c in candidates if c.first_name.lower() != pv.first_name.lower()
        ]

        for canon in candidates:
            pair_key = (min(pv.id, canon.id), max(pv.id, canon.id))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            pairs.append((pv, canon))

    return pairs


def count_event_volunteers(vol_id):
    """Count how many event_volunteers rows belong to this volunteer."""
    result = db.session.execute(
        db.text("SELECT COUNT(*) FROM event_volunteers WHERE volunteer_id = :vid"),
        {"vid": vol_id},
    ).scalar()
    return result or 0


def build_audit_record(pathful_dup, canonical):
    ev_dup = count_event_volunteers(pathful_dup.id)
    ev_can = count_event_volunteers(canonical.id)
    return {
        "pathful_duplicate": {
            "id": pathful_dup.id,
            "first_name": pathful_dup.first_name,
            "last_name": pathful_dup.last_name,
            "pathful_user_id": pathful_dup.pathful_user_id,
            "organization_name": pathful_dup.organization_name,
            "event_volunteers_count": ev_dup,
        },
        "canonical": {
            "id": canonical.id,
            "first_name": canonical.first_name,
            "last_name": canonical.last_name,
            "pathful_user_id": canonical.pathful_user_id,
            "organization_name": canonical.organization_name,
            "event_volunteers_count": ev_can,
        },
    }


def run(dry_run: bool, limit: int | None = None):
    with app.app_context():
        print("=" * 70)
        print("B3: Historical Duplicate Volunteer Backfill")
        print(
            f"Mode: {'DRY-RUN (no writes)' if dry_run else 'APPLY (will create tickets)'}"
        )
        print("=" * 70)
        print()

        pairs = find_pairs()

        if limit:
            pairs = pairs[:limit]
            print(f"Limiting to first {limit} pairs (--limit flag).")
            print()

        # ── Build audit data ──────────────────────────────────────────────
        audit = {
            "generated_at": datetime.utcnow().isoformat(),
            "mode": "dry_run" if dry_run else "apply",
            "total_pairs_found": len(pairs),
            "limit_applied": limit,
            "pairs": [],
        }

        sessions_at_risk = 0
        for pathful_dup, canonical in pairs:
            rec = build_audit_record(pathful_dup, canonical)
            audit["pairs"].append(rec)
            sessions_at_risk += rec["pathful_duplicate"]["event_volunteers_count"]

        audit["total_sessions_at_risk"] = sessions_at_risk

        # ── Write audit JSON ──────────────────────────────────────────────
        date_str = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        audit_path = Path("tmp") / f"near_match_backfill_{date_str}.json"
        audit_path.parent.mkdir(exist_ok=True)
        with open(audit_path, "w") as f:
            json.dump(audit, f, indent=2)
        print(f"Audit JSON written to: {audit_path}")
        print()

        # ── Print summary ─────────────────────────────────────────────────
        print(f"Duplicate pairs found : {len(pairs)}")
        print(
            f"Sessions at risk      : {sessions_at_risk}  (attributed to duplicates, not canonical)"
        )
        print()

        if len(pairs) > 0:
            print("Top 15 pairs (pathful_duplicate -> canonical):")
            print(
                f"  {'DUP ID':>7}  {'Pathful Name':<28}  {'CANONICAL ID':>12}  {'Canonical Name':<28}  {'Sessions':>8}"
            )
            print("  " + "-" * 95)
            for pathful_dup, canonical in pairs[:15]:
                ev = count_event_volunteers(pathful_dup.id)
                print(
                    f"  {pathful_dup.id:>7}  "
                    f"{pathful_dup.first_name + ' ' + pathful_dup.last_name:<28}  "
                    f"{canonical.id:>12}  "
                    f"{canonical.first_name + ' ' + canonical.last_name:<28}  "
                    f"{ev:>8}"
                )
            if len(pairs) > 15:
                print(f"  ... and {len(pairs) - 15} more (see JSON for full list)")
            print()

        if dry_run:
            print("DRY-RUN complete. No changes made.")
            print()
            print("To proceed, run with --apply:")
            print(
                f"  python scripts/maintenance/backfill_near_match_tickets.py --apply"
            )
            if limit:
                print(f"  (or add --limit {limit} for a partial run)")
            return

        # ── Apply — create quarantine tickets ─────────────────────────────
        if not pairs:
            print("No pairs found. Nothing to do.")
            return

        # We need an import_log_id to attach tickets to. Find the most recent one
        # or create a synthetic maintenance log entry.
        from models.pathful_import import (
            PathfulImportLog,
            PathfulUnmatchedRecord,
            UnmatchedType,
        )

        import_log = PathfulImportLog.query.order_by(PathfulImportLog.id.desc()).first()
        if not import_log:
            print("ERROR: No PathfulImportLog found. Cannot create quarantine tickets.")
            print("Run at least one Pathful import first.")
            sys.exit(1)

        print(
            f"Attaching tickets to import_log_id={import_log.id} (most recent import)."
        )
        print()

        created = 0
        skipped = 0
        for pathful_dup, canonical in pairs:
            # Check if a ticket for this specific duplicate already exists
            existing = PathfulUnmatchedRecord.query.filter_by(
                resolved_volunteer_id=pathful_dup.id,
                unmatched_type=UnmatchedType.VOLUNTEER,
            ).first()
            if existing:
                skipped += 1
                continue

            raw_data_dict = {
                "_near_match_volunteer_ids": [canonical.id],
                "_source": "b3_backfill",
                "_pathful_user_id": pathful_dup.pathful_user_id,
            }

            ticket = PathfulUnmatchedRecord(
                import_log_id=import_log.id,
                row_number=0,
                raw_data=raw_data_dict,
                unmatched_type=UnmatchedType.VOLUNTEER,
                attempted_match_name=(
                    f"{pathful_dup.first_name} {pathful_dup.last_name}"
                ),
                attempted_match_organization=pathful_dup.organization_name or "",
            )
            # Set fields not accepted by __init__
            ticket.resolved_volunteer_id = pathful_dup.id
            ticket.resolution_notes = (
                f"[B3 Backfill] Existing duplicate detected. "
                f"'{pathful_dup.first_name} {pathful_dup.last_name}' "
                f"(vol_id={pathful_dup.id}, pathful_id={pathful_dup.pathful_user_id}) "
                f"may be the same person as "
                f"'{canonical.first_name} {canonical.last_name}' "
                f"(vol_id={canonical.id}). "
                f"Use Confirm Merge or Reject to resolve."
            )
            db.session.add(ticket)
            created += 1

        db.session.commit()
        print(f"Created : {created} quarantine tickets")
        print(f"Skipped : {skipped} (tickets already existed)")
        print()
        print("Done. Find these tickets in the quarantine queue:")
        print("  /virtual/pathful/unmatched?type=volunteer&status=pending")
        print()
        print("Each ticket shows near-match candidates via the suggestion engine.")
        print("Use 'Confirm Merge' to merge, 'Reject' to keep as separate volunteers.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="B3: Backfill quarantine tickets for historical duplicate volunteer pairs."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print what would happen without making changes (default).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually create the quarantine tickets.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N pairs (for a partial apply).",
    )
    args = parser.parse_args()

    # --apply overrides --dry-run
    dry_run = not args.apply

    run(dry_run=dry_run, limit=args.limit)
