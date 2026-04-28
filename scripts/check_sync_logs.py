import sqlite3

conn = sqlite3.connect("instance/your_database.db")
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_logs'")
print("sync_logs table exists:", bool(cur.fetchone()))
cur.execute(
    "SELECT sync_type, status, recovery_buffer_hours, last_sync_watermark FROM sync_logs ORDER BY id DESC LIMIT 20"
)
rows = cur.fetchall()
print("sync_type | status | buffer_hours | watermark")
print("-" * 75)
for r in rows:
    print(f"{str(r[0]):<25} {str(r[1]):<12} {str(r[2]):<14} {r[3]}")
conn.close()
