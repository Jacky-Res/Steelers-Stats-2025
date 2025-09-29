import os
import re
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI

# Optional: load .env for local runs (ignore if you don't use it)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- Config (env or defaults) ---
ENDPOINT = os.getenv("OPENAI_BASE_URL", "https://cdong1--azure-proxy-web-app.modal.run")
API_KEY = os.getenv("OPENAI_API_KEY", "supersecretkey")
MODEL = os.getenv("OPENAI_DEPLOYMENT", "gpt-4o")
DEBUG = os.getenv("DEBUG", "0") == "1"

client = OpenAI(base_url=ENDPOINT, api_key=API_KEY)

# --- Files ---
DATA_DIR = Path("data")
RAW_BLOB_PATH = DATA_DIR / "raw_blob.txt"
META_PATH = DATA_DIR / "meta.txt"
OUT_JSON_PATH = DATA_DIR / "records.json"

SCHEMA = {
    "id": "string (unique id)",
    "title": "string",
    "summary": "string",
    "source_url": "string",
    "extracted_at": "ISO8601 timestamp"
}

def read_meta():
    meta = {}
    if META_PATH.exists():
        for line in META_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                meta[k.strip()] = v.strip()
    return meta

def clean_llm_output(raw: str) -> str:
    """
    Make the model output parseable:
    1) strip triple backtick fences (``` or ```json)
    2) if still mixed text, extract the first JSON object/array substring
    """
    s = raw.strip()

    # Strip fenced code blocks like ```json ... ``` or ``` ... ```
    if s.startswith("```"):
        # remove opening ```
        s = s[3:].lstrip()
        # drop a leading language tag like 'json'
        s = re.sub(r"^(json|javascript|js|txt)\s*", "", s, flags=re.IGNORECASE)
        # remove trailing ``` if present
        if s.endswith("```"):
            s = s[:-3].rstrip()

    # If still not pure JSON, try to extract the first {...} or [...]
    def try_json(x: str):
        try:
            return json.loads(x), x
        except Exception:
            return None, None

    parsed, used = try_json(s)
    if parsed is not None:
        return s  # already valid

    # Find first JSON-looking block
    first_obj = s.find("{")
    first_arr = s.find("[")
    starts = [i for i in [first_obj, first_arr] if i != -1]
    if starts:
        start = min(starts)
        # heuristically find the last closing brace/bracket
        end_obj = s.rfind("}")
        end_arr = s.rfind("]")
        end = max(end_obj, end_arr)
        if end > start:
            candidate = s[start : end + 1]
            parsed, used = try_json(candidate)
            if parsed is not None:
                return candidate

    # Give up: return original (caller will print it on failure)
    return s

def normalize_records(records, fallback_url, fallback_extracted_at, blob_for_id_seed):
    """Ensure required fields exist and are consistent."""
    out = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        title = rec.get("title") or ""
        source_url = rec.get("source_url") or fallback_url or "unknown"
        extracted_at = rec.get("extracted_at") or fallback_extracted_at or datetime.now(timezone.utc).isoformat()
        summary = rec.get("summary") or title

        _id = rec.get("id")
        if not _id:
            seed = f"{title}|{source_url}|{extracted_at}|{len(blob_for_id_seed)}"
            _id = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]

        out.append({
            "id": _id,
            "title": title,
            "summary": summary,
            "source_url": source_url,
            "extracted_at": extracted_at
        })
    return out

def structure_blob():
    # --- Guardrails ---
    if not RAW_BLOB_PATH.exists():
        raise SystemExit("❌ data/raw_blob.txt not found. Run the collector first.")

    blob = RAW_BLOB_PATH.read_text(encoding="utf-8").strip()
    if not blob:
        raise SystemExit("❌ data/raw_blob.txt is empty. Check your collector URL/extractor.")

    meta = read_meta()
    now_iso = datetime.now(timezone.utc).isoformat()
    source_url = meta.get("source_url", "unknown")
    extracted_at = meta.get("extracted_at", now_iso)

    system = (
        "Return ONLY valid JSON (no code fences, no prose). "
        f"Use this schema exactly: {json.dumps(SCHEMA)}. "
        "If you can only produce one item, return a JSON OBJECT; if many, a JSON ARRAY of objects."
    )
    user = (
        f"Source URL: {source_url}\n"
        f"Extracted at: {extracted_at}\n\n"
        f"TEXT:\n{blob}"
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0
    )

    raw = resp.choices[0].message.content or ""
    if DEBUG:
        print("----- RAW FROM MODEL -----")
        print(raw)
        print("----- END RAW -----")

    cleaned = clean_llm_output(raw)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        print("❌ LLM output still not valid JSON after cleaning. Here is what I tried to parse:\n")
        print(cleaned)
        raise SystemExit(1)

    # Normalize to a list
    if isinstance(parsed, dict):
        parsed = [parsed]
    elif not isinstance(parsed, list):
        print("❌ Parsed JSON is neither object nor array. Got:", type(parsed))
        raise SystemExit(1)

    normalized = normalize_records(parsed, source_url, extracted_at, blob)
    OUT_JSON_PATH.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Wrote {OUT_JSON_PATH} with {len(normalized)} record(s).")

if __name__ == "__main__":
    structure_blob()

