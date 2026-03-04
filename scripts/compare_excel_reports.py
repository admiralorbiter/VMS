"""
Compare KCKPS Teacher Progress data across multiple sources.

Compares:
  1. Two Teacher Progress Excel exports (production vs dev)
  2. Two Audit Log CSVs (production vs dev manual overrides)
  3. Optionally cross-references against a Pathful Session Report

Usage:
    python compare_excel_reports.py                # uses default file paths
    python compare_excel_reports.py --help          # show options

Outputs a comprehensive difference report to the console and saves it as a
timestamped file in scripts/data/.
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl is required. Install with:  pip install openpyxl")
    sys.exit(1)

# ──────────────────────────────────────────────
# Configuration / Defaults
# ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

DEFAULT_PROGRESS_A = os.path.join(
    DATA_DIR,
    "Kansas_City,_KS_(KCKPS)_Public_Schools_Teacher_Progress_2025-2026.xlsx",
)
DEFAULT_PROGRESS_B = os.path.join(
    DATA_DIR,
    "Kansas_City,_KS_(KCKPS)_Public_Schools_Teacher_Progress_2025-2026 (1).xlsx",
)
DEFAULT_AUDIT_A = os.path.join(DATA_DIR, "teacher_usage_audit_log.csv")
DEFAULT_AUDIT_B = os.path.join(DATA_DIR, "teacher_usage_audit_log (1).csv")
DEFAULT_SESSION_REPORT = os.path.join(
    DATA_DIR,
    "Session Report_reports_556de88b-7054-44e9-b20e-c0f90c6110f6.xlsx",
)

# Teacher Progress column indices (0-based)
COL_BUILDING = 0
COL_NAME = 1
COL_EMAIL = 2
COL_GRADE = 3
COL_TARGET = 4
COL_COMPLETED = 5
COL_STATUS = 6
FIELD_NAMES = [
    "Building",
    "Name",
    "Email",
    "Grade",
    "Target Sessions",
    "Completed Sessions",
    "Status",
]


# ──────────────────────────────────────────────
# Data loaders
# ──────────────────────────────────────────────
def load_progress(filepath):
    """Load a Teacher Progress Excel and return {email: row_dict}."""
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    rows = list(ws.rows)
    wb.close()

    data = {}
    duplicates = []
    for row in rows[1:]:
        values = [cell.value for cell in row]
        email = str(values[COL_EMAIL] or "").strip().lower()
        if not email:
            continue
        row_dict = {FIELD_NAMES[i]: values[i] for i in range(len(FIELD_NAMES))}
        if email in data:
            duplicates.append(email)
        data[email] = row_dict
    return data, duplicates


def load_audit_log(filepath):
    """Load an audit log CSV and return list of dicts."""
    if not os.path.exists(filepath):
        return []
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Timestamp (UTC)"):
                entries.append(row)
    return entries


def load_session_report(filepath):
    """Load the Pathful session report and return list of dicts."""
    if not os.path.exists(filepath):
        return []
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    rows = list(ws.rows)
    wb.close()
    if len(rows) < 2:
        return []
    headers = [cell.value for cell in rows[0]]
    data = []
    for row in rows[1:]:
        values = [cell.value for cell in row]
        data.append({headers[i]: values[i] for i in range(len(headers))})
    return data


def safe(val):
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return val
    return str(val).strip()


# ──────────────────────────────────────────────
# Build the report
# ──────────────────────────────────────────────
def build_report(
    progress_a_path, progress_b_path, audit_a_path, audit_b_path, session_path
):
    lines = []

    def out(text=""):
        lines.append(text)

    label_a = os.path.basename(progress_a_path)
    label_b = os.path.basename(progress_b_path)

    out("=" * 90)
    out("  KCKPS Teacher Progress — Comprehensive Comparison Report")
    out(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out("=" * 90)
    out()
    out(f"  Progress A (prod): {label_a}")
    out(f"  Progress B (dev):  {label_b}")
    if audit_a_path:
        out(f"  Audit A (prod):    {os.path.basename(audit_a_path)}")
    if audit_b_path:
        out(f"  Audit B (dev):     {os.path.basename(audit_b_path)}")
    if session_path:
        out(f"  Session Report:    {os.path.basename(session_path)}")
    out()

    # ── Load data ────────────────────────────────
    data_a, dups_a = load_progress(progress_a_path)
    data_b, dups_b = load_progress(progress_b_path)

    audit_a = load_audit_log(audit_a_path) if audit_a_path else []
    audit_b = load_audit_log(audit_b_path) if audit_b_path else []

    sessions = load_session_report(session_path) if session_path else []

    emails_a = set(data_a.keys())
    emails_b = set(data_b.keys())
    common = emails_a & emails_b
    only_a = emails_a - emails_b
    only_b = emails_b - emails_a

    # ══════════════════════════════════════════════
    # PART I — TEACHER PROGRESS COMPARISON
    # ══════════════════════════════════════════════
    out("╔" + "═" * 88 + "╗")
    out("║  PART I: TEACHER PROGRESS COMPARISON" + " " * 51 + "║")
    out("╚" + "═" * 88 + "╝")
    out()

    # ── 1. High-level summary ────────────────────
    out("─" * 90)
    out("  1. HIGH-LEVEL SUMMARY")
    out("─" * 90)
    out(f"  Total teachers in Prod:   {len(data_a)}")
    out(f"  Total teachers in Dev:    {len(data_b)}")
    out(f"  Teachers in both:         {len(common)}")
    out(f"  Only in Prod:             {len(only_a)}")
    out(f"  Only in Dev:              {len(only_b)}")
    out()

    if dups_a:
        out(
            f"  ⚠ Duplicate emails in Prod: {len(dups_a)}  ({', '.join(sorted(dups_a))})"
        )
    if dups_b:
        out(
            f"  ⚠ Duplicate emails in Dev:  {len(dups_b)}  ({', '.join(sorted(dups_b))})"
        )
    if dups_a or dups_b:
        out()

    # ── 2. Status distribution ───────────────────
    out("─" * 90)
    out("  2. STATUS DISTRIBUTION")
    out("─" * 90)
    status_a = Counter(r["Status"] for r in data_a.values())
    status_b = Counter(r["Status"] for r in data_b.values())
    all_statuses = sorted(set(list(status_a) + list(status_b)), key=str)

    out(f"  {'Status':<20s}  {'Prod':>8s}  {'Dev':>8s}  {'Diff':>8s}")
    out(f"  {'─' * 20}  {'─' * 8}  {'─' * 8}  {'─' * 8}")
    for s in all_statuses:
        ca, cb = status_a.get(s, 0), status_b.get(s, 0)
        diff = cb - ca
        marker = "  ◄" if diff != 0 else ""
        out(f"  {str(s):<20s}  {ca:>8d}  {cb:>8d}  {diff:>+8d}{marker}")
    out(
        f"  {'TOTAL':<20s}  {len(data_a):>8d}  {len(data_b):>8d}  {len(data_b) - len(data_a):>+8d}"
    )
    out()

    # ── 3. Completed sessions aggregate ──────────
    out("─" * 90)
    out("  3. COMPLETED SESSIONS AGGREGATE")
    out("─" * 90)
    completed_a = sum(int(r["Completed Sessions"] or 0) for r in data_a.values())
    completed_b = sum(int(r["Completed Sessions"] or 0) for r in data_b.values())
    target_a = sum(int(r["Target Sessions"] or 0) for r in data_a.values())
    target_b = sum(int(r["Target Sessions"] or 0) for r in data_b.values())
    out(
        f"  Completed sessions — Prod: {completed_a}  |  Dev: {completed_b}  |  Diff: {completed_b - completed_a:+d}"
    )
    out(
        f"  Target sessions   — Prod: {target_a}  |  Dev: {target_b}  |  Diff: {target_b - target_a:+d}"
    )
    out()

    # ── 4. Per-building breakdown ────────────────
    out("─" * 90)
    out("  4. PER-BUILDING STATUS BREAKDOWN  (only buildings with differences)")
    out("─" * 90)
    buildings_a = defaultdict(Counter)
    buildings_b = defaultdict(Counter)
    for r in data_a.values():
        buildings_a[r["Building"] or "Unknown"][r["Status"]] += 1
    for r in data_b.values():
        buildings_b[r["Building"] or "Unknown"][r["Status"]] += 1

    all_buildings = sorted(set(list(buildings_a) + list(buildings_b)))
    for bldg in all_buildings:
        ba, bb = buildings_a[bldg], buildings_b[bldg]
        bldg_statuses = sorted(set(list(ba) + list(bb)), key=str)
        if all(ba.get(s, 0) == bb.get(s, 0) for s in bldg_statuses):
            continue
        total_a, total_b = sum(ba.values()), sum(bb.values())
        out(f"\n  📍 {bldg}  (Prod: {total_a}, Dev: {total_b})")
        for s in bldg_statuses:
            ca, cb = ba.get(s, 0), bb.get(s, 0)
            if ca != cb:
                out(
                    f"     {str(s):<20s}  Prod: {ca:>3d}  →  Dev: {cb:>3d}  ({cb - ca:+d})"
                )
    out()

    # ── 5. Teachers only in one file ─────────────
    if only_a or only_b:
        out("─" * 90)
        out("  5. TEACHERS ONLY IN ONE FILE")
        out("─" * 90)
        if only_a:
            out(f"\n  Only in Prod — {len(only_a)} teacher(s):")
            for email in sorted(only_a):
                r = data_a[email]
                out(
                    f"    • {r['Name']:<30s}  {r['Email']:<40s}  [{r['Building']}]  {r['Status']}"
                )
        if only_b:
            out(f"\n  Only in Dev — {len(only_b)} teacher(s):")
            for email in sorted(only_b):
                r = data_b[email]
                out(
                    f"    • {r['Name']:<30s}  {r['Email']:<40s}  [{r['Building']}]  {r['Status']}"
                )
        out()

    # ── 6. Per-teacher field differences ─────────
    out("─" * 90)
    out("  6. PER-TEACHER FIELD DIFFERENCES (matched by email)")
    out("─" * 90)
    diff_fields = [
        "Building",
        "Name",
        "Grade",
        "Target Sessions",
        "Completed Sessions",
        "Status",
    ]
    teachers_with_diffs = []
    for email in sorted(common):
        ra, rb = data_a[email], data_b[email]
        diffs = [
            (f, safe(ra[f]), safe(rb[f]))
            for f in diff_fields
            if safe(ra[f]) != safe(rb[f])
        ]
        if diffs:
            teachers_with_diffs.append((email, ra, diffs))

    if teachers_with_diffs:
        out(
            f"\n  {len(teachers_with_diffs)} teacher(s) with field-level differences:\n"
        )
        for email, ra, diffs in teachers_with_diffs:
            out(f"  ┌─ {ra['Name']}  ({email})  [{ra['Building']}]")
            for field, va, vb in diffs:
                out(f"  │   {field}: {va!r} → {vb!r}")
            out(f"  └{'─' * 65}")
    else:
        out("  No field-level differences found among matched teachers.")
    out()

    # ── 7. Status transition matrix ──────────────
    out("─" * 90)
    out("  7. STATUS TRANSITION MATRIX  (Prod → Dev)")
    out("─" * 90)
    transitions = Counter()
    for email in common:
        sa, sb = data_a[email]["Status"], data_b[email]["Status"]
        if sa != sb:
            transitions[(str(sa), str(sb))] += 1

    if transitions:
        out(f"\n  {'From (Prod)':<20s}  →  {'To (Dev)':<20s}  {'Count':>6s}")
        out(f"  {'─' * 20}     {'─' * 20}  {'─' * 6}")
        for (fr, to), count in sorted(transitions.items(), key=lambda x: -x[1]):
            out(f"  {fr:<20s}  →  {to:<20s}  {count:>6d}")
    else:
        out("  No status transitions detected.")
    out()

    # ══════════════════════════════════════════════
    # PART II — AUDIT LOG COMPARISON
    # ══════════════════════════════════════════════
    if audit_a or audit_b:
        out("╔" + "═" * 88 + "╗")
        out("║  PART II: AUDIT LOG COMPARISON" + " " * 57 + "║")
        out("╚" + "═" * 88 + "╝")
        out()

        # ── 8. Audit summary ────────────────────────
        out("─" * 90)
        out("  8. AUDIT LOG SUMMARY")
        out("─" * 90)
        adds_a = [e for e in audit_a if e.get("Action") == "attendance_override_add"]
        removes_a = [
            e for e in audit_a if e.get("Action") == "attendance_override_remove"
        ]
        adds_b = [e for e in audit_b if e.get("Action") == "attendance_override_add"]
        removes_b = [
            e for e in audit_b if e.get("Action") == "attendance_override_remove"
        ]

        out(f"  {'':30s}  {'Prod':>8s}  {'Dev':>8s}  {'Diff':>8s}")
        out(f"  {'─' * 30}  {'─' * 8}  {'─' * 8}  {'─' * 8}")
        out(
            f"  {'Total audit entries':<30s}  {len(audit_a):>8d}  {len(audit_b):>8d}  {len(audit_b) - len(audit_a):>+8d}"
        )
        out(
            f"  {'attendance_override_add':<30s}  {len(adds_a):>8d}  {len(adds_b):>8d}  {len(adds_b) - len(adds_a):>+8d}"
        )
        out(
            f"  {'attendance_override_remove':<30s}  {len(removes_a):>8d}  {len(removes_b):>8d}  {len(removes_b) - len(removes_a):>+8d}"
        )
        out()

        # ── 9. Entries only in Prod ─────────────────
        def audit_key(entry):
            return (
                entry.get("Timestamp (UTC)", "").strip(),
                entry.get("Teacher", "").strip(),
                entry.get("Event/Session", "").strip(),
                entry.get("Action", "").strip(),
            )

        keys_a = {audit_key(e) for e in audit_a}
        keys_b = {audit_key(e) for e in audit_b}
        only_in_a = keys_a - keys_b
        only_in_b = keys_b - keys_a

        if only_in_a:
            out("─" * 90)
            out(f"  9. AUDIT ENTRIES ONLY IN PROD  ({len(only_in_a)} entries)")
            out("     These manual overrides need to be replicated in dev.")
            out("─" * 90)
            # Get the full entries for display
            only_a_entries = [e for e in audit_a if audit_key(e) in only_in_a]
            only_a_entries.sort(
                key=lambda e: e.get("Timestamp (UTC)", ""), reverse=True
            )
            out()
            for e in only_a_entries:
                action = "➕ ADD" if "add" in e.get("Action", "") else "➖ REMOVE"
                out(f"  {action}  {e.get('Timestamp (UTC)', '')}")
                out(f"    Teacher: {e.get('Teacher', '')}")
                out(f"    Session: {e.get('Event/Session', '')}")
                out(f"    Reason:  {e.get('Reason', '')}")
                out()

        if only_in_b:
            out("─" * 90)
            out(f"  10. AUDIT ENTRIES ONLY IN DEV  ({len(only_in_b)} entries)")
            out("─" * 90)
            only_b_entries = [e for e in audit_b if audit_key(e) in only_in_b]
            only_b_entries.sort(
                key=lambda e: e.get("Timestamp (UTC)", ""), reverse=True
            )
            out()
            for e in only_b_entries:
                action = "➕ ADD" if "add" in e.get("Action", "") else "➖ REMOVE"
                out(f"  {action}  {e.get('Timestamp (UTC)', '')}")
                out(f"    Teacher: {e.get('Teacher', '')}")
                out(f"    Session: {e.get('Event/Session', '')}")
                out(f"    Reason:  {e.get('Reason', '')}")
                out()

        # ── 10. Cross-ref: teachers with diffs vs audit entries ──
        if teachers_with_diffs:
            out("─" * 90)
            out("  11. CROSS-REFERENCE: Teachers with Progress Diffs vs Audit Log")
            out("      Shows whether each teacher's data difference is explained by")
            out("      an audit entry (manual override) or is unexplained.")
            out("─" * 90)
            out()

            # Build lookup: teacher name → audit entries (prod)
            audit_by_teacher_a = defaultdict(list)
            for e in audit_a:
                name = e.get("Teacher", "").strip()
                audit_by_teacher_a[name].append(e)

            audit_by_teacher_b = defaultdict(list)
            for e in audit_b:
                name = e.get("Teacher", "").strip()
                audit_by_teacher_b[name].append(e)

            explained = 0
            unexplained = 0

            for email, ra, diffs in teachers_with_diffs:
                teacher_name = ra["Name"]
                prod_audits = audit_by_teacher_a.get(teacher_name, [])
                dev_audits = audit_by_teacher_b.get(teacher_name, [])

                # Check if any prod-only audits exist for this teacher
                prod_only_for_teacher = [
                    e for e in prod_audits if audit_key(e) in only_in_a
                ]

                if prod_only_for_teacher:
                    explained += 1
                    status_icon = "✅ EXPLAINED (prod-only audit entries exist)"
                elif prod_audits and not dev_audits:
                    explained += 1
                    status_icon = "✅ EXPLAINED (audit entries in prod only)"
                elif prod_audits or dev_audits:
                    status_icon = "⚠️  PARTIAL (audit entries exist in both, may differ)"
                    unexplained += 1
                else:
                    unexplained += 1
                    status_icon = "❓ UNEXPLAINED (no audit entries found)"

                out(f"  {teacher_name:<35s}  {status_icon}")
                for field, va, vb in diffs:
                    out(f"    {field}: {va!r} → {vb!r}")
                if prod_only_for_teacher:
                    for e in prod_only_for_teacher:
                        action_label = (
                            "ADD" if "add" in e.get("Action", "") else "REMOVE"
                        )
                        out(
                            f"    └ Prod audit: {action_label} — {e.get('Event/Session', '')}"
                        )
                        out(f"      Reason: {e.get('Reason', '')}")
                out()

            out(f"  Summary: {explained} explained, {unexplained} unexplained/partial")
            out()

    # ══════════════════════════════════════════════
    # PART III — SESSION REPORT CONTEXT (if provided)
    # ══════════════════════════════════════════════
    if sessions:
        out("╔" + "═" * 88 + "╗")
        out("║  PART III: SESSION REPORT CONTEXT" + " " * 54 + "║")
        out("╚" + "═" * 88 + "╝")
        out()

        out("─" * 90)
        out("  12. SESSION REPORT OVERVIEW")
        out("─" * 90)
        out(f"  Total session registrations: {len(sessions)}")

        # Filter to KCKPS sessions
        kckps_sessions = [
            s
            for s in sessions
            if s.get("District or Company")
            and "KCKPS" in str(s.get("District or Company", "")).upper()
            or "KANSAS CITY" in str(s.get("District or Company", "")).upper()
        ]
        out(f"  KCKPS-related registrations: {len(kckps_sessions)}")

        # Status breakdown
        session_statuses = Counter(str(s.get("Status", "")) for s in kckps_sessions)
        if session_statuses:
            out(f"\n  KCKPS Session Status Breakdown:")
            for stat, count in sorted(session_statuses.items(), key=lambda x: -x[1]):
                out(f"    {stat:<30s}  {count:>6d}")

        # Educator-role registrations
        educators = [
            s
            for s in kckps_sessions
            if str(s.get("SignUp Role", "")).lower() == "educator"
        ]
        out(f"\n  KCKPS Educator registrations: {len(educators)}")

        if educators:
            educator_status = Counter(str(s.get("Status", "")) for s in educators)
            for stat, count in sorted(educator_status.items(), key=lambda x: -x[1]):
                out(f"    {stat:<30s}  {count:>6d}")

        # For teachers with differences, look up their sessions
        if teachers_with_diffs:
            out()
            out("─" * 90)
            out("  13. SESSION DETAILS FOR TEACHERS WITH DIFFERENCES")
            out("      Shows the actual sessions from Pathful for each teacher whose")
            out("      progress data differs between prod and dev.")
            out("─" * 90)
            out()

            # Build educator lookup by name
            sessions_by_name = defaultdict(list)
            for s in kckps_sessions:
                name = str(s.get("Name", "")).strip()
                if name:
                    sessions_by_name[name].append(s)

            for email, ra, diffs in teachers_with_diffs:
                teacher_name = ra["Name"]
                teacher_sessions = sessions_by_name.get(teacher_name, [])

                if not teacher_sessions:
                    # Try partial match
                    for sname, slist in sessions_by_name.items():
                        if (
                            teacher_name.lower() in sname.lower()
                            or sname.lower() in teacher_name.lower()
                        ):
                            teacher_sessions = slist
                            break

                out(f"  ┌─ {teacher_name}  ({email})")
                for field, va, vb in diffs:
                    out(f"  │   {field}: {va!r} → {vb!r}")

                if teacher_sessions:
                    out(f"  │")
                    out(f"  │   Pathful Sessions ({len(teacher_sessions)}):")
                    for s in teacher_sessions:
                        title = (
                            s.get("Title") or s.get("Series or Event Title") or "N/A"
                        )
                        date = s.get("Date", "N/A")
                        status = s.get("Status", "N/A")
                        attended_ed = s.get("Attended Educator Count", "N/A")
                        out(f"  │     • {title}")
                        out(
                            f"  │       Date: {date}  |  Status: {status}  |  Attended Educators: {attended_ed}"
                        )
                else:
                    out(f"  │   ⚠ No matching sessions found in Pathful report")

                out(f"  └{'─' * 65}")
                out()

    # ── End ──────────────────────────────────────
    out("=" * 90)
    out("  END OF REPORT")
    out("=" * 90)

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Compare KCKPS Teacher Progress exports (prod vs dev)."
    )
    parser.add_argument(
        "--progress-a",
        default=DEFAULT_PROGRESS_A,
        help="Teacher Progress Excel (production)",
    )
    parser.add_argument(
        "--progress-b", default=DEFAULT_PROGRESS_B, help="Teacher Progress Excel (dev)"
    )
    parser.add_argument(
        "--audit-a", default=DEFAULT_AUDIT_A, help="Audit log CSV (production)"
    )
    parser.add_argument(
        "--audit-b", default=DEFAULT_AUDIT_B, help="Audit log CSV (dev)"
    )
    parser.add_argument(
        "--sessions",
        default=DEFAULT_SESSION_REPORT,
        help="Pathful Session Report Excel",
    )
    parser.add_argument(
        "--no-audit", action="store_true", help="Skip audit log comparison"
    )
    parser.add_argument(
        "--no-sessions", action="store_true", help="Skip session report cross-reference"
    )
    args = parser.parse_args()

    for label, path in [
        ("Progress A", args.progress_a),
        ("Progress B", args.progress_b),
    ]:
        if not os.path.exists(path):
            print(f"ERROR: {label} file not found: {path}")
            sys.exit(1)

    audit_a = None if args.no_audit else args.audit_a
    audit_b = None if args.no_audit else args.audit_b
    session_path = None if args.no_sessions else args.sessions

    # Warn about missing optional files
    if audit_a and not os.path.exists(audit_a):
        print(f"WARNING: Audit log A not found, skipping: {audit_a}")
        audit_a = None
    if audit_b and not os.path.exists(audit_b):
        print(f"WARNING: Audit log B not found, skipping: {audit_b}")
        audit_b = None
    if session_path and not os.path.exists(session_path):
        print(f"WARNING: Session report not found, skipping: {session_path}")
        session_path = None

    report = build_report(
        args.progress_a,
        args.progress_b,
        audit_a,
        audit_b,
        session_path,
    )
    print(report)

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(DATA_DIR, f"comparison_report_{timestamp}.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"\n📄 Report saved to: {report_path}")


if __name__ == "__main__":
    main()
