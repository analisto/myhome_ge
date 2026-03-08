import asyncio
import csv
import json
import sys
from pathlib import Path

from curl_cffi.requests import AsyncSession

API_BASE = "https://api-statements.tnet.ge/v1/statements"
COUNT_URL = f"{API_BASE}/count"

HEADERS = {
    "X-Website-Key": "myhome",
    "Accept": "application/json",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "referer": "https://www.myhome.ge/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
}

PARAMS_BASE = {
    "currency_id": "1",
    "locale": "ka",
}

CONCURRENCY = 10  # parallel requests
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "data.csv"


def flatten_listing(item: dict) -> dict:
    row = {}
    for key, value in item.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (dict, list)):
                    row[f"{key}_{sub_key}"] = json.dumps(sub_value, ensure_ascii=False)
                else:
                    row[f"{key}_{sub_key}"] = sub_value
        elif isinstance(value, list):
            row[key] = json.dumps(value, ensure_ascii=False)
        else:
            row[key] = value
    return row


async def get_total_pages(session: AsyncSession) -> tuple[int, int]:
    r = await session.get(COUNT_URL, headers=HEADERS, params=PARAMS_BASE)
    r.raise_for_status()
    d = r.json()["data"]
    return d["last_page"], d["total"]


async def fetch_page(session: AsyncSession, page: int) -> list[dict]:
    params = {**PARAMS_BASE, "page": str(page)}
    r = await session.get(API_BASE, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()["data"]["data"]


async def scrape(max_pages: int | None = None) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSession(impersonate="chrome110") as session:
        last_page, total = await get_total_pages(session)
        if max_pages is not None:
            last_page = min(last_page, max_pages)

        print(f"Total listings: {total:,} | Pages to scrape: {last_page:,}", flush=True)

        # Fetch page 1 to establish fieldnames
        print("Fetching page 1 ...", flush=True)
        first_listings = await fetch_page(session, 1)
        rows = [flatten_listing(item) for item in first_listings]
        fieldnames = list(rows[0].keys()) if rows else []

        with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        # Fetch remaining pages with bounded concurrency
        sem = asyncio.Semaphore(CONCURRENCY)
        completed = 1

        async def fetch_and_write(page: int) -> None:
            nonlocal completed
            async with sem:
                try:
                    listings = await fetch_page(session, page)
                    page_rows = [flatten_listing(item) for item in listings]
                    # Append (file lock not needed: GIL covers single-writer pattern)
                    with OUTPUT_FILE.open("a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                        writer.writerows(page_rows)
                    completed += 1
                    if completed % 100 == 0:
                        print(f"  {completed}/{last_page} pages done", flush=True)
                except Exception as exc:
                    print(f"  [WARN] page {page} failed: {exc}", flush=True)

        tasks = [fetch_and_write(p) for p in range(2, last_page + 1)]
        await asyncio.gather(*tasks)

    print(f"\nDone. {completed} pages scraped -> {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(scrape(max_pages))
