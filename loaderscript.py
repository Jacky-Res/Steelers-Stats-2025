import json
import pandas as pd
from pathlib import Path
from supabase import create_client
import os
from dotenv import load_dotenv

# --- Load .env (explicit path) ---
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    print(f"🔍 Loading env vars from {env_path}")
    load_dotenv(dotenv_path=env_path)
else:
    print("⚠️ No .env file found, relying on shell environment variables.")

# --- Config ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

print("DEBUG SUPABASE_URL:", SUPABASE_URL)
print("DEBUG SUPABASE_ANON_KEY prefix:", SUPABASE_ANON_KEY[:10] if SUPABASE_ANON_KEY else None)

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("❌ Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_ANON_KEY.")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --- Files ---
DATA_DIR = Path("data")
OUT_JSON_PATH = DATA_DIR / "records.json"

def load_to_supabase():
    if not OUT_JSON_PATH.exists():
        raise FileNotFoundError(f"❌ {OUT_JSON_PATH} not found. Run structurer.py first.")

    # Load JSON
    records = json.loads(OUT_JSON_PATH.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = [records]

    # Convert to DataFrame
    df = pd.DataFrame.from_records(records)
    print("📊 Preview of data to insert:")
    print(df.head())

    # Upsert to Supabase
    rows = df.to_dict(orient="records")
    res = supabase.table("collected_docs").upsert(rows, on_conflict="id").execute()

    print(f"✅ Upserted {len(rows)} rows into Supabase.")
    if getattr(res, "error", None):
        print("❌ Supabase error:", res.error)

if __name__ == "__main__":
    load_to_supabase()

