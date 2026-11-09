"""Download raw data for the DATA:4600 project.

- NIBRS incident files from the FBI Crime Data Explorer: one zip per state per
  year (2011-2025), each holding every NIBRS table as CSV. About 9 GB total.
- NFL games (with Vegas spreads) from nflverse.

Standard library only. Re-running skips files that already downloaded.

    python download_data.py            # saves into ./data
    python download_data.py --out raw  # or pick a folder
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

YEARS = range(2011, 2026)
STATES = (
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
    "NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"
).split()

# Returns {"<key>": "<presigned S3 url, valid ~15 min>"}
SIGNED_URL = "https://cde.ucr.cjis.gov/LATEST/s3/signedurl?key={key}"
NFL_GAMES = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"


def fetch(url, retries=4):
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):  # file doesn't exist (state didn't report that year)
                return None
            if attempt == retries:
                raise
        except urllib.error.URLError:
            if attempt == retries:
                raise
        time.sleep(2 ** (attempt + 1))


def save(path, data):
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    out = Path(ap.parse_args().out)
    (out / "nfl").mkdir(parents=True, exist_ok=True)

    games = out / "nfl" / "games.csv"
    if not games.exists():
        save(games, fetch(NFL_GAMES))
        print("nfl games done")

    for year in YEARS:
        ydir = out / "nibrs" / str(year)
        ydir.mkdir(parents=True, exist_ok=True)
        got = missing = 0
        for state in STATES:
            dest = ydir / f"{state}-{year}.zip"
            if dest.exists() and dest.stat().st_size > 0:
                got += 1
                continue
            key = f"nibrs/incident/{year}/{state}-{year}.zip"
            body = fetch(SIGNED_URL.format(key=key))
            url = json.loads(body).get(key) if body else None
            data = fetch(url) if url else None
            if data:
                save(dest, data)
                got += 1
            else:
                missing += 1
        print(f"{year}: {got} states, {missing} not available")


if __name__ == "__main__":
    main()
