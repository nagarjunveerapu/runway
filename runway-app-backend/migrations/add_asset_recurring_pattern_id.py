"""
Migration: Add recurring_pattern_id to assets and backfill from notes
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage.database import DatabaseManager


def migrate():
    db = DatabaseManager()
    conn = db.engine.raw_connection()
    cur = conn.cursor()
    try:
        try:
            cur.execute("ALTER TABLE assets ADD COLUMN recurring_pattern_id VARCHAR(36)")
            conn.commit()
            print("✅ Added assets.recurring_pattern_id")
        except Exception as e:
            print(f"ℹ️  Skipping add column: {e}")

        # Backfill from notes if present: pattern 'mapped_from_emi:{pattern_id}:'
        try:
            cur.execute("SELECT asset_id, notes FROM assets WHERE notes IS NOT NULL")
            rows = cur.fetchall()
            updated = 0
            import re
            for asset_id, notes in rows:
                if not notes:
                    continue
                m = re.search(r"mapped_from_emi:([^:]+)", str(notes))
                if m:
                    pid = m.group(1)
                    cur.execute("UPDATE assets SET recurring_pattern_id = ? WHERE asset_id = ?", (pid, asset_id))
                    updated += 1
            conn.commit()
            print(f"✅ Backfilled recurring_pattern_id for {updated} assets from notes")
        except Exception as e:
            print(f"ℹ️  Skipping backfill: {e}")

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    migrate()



