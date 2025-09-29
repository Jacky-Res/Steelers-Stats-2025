import json
import pathlib
import os
from supabase import create_client

DATA_DIR = pathlib.Path("data")
JSON_PATH = DATA_DIR / "steelers_stats.json"

# Initialize Supabase connection
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
else:
    print("⚠️ Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment.")

# Map ESPN tables → friendly names
TABLE_MAP = {
    "table_0": "passing_names",
    "table_1": "passing_stats",
    "table_2": "rushing_names",
    "table_3": "rushing_stats",
    "table_4": "receiving_names",
    "table_5": "receiving_stats",
    "table_6": "defense_names",
    "table_7": "defense_stats",
    "table_8": "scoring_names",
    "table_9": "scoring_stats",
    "table_10": "kick_names",
    "table_11": "kick_stats",
    "table_12": "fg_names",
    "table_13": "fg_stats",
    "table_14": "punting_names",
    "table_15": "punting_stats",
}

def print_stats():
    if not JSON_PATH.exists():
        print(f"❌ File not found: {JSON_PATH}")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        stats = json.load(f)

    print("📊 Steelers 2025 Stats (from JSON)\n")

    for table_name, table in stats.items():
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        friendly_name = TABLE_MAP.get(table_name, table_name)

        print(f"--- {friendly_name} ---")
        print(" | ".join(headers))

        for row in rows[:5]:  # print only first 5 rows
            print(" | ".join(row.get(h, "") for h in headers))

        print()

        # Insert into Supabase if client is available
        if supabase:
            for row in rows:
                player = row.get("Player") or row.get("Name")
                for key, value in row.items():
                    if key not in ["Player", "Name"]:
                        supabase.table("steelers_stats").insert({
                            "category": friendly_name,
                            "player": player,
                            "stat_key": key,
                            "stat_value": value
                        }).execute()

if __name__ == "__main__":
    print_stats()







