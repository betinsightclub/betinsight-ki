import os
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

URLS = [
    "https://raw.githubusercontent.com/PranavSitaraman/NBA-Injury-Betting/main/basketball-final.sqlite.zip",
    "https://github.com/PranavSitaraman/NBA-Injury-Betting/raw/main/basketball-final.sqlite.zip",
]
OUT = Path("/tmp/basketball-final.sqlite.zip")
EXTRACT = Path("/tmp/nba_sqlite")
EXTRACT.mkdir(parents=True, exist_ok=True)

last = None
for url in URLS:
    try:
        print("DOWNLOAD", url)
        urllib.request.urlretrieve(url, OUT)
        print("DOWNLOADED_BYTES", OUT.stat().st_size)
        break
    except Exception as e:
        last = e
        print("DOWNLOAD_FAILED", repr(e))
else:
    raise RuntimeError(f"all downloads failed: {last!r}")

with zipfile.ZipFile(OUT) as z:
    print("ZIP_MEMBERS", [(x.filename, x.file_size, x.compress_size) for x in z.infolist()])
    z.extractall(EXTRACT)

sqlite_files = list(EXTRACT.rglob("*.sqlite")) + list(EXTRACT.rglob("*.db"))
if not sqlite_files:
    raise RuntimeError(f"No sqlite file found under {EXTRACT}")
path = sqlite_files[0]
print("SQLITE_PATH", path, "BYTES", path.stat().st_size)

con = sqlite3.connect(path)
cur = con.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("TABLES", tables)
for t in tables:
    try:
        n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    except Exception as e:
        n = f"ERR:{e}"
    cols = cur.execute(f'PRAGMA table_info("{t}")').fetchall()
    print("TABLE", t, "COUNT", n)
    print("COLUMNS", [(c[1], c[2]) for c in cols])
    if t.lower() == "bettingodds_history":
        names = [c[1] for c in cols]
        rows = cur.execute(f'SELECT * FROM "{t}" LIMIT 5').fetchall()
        for r in rows:
            print("SAMPLE", dict(zip(names, r)))

# Also locate columns that matter even if the table name differs.
for t in tables:
    cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]
    low = {c.lower(): c for c in cols}
    if any("2h" in c.lower() for c in cols) or any("spread" in c.lower() for c in cols):
        print("ODDS_CANDIDATE_TABLE", t, cols)

con.close()
