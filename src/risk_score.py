import pandas as pd
from supabase_client import get_supabase_client


def score_band(value, bands):
    """Return the score for the first matching band.

    If the value is missing/NaN, return 0 so that missing metrics are neutral
    rather than penalized.
    """
    if pd.isna(value):
        return 0

    for predicate, points in bands:
        if predicate(value):
            return points

    return 0


RULE_BASED_V2_BANDS = {
    "steps": [
        (lambda v: v < 3000, 30),
        (lambda v: v < 6000, 15),
        (lambda v: True, 5),
    ],
    "sleep_minutes": [
        (lambda v: v < 360, 30),
        (lambda v: v < 420, 15),
        (lambda v: True, 5),
    ],
    "resting_hr": [
        (lambda v: v > 85, 30),
        (lambda v: v > 75, 15),
        (lambda v: True, 5),
    ],
    "active_minutes": [
        (lambda v: v < 30, 20),
        (lambda v: v < 60, 10),
        (lambda v: True, 5),
    ],
    "active_energy_kcal": [
        (lambda v: v < 300, 20),
        (lambda v: v < 600, 10),
        (lambda v: True, 5),
    ],
    "spo2_avg": [
        (lambda v: v < 94, 30),
        (lambda v: v < 96, 15),
        (lambda v: True, 5),
    ],
    "stress_avg": [
        (lambda v: v > 75, 30),
        (lambda v: v > 50, 15),
        (lambda v: True, 5),
    ],
    # Metrics not yet in daily_metrics (HRV, VO₂max, walking HR) are intentionally
    # omitted to avoid penalizing missing values.
}


def compute_risk_score(row):
    score = 0

    for metric, bands in RULE_BASED_V2_BANDS.items():
        score += score_band(row.get(metric), bands)

    # Normalize to 0–100
    return min(score, 100)


def get_daily_metrics(user_id):
    supabase = get_supabase_client()
    res = supabase.table("daily_metrics").select("*").eq("user_id", user_id).execute()
    return pd.DataFrame(res.data)


def get_or_create_user(user_external_id="kiki"):
    supabase = get_supabase_client()
    res = supabase.table("users").select("*").eq("external_id", user_external_id).execute()
    if len(res.data) == 0:
        res = supabase.table("users").insert({"external_id": user_external_id}).execute()
    return res.data[0]["id"]


def upsert_risk_predictions(df, user_id):
    supabase = get_supabase_client()

    rows = []
    for _, row in df.iterrows():
        rows.append({
            "user_id": user_id,
            "date": str(row["date"]),
            "model_name": "rule_based_v2",
            "risk_score": float(row["risk_score"]),
            "risk_level": row["risk_level"]
        })


    supabase.table("risk_predictions").upsert(rows, on_conflict="user_id,date").execute()


def main():
    user_id = get_or_create_user()

    print("📥 Fetching daily metrics from Supabase...")
    df = get_daily_metrics(user_id)

    print(f"Processing {len(df)} days...")

    # compute risk score
    df["risk_score"] = df.apply(compute_risk_score, axis=1)

    # assign levels
    df["risk_level"] = df["risk_score"].apply(
        lambda s: "high" if s >= 70 else ("medium" if s >= 40 else "low")
    )

    print("Uploading risk scores...")
    upsert_risk_predictions(df, user_id)
    print("Done! Risk scores uploaded ⚡")


if __name__ == "__main__":
    main()
