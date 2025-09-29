import os
import pathlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json

DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)
JSON_PATH = DATA_DIR / "steelers_stats.json"
META_PATH = DATA_DIR / "meta.txt"

def collect_stats(url: str) -> None:
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

    stats_data = {}

    tables = soup.find_all("table")
    for idx, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
        stats_data[f"table_{idx}"] = {"headers": headers, "rows": rows}

    JSON_PATH.write_text(json.dumps(stats_data, indent=2), encoding="utf-8")

    META_PATH.write_text(
        f"source_url={url}\nextracted_at={datetime.now(timezone.utc).isoformat()}",
        encoding="utf-8",
    )

    print(f"Saved stats JSON to {JSON_PATH} with {len(stats_data)} tables")

if __name__ == "__main__":
    url = "https://www.espn.com/nfl/team/stats/_/name/pit"  # Steelers stats
    collect_stats(url)


