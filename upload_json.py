import os
import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()


# --- Supabase setup ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY env variables")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --- Step 1: Scrape ESPN Steelers stats ---
def collect_stats(url: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table")

    stats_data = {}
    for idx, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
        stats_data[f"table_{idx}"] = {"headers": headers, "rows": rows}

    return stats_data


# --- Step 2: Collect Steelers stats ---
url = "https://www.espn.com/nfl/team/stats/_/name/pit"
stats = collect_stats(url)

print("📊 Scraped tables:", list(stats.keys()))

# --- Step 3: Insert ALL tables into Supabase ---
for table_name, table in stats.items():
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    if not rows:
        continue  # skip empty tables

    df = pd.DataFrame(rows)

    # Example: drop LNG column if exists
    if "LNG" in df.columns:
        df = df.drop(columns=["LNG"])

    print(f"\n📥 Inserting {len(df)} rows from {table_name}...")

    rows_to_insert = df.to_dict(orient="records")

    for row in rows_to_insert:
        supabase.table("steelers_stats").insert({
            "category": table_name,
            "player": row.get("Player") or row.get("Name"),
            "stat_key": json.dumps(list(row.keys())),
            "stat_value": json.dumps(list(row.values()))
        }).execute()

    print(f"✅ Inserted {len(rows_to_insert)} rows from {table_name}")

# --- Step 4: Verify by reading back ---
response = supabase.table("steelers_stats").select("*").limit(10).execute()

print("\n🔎 Sample from Supabase:")
for record in response.data:
    print(record)


