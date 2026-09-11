import math
import numpy as np
import pandas as pd

SEASONS = {
    "2017-18": {
        "url": "https://raw.githubusercontent.com/garfjohnson/Nba-Sports-Betting-Model/master/nba%20odds%202017-18.csv",
        "regular_last_mmdd": 411,
        "target_n": 1230,
        "target_rmse": 9.883179436414059,
    },
    "2018-19": {
        "url": "https://raw.githubusercontent.com/garfjohnson/Nba-Sports-Betting-Model/master/nba%20odds%202018-19.csv",
        "regular_last_mmdd": 410,
        "target_n": 1230,
        "target_rmse": 10.19949385002746,
    },
}


def num(v):
    if pd.isna(v):
        return np.nan
    s = str(v).strip().lower()
    if s in {"pk", "pick", "pick'em", "pickem"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return np.nan


def parse_season(label, cfg):
    d = pd.read_csv(cfg["url"], dtype=str)
    print("\nRAW", label, "rows", len(d), "cols", list(d.columns))
    # Keep only clean complete two-row games; the historical source is visitor row then home row.
    games = []
    bad = []
    for i in range(0, len(d) - 1, 2):
        a = d.iloc[i]
        h = d.iloc[i + 1]
        if str(a.get("VH", "")).strip().upper() != "V" or str(h.get("VH", "")).strip().upper() != "H":
            bad.append((i, "VH", a.get("VH"), h.get("VH")))
            continue
        try:
            date_a = int(float(a["Date"]))
            date_h = int(float(h["Date"]))
        except Exception:
            bad.append((i, "date", a.get("Date"), h.get("Date")))
            continue
        if date_a != date_h:
            bad.append((i, "date_mismatch", date_a, date_h))
            continue
        # Regular season: Oct-Dec (MMDD >= 1000) or Jan-Apr through official final date.
        if not (date_a >= 1000 or date_a <= cfg["regular_last_mmdd"]):
            continue

        h2a, h2h = num(a["2H"]), num(h["2H"])
        # In the raw SBR pair one row contains the 2H spread (small), the other the 2H total (~90-130).
        spread_candidates = []
        if math.isfinite(h2a) and abs(h2a) <= 30:
            spread_candidates.append(("away", abs(h2a)))
        if math.isfinite(h2h) and abs(h2h) <= 30:
            spread_candidates.append(("home", abs(h2h)))
        if len(spread_candidates) != 1:
            bad.append((i, "h2_identification", h2a, h2h))
            continue
        spread_side, mag = spread_candidates[0]
        # Home-team spread perspective: negative if home is favored, positive if away is favored.
        home_spread = -mag if spread_side == "home" else mag
        expected_home_2h_margin = -home_spread

        q1a, q2a, q1h, q2h = map(num, [a["1st"], a["2nd"], h["1st"], h["2nd"]])
        fa, fh = num(a["Final"]), num(h["Final"])
        vals = [q1a, q2a, q1h, q2h, fa, fh]
        if not all(math.isfinite(x) for x in vals):
            bad.append((i, "scores", vals))
            continue
        ht_home_margin = (q1h + q2h) - (q1a + q2a)
        actual_home_2h_margin = (fh - fa) - ht_home_margin  # includes OT automatically
        games.append({
            "date": date_a,
            "away": a["Team"],
            "home": h["Team"],
            "spread_side": spread_side,
            "h2_mag": mag,
            "home_spread": home_spread,
            "expected": expected_home_2h_margin,
            "actual": actual_home_2h_margin,
        })

    g = pd.DataFrame(games)
    err = g["actual"] - g["expected"]
    r = float(np.sqrt(np.mean(np.square(err))))
    print("PARSED", len(g), "TARGET_N", cfg["target_n"], "BAD", len(bad))
    print("SPREAD_SIDE_COUNTS", g["spread_side"].value_counts().to_dict())
    print("RMSE", repr(r), "TARGET", repr(cfg["target_rmse"]), "ABS_DELTA", repr(abs(r-cfg["target_rmse"])))
    print("EXACT_N", len(g) == cfg["target_n"], "RMSE_CLOSE_1E12", abs(r-cfg["target_rmse"]) < 1e-12)
    if bad:
        print("BAD_SAMPLE", bad[:20])
    print(g.head(8).to_string(index=False))
    return g, r

for label, cfg in SEASONS.items():
    parse_season(label, cfg)
