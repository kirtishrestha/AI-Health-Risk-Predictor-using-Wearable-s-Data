import zipfile
from pathlib import Path
from typing import Dict, List

import pandas as pd
from lxml import etree

from supabase_client import get_supabase_client

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = BASE_DIR / "data" / "raw"

def extract_apple_export() -> Path:

    zip_path = DATA_RAW / "apple_health_export.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"Apple Health zip not found at {zip_path}")

    extract_dir = DATA_RAW / "apple_health_export"
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Extract only once (idempotent)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    # Try to find export.xml inside extracted content
    xml_candidates = list(extract_dir.rglob("export.xml"))
    if not xml_candidates:
        raise FileNotFoundError("export.xml not found inside Apple Health export.")
    return xml_candidates[0]

APPLE_RECORD_TYPES = [
    "HKQuantityTypeIdentifierStepCount",
    "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKQuantityTypeIdentifierAppleExerciseTime",
    "HKQuantityTypeIdentifierRestingHeartRate",
    "HKQuantityTypeIdentifierVO2Max",
    "HKQuantityTypeIdentifierWalkingHeartRateAverage",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
    "HKCategoryTypeIdentifierSleepAnalysis",
]


def parse_apple_records(xml_path: Path) -> Dict[str, pd.DataFrame]:
    records: Dict[str, List[dict]] = {t: [] for t in APPLE_RECORD_TYPES}

    # iterparse for memory efficiency
    context = etree.iterparse(str(xml_path), tag="Record")
    for _, elem in context:
        r_type = elem.get("type")
        if r_type in APPLE_RECORD_TYPES:
            rec = {
                "type": r_type,
                "unit": elem.get("unit"),
                "startDate": elem.get("startDate"),
                "endDate": elem.get("endDate"),
                "value": elem.get("value"),
            }
            records[r_type].append(rec)

        # Free memory
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    dfs: Dict[str, pd.DataFrame] = {}
    for r_type, items in records.items():
        if items:
            df = pd.DataFrame(items)
            # Parse datetimes
            df["startDate"] = pd.to_datetime(df["startDate"])
            df["endDate"] = pd.to_datetime(df["endDate"])
            dfs[r_type] = df

    return dfs

def build_daily_metrics(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    # Collect all dates we see across different metrics
    date_index = set()

    def add_dates(df: pd.DataFrame, col: str = "startDate"):
        nonlocal date_index
        if df is not None and not df.empty:
            date_index.update(df[col].dt.date.tolist())

    # Add dates from all available types
    for key, df in dfs.items():
        add_dates(df)

    if not date_index:
        raise ValueError("No dates found in Apple Health records.")

    daily = pd.DataFrame(sorted(date_index), columns=["date"]).set_index("date")

    # ---- Steps ----
    steps_df = dfs.get("HKQuantityTypeIdentifierStepCount")
    if steps_df is not None and not steps_df.empty:
        steps_df = steps_df.copy()
        steps_df["value"] = pd.to_numeric(steps_df["value"], errors="coerce")
        steps_df["date"] = steps_df["startDate"].dt.date
        steps_group = steps_df.groupby("date")["value"].sum()
        daily["steps"] = steps_group

    # ---- Distance (km) ----
    dist_df = dfs.get("HKQuantityTypeIdentifierDistanceWalkingRunning")
    if dist_df is not None and not dist_df.empty:
        dist_df = dist_df.copy()
        dist_df["value"] = pd.to_numeric(dist_df["value"], errors="coerce")
        dist_df["date"] = dist_df["startDate"].dt.date
        dist_group = dist_df.groupby("date")["value"].sum()
        daily["distance_km"] = dist_group

    # ---- Active energy (kcal) ----
    active_e_df = dfs.get("HKQuantityTypeIdentifierActiveEnergyBurned")
    if active_e_df is not None and not active_e_df.empty:
        active_e_df = active_e_df.copy()
        active_e_df["value"] = pd.to_numeric(active_e_df["value"], errors="coerce")
        active_e_df["date"] = active_e_df["startDate"].dt.date
        active_energy_group = active_e_df.groupby("date")["value"].sum()
        daily["active_energy_kcal"] = active_energy_group

    # ---- Exercise time (minutes) ----
    exercise_df = dfs.get("HKQuantityTypeIdentifierAppleExerciseTime")
    if exercise_df is not None and not exercise_df.empty:
        exercise_df = exercise_df.copy()
        exercise_df["value"] = pd.to_numeric(exercise_df["value"], errors="coerce")
        exercise_df["date"] = exercise_df["startDate"].dt.date
        exercise_group = exercise_df.groupby("date")["value"].sum()
        daily["active_minutes"] = exercise_group

    # ---- Resting heart rate (bpm, daily avg) ----
    resting_df = dfs.get("HKQuantityTypeIdentifierRestingHeartRate")
    if resting_df is not None and not resting_df.empty:
        resting_df = resting_df.copy()
        resting_df["value"] = pd.to_numeric(resting_df["value"], errors="coerce")
        resting_df["date"] = resting_df["startDate"].dt.date
        resting_group = resting_df.groupby("date")["value"].mean()
        daily["resting_hr"] = resting_group

    # ---- VO2Max (optional, daily avg) ----
    vo2_df = dfs.get("HKQuantityTypeIdentifierVO2Max")
    if vo2_df is not None and not vo2_df.empty:
        vo2_df = vo2_df.copy()
        vo2_df["value"] = pd.to_numeric(vo2_df["value"], errors="coerce")
        vo2_df["date"] = vo2_df["startDate"].dt.date
        vo2_group = vo2_df.groupby("date")["value"].mean()
        daily["vo2max"] = vo2_group

    # ---- Walking HR average (optional) ----
    walking_hr_df = dfs.get("HKQuantityTypeIdentifierWalkingHeartRateAverage")
    if walking_hr_df is not None and not walking_hr_df.empty:
        walking_hr_df = walking_hr_df.copy()
        walking_hr_df["value"] = pd.to_numeric(walking_hr_df["value"], errors="coerce")
        walking_hr_df["date"] = walking_hr_df["startDate"].dt.date
        walking_hr_group = walking_hr_df.groupby("date")["value"].mean()
        daily["walking_hr_avg"] = walking_hr_group

    # ---- HRV SDNN (optional) ----
    hrv_df = dfs.get("HKQuantityTypeIdentifierHeartRateVariabilitySDNN")
    if hrv_df is not None and not hrv_df.empty:
        hrv_df = hrv_df.copy()
        hrv_df["value"] = pd.to_numeric(hrv_df["value"], errors="coerce")
        hrv_df["date"] = hrv_df["startDate"].dt.date
        hrv_group = hrv_df.groupby("date")["value"].mean()
        daily["hrv_sdnn"] = hrv_group

    # ---- Sleep minutes (from SleepAnalysis) ----
    sleep_df = dfs.get("HKCategoryTypeIdentifierSleepAnalysis")
    if sleep_df is not None and not sleep_df.empty:
        sleep_df = sleep_df.copy()
        # Duration in minutes
        sleep_df["duration_minutes"] = (
            sleep_df["endDate"] - sleep_df["startDate"]
        ).dt.total_seconds() / 60.0

        def is_asleep(v: str) -> bool:
            if v is None:
                return False
            return "Asleep" in v

        sleep_df = sleep_df[sleep_df["value"].apply(is_asleep)]
        sleep_df["date"] = sleep_df["startDate"].dt.date
        sleep_group = sleep_df.groupby("date")["duration_minutes"].sum()
        daily["sleep_minutes"] = sleep_group

    # Add source column
    daily["source"] = "apple"

    # Reset index for easier insertion
    daily = daily.reset_index()

    # Optional: sort by date
    daily = daily.sort_values("date")

    return daily


def upsert_daily_metrics_to_supabase(daily_df: pd.DataFrame, user_external_id: str = "kiki"):
    supabase = get_supabase_client()

    # Get or create user row
    user_res = supabase.table("users").select("*").eq("external_id", user_external_id).execute()
    if len(user_res.data) == 0:
        user_res = supabase.table("users").insert({"external_id": user_external_id}).execute()
    user_id = user_res.data[0]["id"]

    rows = []
    for _, row in daily_df.iterrows():
        rows.append({
            "user_id": user_id,
            "date": str(row["date"]),
            "source": "apple",
            "steps": int(row["steps"]) if not pd.isna(row.get("steps")) else None,
            "distance_km": float(row["distance_km"]) if not pd.isna(row.get("distance_km")) else None,
            "active_minutes": int(row["active_minutes"]) if not pd.isna(row.get("active_minutes")) else None,
            "active_energy_kcal": float(row["active_energy_kcal"]) if not pd.isna(row.get("active_energy_kcal")) else None,
            "sleep_minutes": float(row["sleep_minutes"]) if not pd.isna(row.get("sleep_minutes")) else None,
            "resting_hr": float(row["resting_hr"]) if not pd.isna(row.get("resting_hr")) else None,
        })

    if not rows:
        print("No rows to upsert into daily_metrics.")
        return

    BATCH_SIZE = 500
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        (
            supabase
            .table("daily_metrics")
            .upsert(batch, on_conflict="user_id,date,source")
            .execute()
        )
        print(f"Upserted batch {i}–{i+len(batch)-1}")

def main():
    print("Extracting Apple Health export...")
    xml_path = extract_apple_export()
    print(f"Using export.xml at: {xml_path}")

    print("Parsing Apple Health records (this may take a bit)...")
    dfs = parse_apple_records(xml_path)
    print("Finished parsing records.")

    print("Building daily metrics DataFrame...")
    daily = build_daily_metrics(dfs)
    print(f"Built daily metrics with {len(daily)} days.")

    print("Upserting into Supabase daily_metrics...")
    upsert_daily_metrics_to_supabase(daily)
    print("Done")


if __name__ == "__main__":
    main()
