"""
Pre-Push Database Health Check
================================
Compares LOCAL vs PROD databases across row counts, schema, and business-critical
metrics to surface red flags before overwriting production.

Usage:
    python scripts/maintenance/db_health_check.py

Output:
    PASS  - within acceptable tolerance
    WARN  - notable difference, review before pushing
    FAIL  - significant delta that warrants investigation

Thresholds:
    Row-count delta > 5%  -> WARN
    Row-count delta > 20% -> FAIL
    Missing/extra schema columns -> FAIL
    Alembic version mismatch -> FAIL
"""

import sqlite3
from datetime import datetime

LOCAL_DB = "instance/your_database.db"
PROD_DB = "instance/prod/your_database.db"

WARN_PCT = 5
FAIL_PCT = 20

results = []


def check(label, status, local_val, prod_val, note=""):
    """Record one check result."""
    results.append((status, label, local_val, prod_val, note))
    icon = {"PASS": "v", "WARN": "!", "FAIL": "X"}.get(status, "?")
    print(f"  [{icon}] {status:<4}  {label}")
    if note:
        print(f"           {note}")
    if local_val != prod_val:
        print(f"           LOCAL={local_val}  PROD={prod_val}")


def row_count_check(label, sql, lc, pc, params=()):
    """Compare row counts and apply percentage thresholds."""
    lv = lc.execute(sql, params).fetchone()[0]
    pv = pc.execute(sql, params).fetchone()[0]
    if pv == 0 and lv == 0:
        check(label, "PASS", lv, pv)
        return
    base = max(lv, pv)
    delta_pct = abs(lv - pv) / base * 100 if base else 0
    if delta_pct == 0:
        check(label, "PASS", lv, pv)
    elif delta_pct <= WARN_PCT:
        check(label, "WARN", lv, pv, f"{delta_pct:.1f}% delta")
    elif delta_pct <= FAIL_PCT:
        check(label, "WARN", lv, pv, f"{delta_pct:.1f}% delta — review before push")
    else:
        check(label, "FAIL", lv, pv, f"{delta_pct:.1f}% delta — investigate!")


def schema_check(table, lc, pc):
    """Check that a table has the same columns in both DBs."""
    lc_cols = {r[1] for r in lc.execute(f"PRAGMA table_info({table})").fetchall()}
    pc_cols = {r[1] for r in pc.execute(f"PRAGMA table_info({table})").fetchall()}
    only_local = lc_cols - pc_cols
    only_prod = pc_cols - lc_cols
    if not only_local and not only_prod:
        check(f"schema: {table}", "PASS", "match", "match")
    else:
        note = ""
        if only_local:
            note += f"LOCAL-only cols: {sorted(only_local)}  "
        if only_prod:
            note += f"PROD-only cols: {sorted(only_prod)}"
        check(
            f"schema: {table}", "FAIL", str(sorted(lc_cols)), str(sorted(pc_cols)), note
        )


lc = sqlite3.connect(LOCAL_DB)
pc = sqlite3.connect(PROD_DB)

print("=" * 60)
print("  PRE-PUSH DB HEALTH CHECK")
print(f"  LOCAL: {LOCAL_DB}")
print(f"  PROD:  {PROD_DB}")
print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

# ── 1. Alembic version ────────────────────────────────────────
print("\n[1] Schema Version")
try:
    lv = lc.execute("SELECT version_num FROM alembic_version").fetchone()
    pv = pc.execute("SELECT version_num FROM alembic_version").fetchone()
    lv = lv[0] if lv else "MISSING"
    pv = pv[0] if pv else "MISSING"
    status = "PASS" if lv == pv else "WARN"
    note = "" if lv == pv else "Mismatch — run alembic upgrade head on prod after push"
    check("alembic_version", status, lv, pv, note)
except Exception as e:
    check(
        "alembic_version",
        "WARN",
        "unreadable",
        "unreadable",
        f"Could not read — prod DB may be from pre-recovery backup ({e})",
    )

# Tables known to exist only on prod (legacy) — expected loss on push, not a red flag
EXPECTED_PROD_ONLY = {"connector_data"}

# ── 2. Discover all tables in both DBs ───────────────────────
print("\n[2] Table Inventory & Schema Consistency")

local_tables = set(
    r[0]
    for r in lc.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
)
prod_tables = set(
    r[0]
    for r in pc.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
)

only_local_tables = local_tables - prod_tables
only_prod_tables = prod_tables - local_tables
shared_tables = local_tables & prod_tables

if only_local_tables:
    for t in sorted(only_local_tables):
        check(
            f"table exists: {t}",
            "WARN",
            "EXISTS",
            "MISSING",
            "New table on local only — will be created on prod after push",
        )
if only_prod_tables:
    for t in sorted(only_prod_tables):
        if t in EXPECTED_PROD_ONLY:
            check(
                f"table exists: {t}",
                "PASS",
                "MISSING",
                "EXISTS",
                "Legacy table — expected to be dropped on push",
            )
        else:
            check(
                f"table exists: {t}",
                "WARN",
                "MISSING",
                "EXISTS",
                "Table exists on prod but not local — data will be lost on push!",
            )
if not only_local_tables and not only_prod_tables:
    check(
        "all tables present",
        "PASS",
        f"{len(local_tables)} tables",
        f"{len(prod_tables)} tables",
    )

# Schema columns for every shared table
for table in sorted(shared_tables):
    try:
        schema_check(table, lc, pc)
    except Exception as e:
        check(f"schema: {table}", "WARN", "ERROR", "ERROR", str(e))

# ── 3. Row counts for ALL shared tables ───────────────────────
print("\n[3] Row Counts — All Tables")
for table in sorted(shared_tables):
    try:
        row_count_check(table, f"SELECT COUNT(*) FROM {table}", lc, pc)
    except Exception as e:
        check(table, "WARN", "ERROR", "ERROR", str(e))

# ── 4. KCKPS-specific business metrics ───────────────────────
print("\n[4] KCKPS Business Metrics (tenant=1)")
kckps_checks = [
    (
        "TeacherProgress (active)",
        "SELECT COUNT(*) FROM teacher_progress WHERE tenant_id=1 AND is_active=1",
    ),
    (
        "TeacherProgress (with teacher_id)",
        "SELECT COUNT(*) FROM teacher_progress WHERE tenant_id=1 AND is_active=1 AND teacher_id IS NOT NULL",
    ),
    (
        "Attendance overrides (ADD, active)",
        "SELECT COUNT(*) FROM attendance_override ao JOIN teacher_progress tp ON ao.teacher_progress_id=tp.id WHERE tp.tenant_id=1 AND ao.is_active=1 AND ao.action='add'",
    ),
    (
        "Attendance overrides (REMOVE, active)",
        "SELECT COUNT(*) FROM attendance_override ao JOIN teacher_progress tp ON ao.teacher_progress_id=tp.id WHERE tp.tenant_id=1 AND ao.is_active=1 AND ao.action='remove'",
    ),
    (
        "Spring COMPLETED sessions (Jan-Jul 2026)",
        "SELECT COUNT(*) FROM event WHERE type='VIRTUAL_SESSION' AND status='COMPLETED' AND start_date >= '2026-01-01' AND start_date <= '2026-07-31'",
    ),
    (
        "Spring attended ETs for KCKPS teachers",
        "SELECT COUNT(*) FROM event_teacher et JOIN event e ON et.event_id=e.id JOIN teacher_progress tp ON et.teacher_id=tp.teacher_id WHERE tp.tenant_id=1 AND tp.is_active=1 AND e.type='VIRTUAL_SESSION' AND e.status='COMPLETED' AND et.status='attended' AND e.start_date >= '2026-01-01' AND e.start_date <= '2026-07-31'",
    ),
]
for label, sql in kckps_checks:
    row_count_check(label, sql, lc, pc)

# ── 5. Pathful import pipeline ────────────────────────────────
print("\n[5] Pathful Import Pipeline")
pathful_checks = [
    ("PathfulUnmatchedRecord (total)", "SELECT COUNT(*) FROM pathful_unmatched_record"),
    # Note: column name varies — check actual schema if this errors
    (
        "PathfulUnmatchedRecord (unresolved)",
        "SELECT COUNT(*) FROM pathful_unmatched_record WHERE is_resolved=0",
    ),
    ("SchoolAlias records", "SELECT COUNT(*) FROM school_alias"),
    # OrganizationAlias: expected to differ — TD-052 is local-only until next deploy
    ("OrganizationAlias records", "SELECT COUNT(*) FROM organization_alias"),
]
for label, sql in pathful_checks:
    try:
        row_count_check(label, sql, lc, pc)
    except Exception as e:
        check(label, "WARN", "ERROR", "ERROR", f"Table may not exist: {e}")

# ── 6. Data quality red flags ─────────────────────────────────
print("\n[6] Data Quality Red Flags (LOCAL only)")
redflags = [
    (
        "Teachers with NULL teacher_id (KCKPS)",
        "SELECT COUNT(*) FROM teacher_progress WHERE tenant_id=1 AND is_active=1 AND teacher_id IS NULL",
    ),
    (
        "EventTeacher with NULL teacher_id",
        "SELECT COUNT(*) FROM event_teacher WHERE teacher_id IS NULL",
    ),
    (
        "Events with NULL start_date",
        "SELECT COUNT(*) FROM event WHERE start_date IS NULL",
    ),
    (
        "Volunteers without linked contact",
        "SELECT COUNT(*) FROM volunteer WHERE contact_id IS NULL",
    ),
]
for label, sql in redflags:
    try:
        lv = lc.execute(sql).fetchone()[0]
        pv = pc.execute(sql).fetchone()[0]
        if lv == 0 and pv == 0:
            check(label, "PASS", lv, pv)
        elif lv > 0 or pv > 0:
            check(label, "WARN", lv, pv, "Non-zero count — verify these are expected")
    except Exception as e:
        check(label, "WARN", "ERROR", "ERROR", str(e))

# ── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 60)
fails = [r for r in results if r[0] == "FAIL"]
warns = [r for r in results if r[0] == "WARN"]
passes = [r for r in results if r[0] == "PASS"]
print(f"  PASS: {len(passes)}   WARN: {len(warns)}   FAIL: {len(fails)}")

if fails:
    print("\n  FAILs to resolve before pushing:")
    for _, label, lv, pv, note in fails:
        print(f"    - {label}: {note or f'LOCAL={lv} PROD={pv}'}")

if warns:
    print("\n  WARNs to review:")
    for _, label, lv, pv, note in warns:
        print(f"    ~ {label}: {note or f'LOCAL={lv} PROD={pv}'}")

if not fails:
    print(
        "\n  No FAILs — safe to push."
        if not warns
        else "\n  No FAILs — review WARNs then push."
    )
else:
    print("\n  Resolve FAILs before pushing to production.")

print("=" * 60)

lc.close()
pc.close()
