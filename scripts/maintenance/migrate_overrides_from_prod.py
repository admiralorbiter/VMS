"""
Migrate manual production data to LOCAL DB for KCKPS (tenant=1).

Covers two categories:
  1. Attendance overrides (ADD/REMOVE) applied via the UI on production.
  2. Manually-added TeacherProgress records (last_import_id IS NULL) that
     were added through the admin UI on production and never came in via import.

Safe: dry-run by default. Pass --commit to apply.

Usage:
    python scripts/maintenance/migrate_overrides_from_prod.py           # dry-run
    python scripts/maintenance/migrate_overrides_from_prod.py --commit  # apply
"""

import sqlite3
import sys

DRY_RUN = "--commit" not in sys.argv

LOCAL_DB = "instance/your_database.db"
PROD_DB = "instance/prod/your_database.db"

lc = sqlite3.connect(LOCAL_DB)
pc = sqlite3.connect(PROD_DB)

prefix = "[DRY RUN] " if DRY_RUN else ""
print(f"{prefix}Syncing manual PROD data -> LOCAL\n")

# ── SECTION 1: Attendance Overrides ───────────────────────────────────────────
print("=== 1. Attendance Overrides ===")

prod_rows = pc.execute(
    "SELECT ao.id, ao.teacher_progress_id, ao.event_id, ao.action, "
    "       ao.reason, ao.created_at, ao.is_active, ao.created_by, "
    "       ao.reversed_at, ao.reversal_reason, "
    "       tp.email, tp.name "
    "FROM attendance_override ao "
    "JOIN teacher_progress tp ON ao.teacher_progress_id=tp.id "
    "WHERE tp.tenant_id=1 AND ao.is_active=1 "
    "ORDER BY ao.created_at"
).fetchall()
print(f"Active PROD overrides for KCKPS : {len(prod_rows)}")

existing_overrides = set(
    (r[0], r[1], r[2])
    for r in lc.execute(
        "SELECT ao.teacher_progress_id, ao.event_id, ao.action "
        "FROM attendance_override ao "
        "JOIN teacher_progress tp ON ao.teacher_progress_id=tp.id "
        "WHERE tp.tenant_id=1"
    ).fetchall()
)
print(f"Existing LOCAL overrides for KCKPS: {len(existing_overrides)}")

ov_inserted = ov_skipped = ov_missing_tp = 0
for row in prod_rows:
    (
        prod_ao_id,
        prod_tp_id,
        event_id,
        action,
        reason,
        created_at,
        is_active,
        created_by,
        reversed_at,
        reversal_reason,
        tp_email,
        tp_name,
    ) = row

    local_tp = lc.execute(
        "SELECT id FROM teacher_progress WHERE email=? AND tenant_id=1 AND is_active=1 LIMIT 1",
        (tp_email,),
    ).fetchone()

    if not local_tp:
        print(f"  SKIP (no local TP): {tp_name} <{tp_email}>")
        ov_missing_tp += 1
        continue

    local_tp_id = local_tp[0]
    key = (local_tp_id, event_id, action)
    if key in existing_overrides:
        ov_skipped += 1
        continue

    print(
        f"  {prefix}INSERT override: {action} | {tp_name} | event={event_id} | reason={reason!r}"
    )
    if not DRY_RUN:
        lc.execute(
            "INSERT INTO attendance_override "
            "(teacher_progress_id, event_id, action, reason, created_at, is_active, created_by) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (local_tp_id, event_id, action, reason, created_at, created_by),
        )
        existing_overrides.add(key)
    ov_inserted += 1

if not DRY_RUN:
    lc.commit()

print(
    f"\n  {prefix}Overrides — inserted: {ov_inserted}, skipped: {ov_skipped}, no local TP: {ov_missing_tp}"
)

# ── SECTION 2: Manually-added TeacherProgress records ─────────────────────────
print("\n=== 2. Manually-added Teachers (last_import_id IS NULL) ===")

prod_manual_tps = pc.execute(
    "SELECT name, email, building, academic_year, virtual_year, "
    "grade, target_sessions, district_name, is_active, tenant_id, pathful_user_id "
    "FROM teacher_progress "
    "WHERE tenant_id=1 AND is_active=1 AND last_import_id IS NULL "
    "ORDER BY name"
).fetchall()
print(f"Manually-added teachers on PROD: {len(prod_manual_tps)}")

local_emails = set(
    r[0]
    for r in lc.execute(
        "SELECT email FROM teacher_progress WHERE tenant_id=1"
    ).fetchall()
)

tp_inserted = tp_skipped = 0
for row in prod_manual_tps:
    name, email = row[0], row[1]
    if email in local_emails:
        tp_skipped += 1
        continue

    print(f"  {prefix}INSERT teacher: {name} <{email}> ({row[2]})")
    if not DRY_RUN:
        lc.execute(
            "INSERT INTO teacher_progress "
            "(name, email, building, academic_year, virtual_year, "
            " grade, target_sessions, district_name, is_active, tenant_id, pathful_user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )
        local_emails.add(email)
    tp_inserted += 1

if not DRY_RUN:
    lc.commit()

print(f"\n  {prefix}Teachers — inserted: {tp_inserted}, already existed: {tp_skipped}")

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'=' * 50}")
print(f"{prefix}Total inserted — overrides: {ov_inserted}, teachers: {tp_inserted}")
if DRY_RUN:
    print("\nRun with --commit to apply changes.")

lc.close()
pc.close()
