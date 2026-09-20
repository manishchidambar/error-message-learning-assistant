import json
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "id",
    "language",
    "error_type",
    "error_pattern",
    "concept_nudge",
    "location_clue",
    "root_cause",
    "troubleshooting_checklist",
    "bad_code",
    "fixed_code",
]


def _normalize_checklist(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if pd.isna(value):
        return []
    parts = [p.strip() for p in str(value).replace("\n", "|").split("|")]
    return [p for p in parts if p]


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {', '.join(missing)}")

    normalized = df[REQUIRED_COLUMNS].copy()
    for col in REQUIRED_COLUMNS:
        if col == "troubleshooting_checklist":
            normalized[col] = normalized[col].apply(_normalize_checklist)
        else:
            normalized[col] = normalized[col].fillna("").astype(str)
    return normalized


def load_default_catalog(default_path: Path | None = None) -> pd.DataFrame:
    path = default_path or Path(__file__).resolve().parent / "data" / "default_errors.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return _normalize_dataframe(pd.DataFrame(data))


def load_uploaded_dataset(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".json"):
        content = json.load(uploaded_file)
        if isinstance(content, dict):
            content = [content]
        df = pd.DataFrame(content)
    elif file_name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        raise ValueError("Unsupported file type. Please upload CSV or JSON.")

    return _normalize_dataframe(df)


def merge_catalogs(default_df: pd.DataFrame, custom_df: pd.DataFrame | None) -> pd.DataFrame:
    if custom_df is None or custom_df.empty:
        return default_df.reset_index(drop=True)

    merged = pd.concat([default_df, custom_df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["id"], keep="last")
    return merged.reset_index(drop=True)
