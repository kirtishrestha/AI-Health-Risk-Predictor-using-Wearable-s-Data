import pandas as pd
from supabase_client import get_supabase_client

def compute_risk_score(row):

    score = 0

    # Steps contribution (inverse: fewer steps → higher risk)
    if pd.notna(row.get("steps")):
        if row["steps"] < 3000:
            score += 30
        elif row["steps"] < 6000:
            score += 15
        else:
            score += 5

    # Sleep contribution
    if pd.notna(row.get("sleep_minutes")):
        sleep = row["sleep_minutes"]
        if sleep < 360:  # < 6 hours
            score += 30
        elif sleep < 420:  # < 7 hours
            score += 15
        else:
            score += 5

    # Resting HR contribution (higher → higher risk)
    if pd.notna(row.get("resting_hr")):
        if row["resting_hr"] > 85:
            score += 30
        elif row["resting_hr"] > 75:
            score += 15
        else:
            score += 5

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
            "model_name": "rule_based_v1",
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
