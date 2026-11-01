"""Data pipeline for the Hall of Fame project: extract -> clean -> join.

    python src/data_prep.py

Step 1  extract   unzip data/raw/lahman_2025.zip into data/raw/lahman_2025/
Step 2  clean     turn each raw table into one row per player (career totals, honours, position, label)
Step 3  join      join the cleaned tables on playerID, keep eligible players, save
                  data/processed/hof_players.csv

Eligible players: at least 10 AL/NL seasons (the HOF eligibility minimum) and a final
season in 1946-2010, so everyone has had their full BBWAA ballot window. The whole
career counts, including seasons before 1946.

Features are split into two groups that the project keeps separate:
  PERFORMANCE_FEATURES  career batting/pitching stats and primary position
  HONOURS_FEATURES      awards and All-Star selections (voted on by people)
Ballot vote counts are never used as features (they would leak the answer).
Label: HOF = 1 if ever inducted as a Player, by any route (BBWAA or a committee).
"""
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_ZIP = ROOT / "data" / "raw" / "lahman_2025.zip"
RAW = ROOT / "data" / "raw" / "lahman_2025"
PROCESSED = ROOT / "data" / "processed"
OUTPUT = PROCESSED / "hof_players.csv"

MIN_SEASONS = 10
FINAL_YEAR_RANGE = (1946, 2010)
TEST_FROM = 1996  # time-based split: train = final season <= 1995, test = 1996-2010

AWARD_MAP = {"Most Valuable Player": "MVP", "Cy Young Award": "CyYoung", "Gold Glove": "GoldGlove",
             "Rookie of the Year": "ROY", "World Series MVP": "WS_MVP"}
POSITIONS = ["p", "c", "1b", "2b", "3b", "ss", "of", "dh"]

BATTING_FEATURES = ["G", "PA", "R", "H", "HR", "RBI", "SB", "AVG", "OBP", "SLG"]
PITCHING_FEATURES = ["p_W", "p_L", "p_SV", "p_IPouts", "p_SO", "p_GS", "p_ERA", "p_WHIP"]
POSITION_FEATURES = ["is_pitcher"] + [f"pos_{p}" for p in POSITIONS]
PERFORMANCE_FEATURES = ["seasons"] + BATTING_FEATURES + PITCHING_FEATURES + POSITION_FEATURES
HONOURS_FEATURES = ["AllStar"] + list(AWARD_MAP.values())
ID_COLUMNS = ["playerID", "name", "first_year", "final_year", "pos", "split"]
LABEL_COLUMNS = ["HOF", "hof_year", "hof_route"]


# ---------------------------------------------------------------- Step 1: extract

def ensure_raw_data():
    """Unzip data/raw/lahman_2025.zip unless it has already been unzipped."""
    if not (RAW / "People.csv").exists():
        with zipfile.ZipFile(RAW_ZIP) as z:
            z.extractall(RAW.parent)
    return RAW


def load(name):
    ensure_raw_data()
    # People.csv has a UTF-8 BOM; utf-8-sig strips it from the first column name
    return pd.read_csv(RAW / f"{name}.csv", encoding="utf-8-sig", low_memory=False)


# ---------------------------------------------------------------- Step 2: clean

def al_nl(df):
    """Keep AL/NL seasons only (drops the 1870s National Association, Federal League, etc.)."""
    return df[df["lgID"].isin(["AL", "NL"])]


def clean_batting(bat):
    """Career batting totals and rate stats. Trade stints within a season are simply summed."""
    b = bat.groupby("playerID")[["G", "AB", "R", "H", "2B", "3B", "HR", "RBI", "SB", "BB", "HBP", "SF"]].sum()
    b["PA"] = b[["AB", "BB", "HBP", "SF"]].sum(axis=1)
    b["AVG"] = b["H"] / b["AB"].where(b["AB"] > 0)
    b["OBP"] = (b["H"] + b["BB"] + b["HBP"]) / b["PA"].where(b["PA"] > 0)
    b["SLG"] = (b["H"] + b["2B"] + 2 * b["3B"] + 3 * b["HR"]) / b["AB"].where(b["AB"] > 0)
    return b[BATTING_FEATURES]


def clean_pitching(pit):
    p = pit.groupby("playerID")[["W", "L", "SV", "IPouts", "H", "ER", "BB", "SO", "GS"]].sum()
    p["ERA"] = 27 * p["ER"] / p["IPouts"].where(p["IPouts"] > 0)
    p["WHIP"] = 3 * (p["H"] + p["BB"]) / p["IPouts"].where(p["IPouts"] > 0)
    return p[["W", "L", "SV", "IPouts", "SO", "GS", "ERA", "WHIP"]].add_prefix("p_")


def career_span(bat, pit):
    """Seasons played, first and final AL/NL season (batting or pitching)."""
    years = pd.concat([bat[["playerID", "yearID"]], pit[["playerID", "yearID"]]]).drop_duplicates()
    return years.groupby("playerID")["yearID"].agg(seasons="nunique", first_year="min", final_year="max")


def clean_honours(aw, allstar):
    """Award counts and number of All-Star seasons."""
    awards = (aw[aw["awardID"].isin(AWARD_MAP)].assign(a=lambda d: d["awardID"].map(AWARD_MAP))
              .pivot_table(index="playerID", columns="a", values="yearID", aggfunc="count", fill_value=0))
    allstar = allstar.groupby("playerID")["yearID"].nunique().rename("AllStar")
    return awards.join(allstar, how="outer")


def clean_position(app):
    """Primary position = the position with the most career games."""
    cols = [f"G_{p}" for p in POSITIONS]
    return app.groupby("playerID")[cols].sum().idxmax(axis=1).str[2:].rename("pos")


def clean_hof(hof):
    """First induction as a Player: year and route. Managers, executives and umpires are dropped."""
    ind = hof[(hof["category"] == "Player") & (hof["inducted"] == "Y")].sort_values("yearid")
    ind = ind.groupby("playerID").first()
    return ind[["yearid", "votedBy"]].rename(columns={"yearid": "hof_year", "votedBy": "hof_route"})


def clean_all():
    """Step 2: one cleaned, player-level table per source."""
    bat, pit = al_nl(load("Batting")), al_nl(load("Pitching"))
    return {
        "span": career_span(bat, pit),
        "batting": clean_batting(bat),
        "pitching": clean_pitching(pit),
        "honours": clean_honours(load("AwardsPlayers"), load("AllstarFull")),
        "position": clean_position(load("Appearances")),
        "hof": clean_hof(load("HallOfFame")),
        "people": load("People").set_index("playerID")[["nameFirst", "nameLast"]],
    }


# ---------------------------------------------------------------- Step 3: join

def join_all(tables):
    """Step 3: join on playerID, keep eligible players, fill and derive columns."""
    df = tables["span"]
    for name in ["batting", "pitching", "honours", "position", "hof", "people"]:
        df = df.join(tables[name], how="left")

    df = df[(df["seasons"] >= MIN_SEASONS) & df["final_year"].between(*FINAL_YEAR_RANGE)].copy()

    # Counting stats: no row means none (e.g. a position player never pitched)
    count_cols = ["G", "PA", "R", "H", "HR", "RBI", "SB"] + PITCHING_FEATURES[:6] + HONOURS_FEATURES
    df[count_cols] = df[count_cols].fillna(0).astype(int)
    # Rate stats stay NaN where they don't apply (pitchers' batting, hitters' ERA);
    # imputation is a modelling choice, not a cleaning one.
    df["is_pitcher"] = (df["pos"] == "p").astype(int)
    df[["AVG", "OBP", "SLG"]] = df[["AVG", "OBP", "SLG"]].where(df["is_pitcher"] == 0)
    df[["p_ERA", "p_WHIP"]] = df[["p_ERA", "p_WHIP"]].where(df["is_pitcher"] == 1)
    for p in POSITIONS:
        df[f"pos_{p}"] = (df["pos"] == p).astype(int)

    df["HOF"] = df["hof_year"].notna().astype(int)
    df["hof_year"] = df["hof_year"].astype("Int64")
    df["name"] = (df["nameFirst"].fillna("") + " " + df["nameLast"]).str.strip()
    df["split"] = (df["final_year"] >= TEST_FROM).map({False: "train", True: "test"})

    df = df.reset_index()
    return df[ID_COLUMNS + PERFORMANCE_FEATURES + HONOURS_FEATURES + LABEL_COLUMNS]


def build_table():
    return join_all(clean_all())


def load_table():
    """Read the processed table, running the pipeline first if it doesn't exist yet."""
    if not OUTPUT.exists():
        main()
    return pd.read_csv(OUTPUT, dtype={"hof_year": "Int64"})


def main():
    print(f"Step 1  extract: {ensure_raw_data()}")
    tables = clean_all()
    print("Step 2  clean:   " + ", ".join(f"{k} {len(v):,}" for k, v in tables.items()))
    df = join_all(tables)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    print(f"Step 3  join:    {len(df):,} eligible players x {df.shape[1]} columns -> {OUTPUT}")
    for split, g in df.groupby("split"):
        print(f"        {split:5s}: {len(g):5d} players, {g.HOF.sum():3d} inducted ({g.HOF.mean():.1%})")


if __name__ == "__main__":
    main()
