from typing import Any, Callable, Dict

import pandas as pd

from supabase_client import get_supabase_client


def _score_with_bands(
    value: Any,
    weight: float,
    bands: Dict[str, Callable[[float], bool]],
    missing_penalty: float = 0.5,
) -> float:
    """Return a weighted risk contribution using ordered boolean bands.

    Each callable in ``bands`` should evaluate to ``True`` when the band is a match.
    The first matching band determines the fraction of ``weight`` to apply.
    Missing values receive a neutral penalty so they do not collapse the total score.
    """

    if pd.isna(value):
        return weight * missing_penalty

    for fraction_label, predicate in bands.items():
        if predicate(float(value)):
            fraction = float(fraction_label)
            return weight * fraction

    # Default to a mid-level penalty when no band is matched
    return weight * 0.5


def compute_risk_score(row: pd.Series) -> float:
    """Compute a rule-based health risk score scaled to 0–100.

    The scoring incorporates movement, sleep, cardiovascular strain, and aerobic fitness
    to provide a more balanced view of daily wellness.
    """

    weights = {
        "steps": 20,
        "sleep_minutes": 20,
        "resting_hr": 20,
        "active_minutes": 10,
        "hrv_sdnn": 15,
        "vo2max": 10,
        "walking_hr_avg": 5,
    }

    score = 0.0

    score += _score_with_bands(
        row.get("steps"),
        weights["steps"],
        {
            "1.0": lambda v: v < 3000,
            "0.7": lambda v: v < 6000,
            "0.4": lambda v: v < 9000,
            "0.2": lambda v: True,
        },
    )

    score += _score_with_bands(
        row.get("sleep_minutes"),
        weights["sleep_minutes"],
        {
            "1.0": lambda v: v < 360,  # < 6h
            "0.7": lambda v: v < 420,  # 6–7h
            "0.4": lambda v: v < 540,  # 7–9h
            "0.2": lambda v: True,
        },
    )

    score += _score_with_bands(
        row.get("resting_hr"),
        weights["resting_hr"],
        {
            "1.0": lambda v: v > 90,
            "0.7": lambda v: v > 80,
            "0.4": lambda v: v > 70,
            "0.2": lambda v: True,
        },
    )

    score += _score_with_bands(
        row.get("active_minutes"),
        weights["active_minutes"],
        {
            "0.8": lambda v: v < 20,
            "0.6": lambda v: v < 40,
            "0.4": lambda v: v < 60,
            "0.2": lambda v: True,
        },
    )

    score += _score_with_bands(
        row.get("hrv_sdnn"),
        weights["hrv_sdnn"],
        {
            "1.0": lambda v: v < 20,
            "0.7": lambda v: v < 40,
            "0.5": lambda v: v < 60,
            "0.3": lambda v: True,
        },
    )

    score += _score_with_bands(
        row.get("vo2max"),
        weights["vo2max"],
        {
            "1.0": lambda v: v < 30,
            "0.7": lambda v: v < 35,
            "0.5": lambda v: v < 45,
            "0.3": lambda v: True,
        },
    )

    score += _score_with_bands(
        row.get("walking_hr_avg"),
        weights["walking_hr_avg"],
        {
            "1.0": lambda v: v > 120,
            "0.7": lambda v: v > 110,
            "0.5": lambda v: v > 100,
            "0.3": lambda v: True,
        },
    )

    return min(score, 100.0)


def get_daily_metrics(user_id: str) -> pd.DataFrame:
    supabase = get_supabase_client()
    res = (
        supabase
        .table("daily_metrics")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return pd.DataFrame(res.data)


def get_or_create_user(user_external_id: str = "kiki") -> str:
    supabase = get_supabase_client()
    res = supabase.table("users").select("*").eq("external_id", user_external_id).execute()
    if len(res.data) == 0:
        res = supabase.table("users").insert({"external_id": user_external_id}).execute()
    return res.data[0]["id"]


def upsert_risk_predictions(df: pd.DataFrame, user_id: str) -> None:
    supabase = get_supabase_client()

    rows = []
    for _, row in df.iterrows():
        rows.append({
            "user_id": user_id,
            "date": str(row["date"]),
            "model_name": "rule_based_v2",
            "risk_score": float(row["risk_score"]),
            "risk_level": row["risk_level"],
        })

    supabase.table("risk_predictions").upsert(rows, on_conflict="user_id,date").execute()


def categorize_risk_level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def main():
    user_id = get_or_create_user()

    print("📥 Fetching daily metrics from Supabase...")
    df = get_daily_metrics(user_id)

    print(f"Processing {len(df)} days...")

    # compute risk score
    df["risk_score"] = df.apply(compute_risk_score, axis=1)

    # assign levels
    df["risk_level"] = df["risk_score"].apply(categorize_risk_level)

    print("Uploading risk scores...")
    upsert_risk_predictions(df, user_id)
    print("Done! Risk scores uploaded ⚡")


if __name__ == "__main__":
    main()
