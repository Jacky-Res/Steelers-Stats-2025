from modal import App, Image, asgi_app, Secret
import os, sys, subprocess
import json
import pathlib
from supabase import create_client

app = App("steelers-stats")

image = (
    Image.debian_slim()
    .pip_install(
        "streamlit",
        "supabase",
        "pandas",
        "python-dotenv",
        "beautifulsoup4",
        "requests",
    )
)

# Paths
DATA_DIR = pathlib.Path("data")
JSON_PATH = DATA_DIR / "steelers_stats.json"

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


def insert_stats():
    if not JSON_PATH.exists():
        print(f"❌ JSON not found: {JSON_PATH}")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        stats = json.load(f)

    # Connect to Supabase
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("⚠️ Missing Supabase credentials")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    print("📊 Inserting Steelers stats into Supabase...\n")

    for table_name, table in stats.items():
        friendly_name = TABLE_MAP.get(table_name, table_name)
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        print(f"--- {friendly_name} ---")
        print(" | ".join(headers))

        for row in rows[:3]:  # print preview
            print(" | ".join(row.get(h, "") for h in headers))

        # Insert into Supabase
        for row in rows:
            player = row.get("Player") or row.get("Name")
            for key, value in row.items():
                if key not in ["Player", "Name"]:
                    supabase.table("steelers_stats").insert(
                        {
                            "category": friendly_name,
                            "player": player,
                            "stat_key": key,
                            "stat_value": value,
                        }
                    ).execute()

    print("\n✅ Finished inserting Steelers stats.")


# Run stats loader
@app.function(secrets=[Secret.from_name("custom-secret")])
def run_stats():
    insert_stats()


# Streamlit app runner
@asgi_app()
def serve():
    port = os.environ.get("PORT", "8000")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "streamlit_app.py",
        "--server.port",
        port,
        "--server.address",
        "0.0.0.0",
    ]
    return subprocess.Popen(cmd)




