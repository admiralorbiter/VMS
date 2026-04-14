import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app, db
from models.organization import Organization, OrganizationAlias, VolunteerOrganization
from models.pathful_import import PathfulUnmatchedRecord


def run_backfill(dry_run=True):
    """
    Phase 6 Backfill: Retroactively register OrganizationAlias records from
    historical Pathful imports that were resolved manually or via data fixes.

    For each resolved PathfulUnmatchedRecord where:
      - unmatched_type = 'volunteer'
      - attempted_match_organization is not null
      - resolution_status = 'resolved'
      - resolved_volunteer_id is not null

    We look up the volunteer's linked Organization and, if the raw CSV string
    differs from the canonical name, register it as an OrganizationAlias so
    future imports resolve automatically.

    Args:
        dry_run (bool): If True, print what would happen without writing to DB.
                        Set to False to actually commit changes.
    """
    app = create_app()
    with app.app_context():
        print(
            f"{'[DRY RUN] ' if dry_run else ''}Starting Phase 6 Org Alias Backfill...\n"
        )

        # Fetch all resolved volunteer unmatched records that have an org string
        records = PathfulUnmatchedRecord.query.filter(
            PathfulUnmatchedRecord.unmatched_type == "volunteer",
            PathfulUnmatchedRecord.resolution_status == "resolved",
            PathfulUnmatchedRecord.attempted_match_organization.isnot(None),
            PathfulUnmatchedRecord.resolved_volunteer_id.isnot(None),
        ).all()

        print(f"Found {len(records)} resolved volunteer records with org strings.\n")

        registered = 0
        skipped_exact = 0
        skipped_already_exists = 0
        skipped_no_org_link = 0

        for record in records:
            raw_string = record.attempted_match_organization.strip()
            if not raw_string:
                continue

            # Find the volunteer's linked organization (primary preferred)
            vol_org = VolunteerOrganization.query.filter_by(
                volunteer_id=record.resolved_volunteer_id, is_primary=True
            ).first()
            if not vol_org:
                # Fall back to any org link
                vol_org = VolunteerOrganization.query.filter_by(
                    volunteer_id=record.resolved_volunteer_id
                ).first()

            if not vol_org:
                skipped_no_org_link += 1
                continue

            canonical_org = Organization.query.get(vol_org.organization_id)
            if not canonical_org:
                skipped_no_org_link += 1
                continue

            # If the raw string already matches the canonical name exactly, no alias needed
            if raw_string.lower() == canonical_org.name.strip().lower():
                skipped_exact += 1
                continue

            # Check if an alias already exists for this string
            existing = OrganizationAlias.query.filter(
                db.func.lower(OrganizationAlias.name) == raw_string.lower()
            ).first()
            if existing:
                skipped_already_exists += 1
                continue

            # Register the alias
            print(
                f"  {'[DRY RUN] Would register' if dry_run else 'Registering'}: "
                f"'{raw_string}' -> '{canonical_org.name}' (ID {canonical_org.id})"
            )

            if not dry_run:
                new_alias = OrganizationAlias(
                    name=raw_string,
                    organization_id=canonical_org.id,
                    is_auto_generated=True,
                )
                db.session.add(new_alias)

            registered += 1

        if not dry_run:
            db.session.commit()

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Complete!")
        print(f"  Would register / Registered : {registered}")
        print(f"  Skipped (exact name match)  : {skipped_exact}")
        print(f"  Skipped (alias exists)      : {skipped_already_exists}")
        print(f"  Skipped (no org link found) : {skipped_no_org_link}")

        if dry_run and registered > 0:
            print(
                f"\nRun with --commit to apply {registered} alias registration(s) to the database."
            )


if __name__ == "__main__":
    commit = "--commit" in sys.argv
    if commit:
        print("⚠️  Running in COMMIT mode. Changes will be written to the database.")
        confirm = input("Type 'yes' to continue: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    run_backfill(dry_run=not commit)
