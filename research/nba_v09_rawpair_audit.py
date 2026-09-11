import math
import numpy as np
import pandas as pd

NORM_URL = "https://raw.githubusercontent.com/Nijjar06/nba-game-predictor/main/data/nba_2008-2025.csv"
SEASONS = {
    "2017-18": {
        "url": "https://raw.githubusercontent.com/garfjohnson/Nba-Sports-Betting-Model/master/nba%20odds%202017-18.csv",
        "start": "2017-10-01", "end": "2018-04-30", "regular_last_mmdd": 411,
        "target_n": 1230, "target_rmse": 9.883179436414059,
    },
    "2018-19": {
        "url": "https://raw.githubusercontent.com/garfjohnson/Nba-Sports-Betting-Model/master/nba%20odds%202018-19.csv",
        "start": "2018-10-01", "end": "2019-04-30", "regular_last_mmdd": 410,
        "target_n": 1230, "target_rmse": 10.19949385002746,
    },
}


def num(v):
    if pd.isna(v): return np.nan
    s = str(v).strip().lower()
    if s in {"pk", "pick", "pick'em", "pickem"}: return 0.0
    try: return float(s)
    except Exception: return np.nan


def build_raw(label, cfg):
    d = pd.read_csv(cfg["url"], dtype=str)
    games, bad = [], []
    for i in range(0, len(d) - 1, 2):
        a, h = d.iloc[i], d.iloc[i + 1]
        va, vh = str(a.get("VH", "")).strip().upper(), str(h.get("VH", "")).strip().upper()
        # Normal game = V/H. Neutral-site game = N/N, but SBR still keeps the first/second row
        # in the same two-team ordering used by the normalized source.
        if (va, vh) not in {("V", "H"), ("N", "N")}:
            bad.append((i, "VH", va, vh)); continue
        try:
            date_a, date_h = int(float(a["Date"])), int(float(h["Date"]))
        except Exception:
            bad.append((i, "date", a.get("Date"), h.get("Date"))); continue
        if date_a != date_h:
            bad.append((i, "date_mismatch", date_a, date_h)); continue
        if not (date_a >= 1000 or date_a <= cfg["regular_last_mmdd"]):
            continue
        h2a, h2h = num(a["2H"]), num(h["2H"])
        candidates = []
        if math.isfinite(h2a) and abs(h2a) <= 30: candidates.append(("away", abs(h2a)))
        if math.isfinite(h2h) and abs(h2h) <= 30: candidates.append(("home", abs(h2h)))
        if len(candidates) != 1:
            bad.append((i, "h2_identification", h2a, h2h)); continue
        spread_side, mag = candidates[0]
        home_spread = -mag if spread_side == "home" else mag
        expected = -home_spread
        vals = list(map(num, [a["1st"], a["2nd"], h["1st"], h["2nd"], a["Final"], h["Final"]]))
        if not all(math.isfinite(x) for x in vals):
            bad.append((i, "scores", vals)); continue
        q1a, q2a, q1h, q2h, fa, fh = vals
        actual = (fh-fa) - ((q1h+q2h)-(q1a+q2a))
        games.append({"raw_i": i, "date_mmdd": date_a, "away_raw": a["Team"], "home_raw": h["Team"],
                      "vh_pair": va+vh, "spread_side": spread_side, "h2_mag": mag,
                      "home_spread": home_spread, "expected": expected, "actual": actual})
    return pd.DataFrame(games), bad


def norm_subset(norm, cfg):
    x = norm.copy()
    x["_date"] = pd.to_datetime(x["date"], errors="coerce")
    s = x[(x["_date"] >= pd.Timestamp(cfg["start"])) & (x["_date"] <= pd.Timestamp(cfg["end"])) & (x["regular"] == True)].copy()
    s["actual"] = (s["score_home"]-s["score_away"]) - ((s["q1_home"]+s["q2_home"]) - (s["q1_away"]+s["q2_away"]))
    s["date_mmdd"] = s["_date"].dt.month*100+s["_date"].dt.day
    return s.reset_index(drop=True)

norm = pd.read_csv(NORM_URL)
for label, cfg in SEASONS.items():
    raw, bad = build_raw(label, cfg)
    ns = norm_subset(norm, cfg)
    err = raw["actual"] - raw["expected"]
    r = float(np.sqrt(np.mean(np.square(err))))
    print("\nSEASON", label)
    print("RAW_N", len(raw), "NORM_N", len(ns), "TARGET_N", cfg["target_n"], "BAD", len(bad))
    print("RMSE", repr(r), "TARGET", repr(cfg["target_rmse"]), "DELTA", repr(r-cfg["target_rmse"]))
    print("RMSE_CLOSE_1E12", abs(r-cfg["target_rmse"]) < 1e-12)
    print("NEUTRAL", raw[raw["vh_pair"]=="NN"].to_string(index=False))
    if bad: print("BAD_SAMPLE", bad[:20])

    if len(raw) == len(ns):
        cmp = pd.DataFrame({
            "i": np.arange(len(raw)),
            "raw_date": raw["date_mmdd"].to_numpy(), "norm_date": ns["date_mmdd"].to_numpy(),
            "raw_h2": raw["h2_mag"].to_numpy(), "norm_h2": pd.to_numeric(ns["h2_spread"], errors="coerce").to_numpy(),
            "raw_actual": raw["actual"].to_numpy(), "norm_actual": ns["actual"].to_numpy(),
            "away_norm": ns["away"].to_numpy(), "home_norm": ns["home"].to_numpy(),
            "away_raw": raw["away_raw"].to_numpy(), "home_raw": raw["home_raw"].to_numpy(),
        })
        mismatch = cmp[(cmp.raw_date != cmp.norm_date) | (~np.isclose(cmp.raw_h2, cmp.norm_h2, equal_nan=True)) | (~np.isclose(cmp.raw_actual, cmp.norm_actual, equal_nan=True))]
        print("SEQUENCE_MISMATCHES", len(mismatch))
        if len(mismatch): print(mismatch.head(50).to_string(index=False))
        # Also show games where the 2H favorite differs from the pregame favorite; this is the information
        # lost by the normalized unsigned h2_spread field.
        norm_homefav = ns["whos_favored"].astype(str).str.lower().eq("home").to_numpy()
        raw_homefav = raw["spread_side"].eq("home").to_numpy()
        flips = np.where(norm_homefav != raw_homefav)[0]
        print("PREGAME_TO_2H_FAVORITE_FLIPS", len(flips), "SAMPLE", flips[:30].tolist())
    print(raw.head(8).to_string(index=False))
