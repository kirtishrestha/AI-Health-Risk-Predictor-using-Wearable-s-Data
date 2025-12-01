from pathlib import Path
from typing import Dict, Optional, List

import pandas as pd

from supabase_client import get_supabase_client


# Base paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = BASE_DIR / "data" / "raw" / "fitbit"


def load_csv(path: Path) -> Optional[pd.DataFrame]:
    """
    Helper for safe CSV loading.
    Returns a pandas DataFrame if the file exists, otherwise prints a warning and returns None.
    """
    if not path.exists():
        print(f"[WARN] Missing Fitbit file: {path}")
        return None

    try:
        df = pd.read_csv(path)
        print(f"[INFO] Loaded {path.name} with {len(df)} rows")
        return df
    except Exception as e:
        print(f"[ERROR] Failed to read {path}: {e}")
        return None


def load_fitbit_daily_data(user_folder: Path) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Given a user folder like data/raw/fitbit/bella_a,
    attempt to load key Fitbit CSV files.

    We expect (based on the Kaggle Fitabase dataset):
      - dailyActivity_merged.csv
      - dailySteps_merged.csv
      - sleepDay_merged.csv          (may be missing for some users)
      - heartrate_seconds_merged.csv
    """
    data = {
        "activity": load_csv(user_folder / "dailyActivity_merged.csv"),
        "steps": load_csv(user_folder / "dailySteps_merged.csv"),
        "sleep": load_csv(user_folder / "sleepDay_merged.csv"),
        "heart_rate": load_csv(user_folder / "heartrate_seconds_merged.csv"),
    }
    return data


def build_daily_metrics(dfs: Dict[str, Optional[pd.DataFrame]]) -> pd.DataFrame:
    """
    Convert Fitbit raw daily DataFrames into the unified daily_metrics schema.

    Output columns:
      - date
      - steps
      - distance_km
      - active_energy_kcal
      - sleep_minutes
      - resting_hr
      - source = "fitbit"
    """
    all_dates = set()

    steps_df = dfs.get("steps")
    activity_df = dfs.get("activity")
    sleep_df = dfs.get("sleep")
    hr_df = dfs.get("heart_rate")

    # ---- Normalize date columns ----
    if steps_df is not None and not steps_df.empty:
        steps_df = steps_df.copy()
        steps_df["ActivityDay"] = pd.to_datetime(steps_df["ActivityDay"], errors="coerce")
        steps_df["date"] = steps_df["ActivityDay"].dt.date
        all_dates.update(steps_df["date"].dropna().tolist())

    if activity_df is not None and not activity_df.empty:
        activity_df = activity_df.copy()
        activity_df["ActivityDate"] = pd.to_datetime(activity_df["ActivityDate"], errors="coerce")
        activity_df["date"] = activity_df["ActivityDate"].dt.date
        all_dates.update(activity_df["date"].dropna().tolist())

    if sleep_df is not None and not sleep_df.empty:
        sleep_df = sleep_df.copy()
        sleep_df["SleepDay"] = pd.to_datetime(sleep_df["SleepDay"], errors="coerce")
        sleep_df["date"] = sleep_df["SleepDay"].dt.date
        all_dates.update(sleep_df["date"].dropna().tolist())

    if hr_df is not None and not hr_df.empty:
        hr_df = hr_df.copy()
        hr_df["Time"] = pd.to_datetime(hr_df["Time"], errors="coerce")
        hr_df["date"] = hr_df["Time"].dt.date
        all_dates.update(hr_df["date"].dropna().tolist())

    if not all_dates:
        print("[WARN] No dates found in Fitbit data.")
        return pd.DataFrame(columns=[
            "date",
            "steps",
            "distance_km",
            "active_energy_kcal",
            "sleep_minutes",
            "resting_hr",
            "source",
        ])

    daily = pd.DataFrame(sorted(all_dates), columns=["date"]).set_index("date")

    # ---- Steps ----
    if steps_df is not None and not steps_df.empty:
        # dailySteps_merged.csv → StepTotal
        steps_group = steps_df.groupby("date")["StepTotal"].sum()
        daily["steps"] = steps_group
    elif activity_df is not None and "TotalSteps" in activity_df.columns:
        # Fallback if dailySteps_merged.csv is missing (e.g., bella_a)
        steps_group = activity_df.groupby("date")["TotalSteps"].sum()
        daily["steps"] = steps_group

    # ---- Distance (miles → km) ----
    if activity_df is not None and not activity_df.empty:
        # Some versions use 'TotalDistance' instead of 'Distance'
        if "Distance" in activity_df.columns:
            dist_col = "Distance"
        elif "TotalDistance" in activity_df.columns:
            dist_col = "TotalDistance"
        else:
            dist_col = None

        if dist_col is not None:
            dist_group = activity_df.groupby("date")[dist_col].sum() * 1.60934
            daily["distance_km"] = dist_group
        else:
            print("[WARN] No Distance/TotalDistance column in dailyActivity_merged.csv")

        # Calories (per day)
        if "Calories" in activity_df.columns:
            cal_group = activity_df.groupby("date")["Calories"].sum()
            daily["active_energy_kcal"] = cal_group
        else:
            print("[WARN] No Calories column in dailyActivity_merged.csv")

    # ---- Sleep minutes ----
    if sleep_df is not None and not sleep_df.empty:
        if "TotalMinutesAsleep" in sleep_df.columns:
            sleep_group = sleep_df.groupby("date")["TotalMinutesAsleep"].sum()
            daily["sleep_minutes"] = sleep_group
        else:
            print("[WARN] No TotalMinutesAsleep column in sleepDay_merged.csv")

    # ---- Resting heart rate (min HR per day) ----
    if hr_df is not None and not hr_df.empty:
        if "Value" in hr_df.columns:
            hr_group = hr_df.groupby("date")["Value"].min()
            daily["resting_hr"] = hr_group
        else:
            print("[WARN] No Value column in heartrate_seconds_merged.csv")

    daily["source"] = "fitbit"

    daily = daily.reset_index()
    daily = daily.sort_values("date")
    return daily


# ---------- Supabase helpers ----------

def get_or_create_user_id(external_id: str) -> str:
    """
    Look up a user in Supabase 'users' table by external_id.
    If it does not exist, insert it.
    Return the user's id (uuid as a string).
    """
    supabase = get_supabase_client()
    res = supabase.table("users").select("*").eq("external_id", external_id).execute()
    if len(res.data) == 0:
        res = supabase.table("users").insert({"external_id": external_id}).execute()
    return res.data[0]["id"]


def upsert_daily_metrics(df: pd.DataFrame, user_external_id: str) -> None:
    """
    Upsert Fitbit daily metrics into the 'daily_metrics' table.
    Uses on_conflict="user_id,date,source".
    """
    if df is None or df.empty:
        print(f"[WARN] No daily metrics to upsert for {user_external_id}")
        return

    supabase = get_supabase_client()
    user_id = get_or_create_user_id(user_external_id)

    rows: List[dict] = []
    for _, row in df.iterrows():
        rows.append({
            "user_id": user_id,
            "date": str(row["date"]),
            "source": row.get("source", "fitbit"),
            "steps": None if pd.isna(row.get("steps")) else float(row["steps"]),
            "distance_km": None if pd.isna(row.get("distance_km")) else float(row["distance_km"]),
            "active_energy_kcal": None if pd.isna(row.get("active_energy_kcal")) else float(row["active_energy_kcal"]),
            "sleep_minutes": None if pd.isna(row.get("sleep_minutes")) else float(row["sleep_minutes"]),
            "resting_hr": None if pd.isna(row.get("resting_hr")) else float(row["resting_hr"]),
        })

    # Batch upsert (small dataset, single call is fine)
    supabase.table("daily_metrics").upsert(
        rows,
        on_conflict="user_id,date,source"
    ).execute()
    print(f"[INFO] Upserted {len(rows)} daily_metric rows for {user_external_id}")


def main():
    """
    Ingest Fitbit data for each known user (bella_a, bella_b)
    from data/raw/fitbit/<user>/ into the Supabase daily_metrics table.
    """
    users = ["bella_a", "bella_b"]

    for external_id in users:
        user_folder = DATA_RAW / external_id
        if not user_folder.exists():
            print(f"[WARN] Skipping {external_id}: folder {user_folder} does not exist.")
            continue

        print(f"\n[INFO] Processing Fitbit data for {external_id}...")
        dfs = load_fitbit_daily_data(user_folder)
        daily_df = build_daily_metrics(dfs)
        print(f"[INFO] Built daily metrics with {len(daily_df)} days for {external_id}.")

        upsert_daily_metrics(daily_df, user_external_id=external_id)

    print("\n✅ Fitbit ingestion complete.")


if __name__ == "__main__":
    main()
