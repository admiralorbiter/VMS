import sqlite3
import pandas as pd

def get_stats(db_path):
    conn = sqlite3.connect(db_path)
    
    stats = {}
    
    # 1. Basic row counts
    tables = [
        "event",
        "event_teacher",
        "teacher",
        "teacher_progress",
        "pathful_unmatched_record",
        "pathful_import_log"
    ]
    
    for table in tables:
        try:
            stats[f"Count {table}"] = pd.read_sql_query(f"SELECT COUNT(*) as c FROM {table}", conn).iloc[0]["c"]
        except Exception as e:
            stats[f"Count {table}"] = 0
            
    # 2. PathfulUnmatchedRecord by type and status
    try:
        unmatched_df = pd.read_sql_query(
            "SELECT unmatched_type, resolution_status, COUNT(*) as c FROM pathful_unmatched_record GROUP BY unmatched_type, resolution_status", 
            conn
        )
        for _, row in unmatched_df.iterrows():
            stats[f"Unmatched {row['unmatched_type']} ({row['resolution_status']})"] = row["c"]
    except Exception as e:
        pass

    # 3. Events by status
    try:
        events_df = pd.read_sql_query(
            "SELECT status, COUNT(*) as c FROM event GROUP BY status", 
            conn
        )
        for _, row in events_df.iterrows():
            stats[f"Event ({row['status']})"] = row["c"]
    except Exception as e:
        pass

    # 4. EventTeacher by status
    try:
        et_df = pd.read_sql_query(
            "SELECT status, COUNT(*) as c FROM event_teacher GROUP BY status", 
            conn
        )
        for _, row in et_df.iterrows():
            stats[f"EventTeacher ({row['status']})"] = row["c"]
    except Exception as e:
        pass

    conn.close()
    return stats

def main():
    prod_db = "instance/prod/your_database.db"
    local_db = "instance/your_database.db"
    
    print("Gathering stats...")
    prod_stats = get_stats(prod_db)
    local_stats = get_stats(local_db)
    
    # Get all unique keys
    all_keys = list(set(list(prod_stats.keys()) + list(local_stats.keys())))
    all_keys.sort()
    
    print(f"\n{'-'*60}")
    print(f"{'Metric':<40} | {'Prod':<8} | {'Local':<8}")
    print(f"{'-'*60}")
    
    for key in all_keys:
        p_val = prod_stats.get(key, 0)
        l_val = local_stats.get(key, 0)
        
        # Highlight differences
        marker = " " if p_val == l_val else "*"
        
        print(f"{marker} {key:<38} | {p_val:<8} | {l_val:<8}")

if __name__ == "__main__":
    main()
