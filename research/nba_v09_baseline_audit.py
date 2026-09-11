import math
import numpy as np
import pandas as pd

URL = "https://raw.githubusercontent.com/Nijjar06/nba-game-predictor/main/data/nba_2008-2025.csv"
TARGETS = {
    "2017-18": {"start": "2017-10-01", "end": "2018-04-30", "n": 1230, "rmse": 9.883179436414059},
    "2018-19": {"start": "2018-10-01", "end": "2019-04-30", "n": 1230, "rmse": 10.19949385002746},
}

print("DOWNLOAD", URL)
df = pd.read_csv(URL)
print("SHAPE", df.shape)
print("COLUMNS", list(df.columns))
print("DTYPES", df.dtypes.astype(str).to_dict())

# Normalize dates without assuming a particular source format.
df["_date"] = pd.to_datetime(df["date"], errors="coerce")
print("DATE_RANGE", df["_date"].min(), df["_date"].max())
for c in ["season", "regular", "playoffs", "whos_favored", "h2_spread", "h2_total", "ot"]:
    if c in df.columns:
        vals = df[c].dropna()
        print("FIELD", c, "NONNULL", len(vals), "UNIQUE_SAMPLE", vals.astype(str).unique()[:30].tolist())

required = ["score_home", "score_away", "q1_home", "q1_away", "q2_home", "q2_away", "h2_spread"]
for c in required:
    if c not in df.columns:
        raise RuntimeError(f"Missing required column: {c}")

# Actual second-half home margin including overtime. This avoids any ambiguity
# about how the source represents OT periods.
df["ht_home_margin"] = (pd.to_numeric(df["q1_home"], errors="coerce") + pd.to_numeric(df["q2_home"], errors="coerce")) - (pd.to_numeric(df["q1_away"], errors="coerce") + pd.to_numeric(df["q2_away"], errors="coerce"))
df["final_home_margin"] = pd.to_numeric(df["score_home"], errors="coerce") - pd.to_numeric(df["score_away"], errors="coerce")
df["actual_2h_home_margin"] = df["final_home_margin"] - df["ht_home_margin"]
df["h2_spread_num"] = pd.to_numeric(df["h2_spread"], errors="coerce")


def is_regular(s):
    if "regular" not in s.columns:
        return pd.Series(True, index=s.index)
    v = s["regular"]
    # accept booleans, 1/0, and common text encodings
    return v.astype(str).str.strip().str.lower().isin(["true", "1", "1.0", "yes", "regular", "regular season"])


def rmse(a, b):
    x = pd.to_numeric(a, errors="coerce") - pd.to_numeric(b, errors="coerce")
    x = x.dropna()
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else float("nan")

# Test multiple line interpretations. The exact stored RMSE is our checksum.
def candidate_predictions(s):
    h = s["h2_spread_num"]
    out = {
        "expected=-h2": -h,
        "expected=+h2": h,
        "expected=-abs(h2)": -h.abs(),
        "expected=+abs(h2)": h.abs(),
    }
    if "whos_favored" in s.columns:
        fav = s["whos_favored"].astype(str).str.strip().str.lower()
        home_tokens = {"home", "h", "1", "home team"}
        away_tokens = {"away", "a", "2", "visitor", "v", "away team"}
        home_fav = fav.isin(home_tokens)
        away_fav = fav.isin(away_tokens)
        mag = h.abs()
        # Expected home margin is positive when home is favored, negative when away is favored.
        signed_margin = pd.Series(np.nan, index=s.index, dtype=float)
        signed_margin.loc[home_fav] = mag.loc[home_fav]
        signed_margin.loc[away_fav] = -mag.loc[away_fav]
        out["expected=favored_margin"] = signed_margin
        out["expected=-favored_margin"] = -signed_margin
    return out

for label, t in TARGETS.items():
    s = df[(df["_date"] >= pd.Timestamp(t["start"])) & (df["_date"] <= pd.Timestamp(t["end"]))].copy()
    print("\nSEASON", label, "date-window rows", len(s))
    if "regular" in s.columns:
        print("regular value counts", s["regular"].astype(str).value_counts(dropna=False).to_dict())
    if "playoffs" in s.columns:
        print("playoffs value counts", s["playoffs"].astype(str).value_counts(dropna=False).to_dict())
    regs = s[is_regular(s)].copy()
    print("regular rows", len(regs), "h2 nonnull", regs["h2_spread_num"].notna().sum(), "target n", t["n"])
    regs = regs.dropna(subset=["actual_2h_home_margin", "h2_spread_num"])
    print("modelable rows", len(regs))
    for name, pred in candidate_predictions(regs).items():
        valid = pred.notna() & regs["actual_2h_home_margin"].notna()
        val = rmse(regs.loc[valid, "actual_2h_home_margin"], pred.loc[valid])
        delta = abs(val - t["rmse"]) if math.isfinite(val) else float("inf")
        print("CANDIDATE", name, "N", int(valid.sum()), "RMSE", repr(val), "ABS_DELTA_TARGET", repr(delta))
    print("TARGET", repr(t["rmse"]))
    print("HEAD_CHECK")
    cols = [c for c in ["date","away","home","regular","playoffs","whos_favored","spread","h2_spread","q1_away","q1_home","q2_away","q2_home","score_away","score_home","actual_2h_home_margin"] if c in regs.columns]
    print(regs[cols].head(8).to_string(index=False))
