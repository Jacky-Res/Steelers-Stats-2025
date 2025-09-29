import os
import json
import pandas as pd
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

# -------------------- Setup --------------------
load_dotenv()
st.set_page_config(page_title="🏈 Steelers Stats Dashboard", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("❌ Missing Supabase credentials.")
    st.stop()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@st.cache_data(ttl=60)
def fetch_all():
    res = supabase.table("steelers_stats").select("*").execute()
    return pd.DataFrame(res.data or [])

df = fetch_all()
if df.empty:
    st.title("🏈 Pittsburgh Steelers 2025 Stats")
    st.info("No stats found in Supabase.")
    st.stop()

# -------------------- Helpers --------------------
def to_list(x):
    """Parse Supabase JSON/text column into a Python list."""
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            # fallback: split by comma if a plain string somehow
            return [p.strip() for p in x.split(",")]
    return []

def expand_kv(df_cat: pd.DataFrame) -> pd.DataFrame:
    """
    Expand each Supabase row where stat_key/stat_value are arrays
    into a flat dict (one row per player/stat record).
    """
    out = []
    for _, rec in df_cat.iterrows():
        keys = to_list(rec.get("stat_key"))
        vals = to_list(rec.get("stat_value"))
        row_dict = {k: v for k, v in zip(keys, vals)}
        # keep any player value on the record (for name tables this is set)
        if pd.notna(rec.get("player")) and rec.get("player") not in (None, "None", ""):
            row_dict.setdefault("player", rec["player"])
        out.append(row_dict)
    return pd.DataFrame(out) if out else pd.DataFrame()

# Pair names-table with stats-table
PAIR_MAP = {
    ("table_0", "table_1"): "Passing Stats",
    ("table_2", "table_3"): "Rushing Stats",
    ("table_4", "table_5"): "Receiving Stats",
    ("table_6", "table_7"): "Defense Stats",
    ("table_8", "table_9"): "Scoring Stats",
    ("table_10", "table_11"): "Kicking Stats",
    ("table_12", "table_13"): "Field Goal Stats",
    ("table_14", "table_15"): "Punting Stats",
}

def build_section(names_table: str, stats_table: str) -> pd.DataFrame:
    """
    Reconstruct a clean table:
      - expand numeric stats from stats_table
      - pull player names from names_table ("Name" or 'player')
      - align by index
      - drop duplicates and 'Total'
    """
    names_src = df[df["category"] == names_table]
    stats_src = df[df["category"] == stats_table]
    if stats_src.empty:
        return pd.DataFrame()

    stats_df = expand_kv(stats_src)
    names_df = expand_kv(names_src)

    # Get a name list from names_df
    names_list = []
    if not names_df.empty:
        if "player" in names_df.columns and not names_df["player"].isna().all():
            names_list = names_df["player"].astype(str).tolist()
        elif "Name" in names_df.columns:
            names_list = names_df["Name"].astype(str).tolist()

    # Align lengths
    if names_list:
        names_list = names_list[: len(stats_df)]
        if len(names_list) < len(stats_df):
            names_list += [None] * (len(stats_df) - len(names_list))
        stats_df.insert(0, "player", names_list)
    else:
        # If no names at all, keep whatever is there (likely None)
        if "player" not in stats_df.columns:
            stats_df.insert(0, "player", [None] * len(stats_df))

    # Drop team total unless you want it
    stats_df = stats_df[stats_df["player"] != "Total"]

    # Deduplicate (some sites repeat the set)
    stats_df = stats_df.drop_duplicates()

    # Convert numeric columns when possible (keep player as string)
    for col in stats_df.columns:
        if col == "player":
            continue
        stats_df[col] = pd.to_numeric(stats_df[col], errors="ignore")

    return stats_df

def best_chart_column(label: str, columns: list[str]) -> str | None:
    if label.startswith("Passing") and "YDS" in columns: return "YDS"
    if label.startswith("Rushing") and "CAR" in columns: return "CAR"
    if label.startswith("Receiving") and "REC" in columns: return "REC"
    # General fallbacks
    for cand in ("YDS", "TD", "GP"):
        if cand in columns: return cand
    return None

# -------------------- UI --------------------
st.title("🏈 Pittsburgh Steelers 2025 Stats")

for (names_tbl, stats_tbl), label in PAIR_MAP.items():
    section = build_section(names_tbl, stats_tbl)
    if section.empty:
        continue

    st.subheader(f"📊 {label}")
    st.dataframe(section, use_container_width=True)

    col = best_chart_column(label, list(section.columns))
    if col and not section.empty:
        try:
            chart_df = section.copy()
            chart_df[col] = pd.to_numeric(chart_df[col], errors="coerce")
            # Remove NaN & keep players with a name
            chart_df = chart_df.dropna(subset=[col])
            chart_df = chart_df[chart_df["player"].notna()]
            if not chart_df.empty:
                st.bar_chart(chart_df.set_index("player")[col])
        except Exception:
            pass








