import pandas as pd
import holidays
no_holidays = holidays.NO()


# ---------------------------------------------------------------------
# Load & basic cleaning
# ---------------------------------------------------------------------
def load_flights(path: str) -> pd.DataFrame:
    """Load historical flights and clean datetime + cancelled."""
    df = pd.read_csv(path)
    df = df[df["cancelled"] == 0].copy()

    for col in ["std", "sta", "atd", "ata"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

# ---------------------------------------------------------------------
#  Handle wrong times
# ---------------------------------------------------------------------
def handle_wrong_times(df: pd.DataFrame) -> pd.DataFrame:
    """Handle cases where actual times are before scheduled times."""
    df['duration'] = df['sta'] - df['std']
    df = df[df['duration'] >= pd.Timedelta(0)].copy()
    df = df[df['duration'] <= pd.Timedelta(hours=10)].copy()

    return df

# ---------------------------------------------------------------------
# Interval construction
# ---------------------------------------------------------------------
def make_intervals(df: pd.DataFrame, actual: bool = True) -> pd.DataFrame:
    """Construct communication intervals (actual vs scheduled)."""
    if actual:
        dep = df.dropna(subset=["atd"]).copy()
        dep["start"] = dep["atd"] - pd.to_timedelta(15, "m")
        dep["end"]   = dep["atd"] + pd.to_timedelta(8, "m")
        dep["delay"] = (dep["atd"] - dep["std"]).dt.total_seconds() / 60

        arr = df.dropna(subset=["ata"]).copy()
        arr["start"] = arr["ata"] - pd.to_timedelta(16, "m")
        arr["end"]   = arr["ata"] + pd.to_timedelta(5, "m")
        arr["delay"] = (arr["ata"] - arr["sta"]).dt.total_seconds() / 60
    else:
        dep = df.dropna(subset=["std"]).copy()
        dep["start"] = dep["std"] - pd.to_timedelta(15, "m")
        dep["end"]   = dep["std"] + pd.to_timedelta(8, "m")
        dep["delay"] = 0 

        arr = df.dropna(subset=["sta"]).copy()
        arr["start"] = arr["sta"] - pd.to_timedelta(16, "m")
        arr["end"]   = arr["sta"] + pd.to_timedelta(5, "m")
        dep["delay"] = 0 

    dep["airport_group"] = dep["dep_airport_group"]
    dep["type"] = "departure"

    arr["airport_group"] = arr["arr_airport_group"]
    arr["type"] = "arrival"

    intervals = pd.concat([dep, arr], ignore_index=True)
    intervals = intervals.dropna(subset=["airport_group"])


    return intervals

def expand_to_hours(intervals: pd.DataFrame) -> pd.DataFrame:
    """Utvid hvert intervall til alle timene det overlapper."""
    rows = []
    for _, row in intervals.iterrows():
        hour_start = row["start"].floor("h")
        hour_end = row["end"].floor("h")
        hours = pd.date_range(hour_start, hour_end, freq="h")
        for h in hours:
            rows.append({**row, "hour": h})
    return pd.DataFrame(rows)

# ---------------------------------------------------------------------
# Overlap calculation
# ---------------------------------------------------------------------
def hourly_overlap(df: pd.DataFrame) -> pd.DataFrame: 
    """Beregn om det finnes overlapp innenfor hver airport_group × time.""" 
    results = [] 
    for (airport, hour), group in df.groupby(["airport_group", "hour"]): 
        events = [] 
        for _, row in group.iterrows(): 
            events.append((row["start"], +1)) 
            events.append((row["end"], -1)) 
            events.sort() 
            active, overlap = 0, 0 
            for _, change in events: 
                active += change 
                if active > 1: 
                    overlap = 1 
                    break 
            results.append({ "airport_group": airport, "hour": hour, "target": overlap }) 
    return pd.DataFrame(results)


def make_hourly_targets(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute hourly overlap targets (actual & scheduled)."""
    # Actual
    intervals_actual = make_intervals(df, actual=True)
    intervals_actual_expanded = expand_to_hours(intervals_actual)
    hourly_actual = intervals_actual_expanded.groupby("airport_group", group_keys=False).apply(hourly_overlap)
    hourly_actual = hourly_actual.rename(columns={"target": "target_actual"})
    print("")

    # Scheduled
    intervals_sched = make_intervals(df, actual=False)
    intervals_sched_expanded = expand_to_hours(intervals_sched)
    hourly_sched = intervals_sched_expanded.groupby("airport_group", group_keys=False).apply(hourly_overlap)
    hourly_sched = hourly_sched.rename(columns={"target": "target_sched"})

    # Merge

    hourly = hourly_actual.merge(hourly_sched, on=["airport_group", "hour"], how="left")
    hourly["target_sched"] = hourly["target_sched"].fillna(0).astype(int)

    return hourly, intervals_actual_expanded


# ---------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------
def make_hourly_features(intervals_actual: pd.DataFrame) -> pd.DataFrame:
    """Aggregate flight features per airport group + hour."""
    intervals_actual["duration_min"] = (
        (intervals_actual["sta"] - intervals_actual["std"]).dt.total_seconds() / 60
    )

    feats = intervals_actual.groupby(["airport_group", "hour"]).agg(
        flights_cnt     = ("flight_id", "count"),
        avg_duration    = ("duration_min", "mean"),
        max_duration    = ("duration_min", "max"),
        avg_delay       = ("delay", "mean"),   
        max_delay       = ("delay", "max"), 
        passenger_share = ("service_type", lambda x: (x == "J").mean()),
        cargo_share     = ("service_type", lambda x: (x == "P").mean()),
        charter_share   = ("service_type", lambda x: (x == "C").mean())
    ).reset_index()

    # Time features
    feats["dow"]     = feats["hour"].dt.dayofweek
    feats["holiday"] = feats["hour"].apply(lambda x: x.date() in no_holidays)
    feats["month"]   = feats["hour"].dt.month
    feats["hournum"] = feats["hour"].dt.hour
    feats["weekend"] = (feats["dow"] >= 5).astype(int)
    
    
    feats = feats.sort_values(["airport_group", "hour"])

    feats["date"] = feats["hour"].dt.normalize()

    feats["daily_flights_cnt"] = feats.groupby(
        ["airport_group", "date"]
    )["flights_cnt"].transform("sum")


    feats["flights_cnt_prev"] = (
        feats.groupby("airport_group")["flights_cnt"].shift(1)
    )
    feats["flights_cnt_next"] = (
        feats.groupby("airport_group")["flights_cnt"].shift(-1)
    )

    # valgfritt håndtering av kanter:
    feats[["flights_cnt_prev", "flights_cnt_next"]] = (
        feats[["flights_cnt_prev", "flights_cnt_next"]].fillna(0).astype(int)
    )

    return feats


# ---------------------------------------------------------------------
# Main preprocessing pipeline
# ---------------------------------------------------------------------
def preprocess(path: str, cutoff="2024-01-01") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Full preprocessing pipeline: load, targets, features, merge, split."""
    df = load_flights(path)
    df = handle_wrong_times(df)
    hourly, intervals_actual = make_hourly_targets(df)
    hourly_features = make_hourly_features(intervals_actual)

    hourly["hour"] = pd.to_datetime(hourly["hour"])
    hourly_features["hour"] = pd.to_datetime(hourly_features["hour"])


    dataset = hourly.merge(hourly_features, on=["airport_group", "hour"], how="left")
    dataset = dataset.sort_values("hour")

    train = dataset[dataset["hour"] < cutoff]
    validation  = dataset[dataset["hour"] >= cutoff]

    return train, validation


# ---------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import os
    print(os.getcwd())
    # Path to your raw data
    input_path = 'data/raw_data/historical_flights.csv'

    # Run preprocessing (this will also save train/test CSVs)
    train, val = preprocess(input_path, cutoff="2024-01-01")

    train.to_csv('data/processed_data/train.csv', index=False)
    val.to_csv('data/processed_data/val.csv', index=False)

