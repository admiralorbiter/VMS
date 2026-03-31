import sqlite3


def compare(label, sql, lc, pc):
    l = lc.cursor()
    l.execute(sql)
    lr = l.fetchall()
    p = pc.cursor()
    p.execute(sql)
    pr = p.fetchall()
    print(f"\n--- {label} ---")
    print(f"  LOCAL: {lr}")
    print(f"  PROD:  {pr}")
    return lr, pr


lc = sqlite3.connect("instance/your_database.db")
pc = sqlite3.connect("instance/prod/your_database.db")

# First get the correct column names from both DBs
print("=== LOCAL event columns ===")
c = lc.cursor()
c.execute("PRAGMA table_info(event)")
print([r[1] for r in c.fetchall()])
print("\n=== PROD event columns ===")
c = pc.cursor()
c.execute("PRAGMA table_info(event)")
print([r[1] for r in c.fetchall()])
print("\n=== LOCAL event_teacher columns ===")
c = lc.cursor()
c.execute("PRAGMA table_info(event_teacher)")
print([r[1] for r in c.fetchall()])

# Sample what 'format' values look like for virtual sessions
print("\n=== Sample event format values ===")
c = lc.cursor()
c.execute("SELECT DISTINCT format, status, academic_year FROM event LIMIT 20")
for r in c.fetchall():
    print(" ", r)

# TeacherProgress rows - spring 2025-2026 (check actual academic_year values in TP)
print("\n=== TeacherProgress academic_year values ===")
c = lc.cursor()
c.execute(
    "SELECT DISTINCT academic_year, virtual_year FROM teacher_progress WHERE tenant_id=1 LIMIT 10"
)
for r in c.fetchall():
    print(" ", r)

lc.close()
pc.close()
