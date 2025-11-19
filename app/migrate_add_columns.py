# migrate_add_columns.py
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "./erp.db")  # 如果你的 DB 檔案叫別的名字，改這裡

NEEDED = {
    "mold_loc_photo": "TEXT",
    "mold_loc_updated_at": "DATETIME",
    "produced_last_qty": "INTEGER",
    "extra_photo_paths": "TEXT",
}


def has_column(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}")
        return
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    for col, typ in NEEDED.items():
        if not has_column(cur, "products", col):
            sql = f"ALTER TABLE products ADD COLUMN {col} {typ};"
            print("Running:", sql)
            cur.execute(sql)
    con.commit()
    con.close()
    print("Done. Columns ensured.")

if __name__ == "__main__":
    main()
