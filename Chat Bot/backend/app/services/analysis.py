import io
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def analyze_dataframe(df: pd.DataFrame, query: str) -> str:
    """Perform data analysis on a DataFrame based on the user's query."""
    results = []

    query_lower = query.lower()

    # Always include basic info
    results.append(f"## Dataset Overview")
    results.append(f"- **Rows:** {len(df):,}")
    results.append(f"- **Columns:** {len(df.columns)}")
    results.append(f"- **Column names:** {', '.join(df.columns.tolist())}")
    results.append("")

    # Data types
    results.append("## Column Types")
    for col in df.columns:
        dtype = df[col].dtype
        nulls = df[col].isnull().sum()
        unique = df[col].nunique()
        results.append(f"- **{col}**: {dtype} ({unique} unique, {nulls} missing)")
    results.append("")

    # Numeric summary
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        results.append("## Numeric Summary")
        desc = df[numeric_cols].describe().round(2)
        results.append(desc.to_markdown())
        results.append("")

    # Correlations
    if len(numeric_cols) >= 2 and any(
        w in query_lower for w in ["correlat", "relat", "all", "summary", "full"]
    ):
        results.append("## Correlations (Top Pairs)")
        corr = df[numeric_cols].corr()
        pairs = []
        for i, c1 in enumerate(numeric_cols):
            for c2 in numeric_cols[i + 1 :]:
                pairs.append((c1, c2, corr.loc[c1, c2]))
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        for c1, c2, val in pairs[:10]:
            results.append(f"- {c1} ↔ {c2}: **{val:.3f}**")
        results.append("")

    # Categorical summary
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if cat_cols:
        results.append("## Categorical Columns")
        for col in cat_cols[:5]:
            top = df[col].value_counts().head(5)
            results.append(f"### {col} (top 5)")
            for val, count in top.items():
                results.append(f"- {val}: {count}")
            results.append("")

    # Missing data
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing) > 0:
        results.append("## Missing Values")
        for col, count in missing.items():
            pct = count / len(df) * 100
            results.append(f"- **{col}**: {count} ({pct:.1f}%)")
        results.append("")

    return "\n".join(results)


def load_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Load a file into a pandas DataFrame."""
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        return pd.read_csv(io.BytesIO(file_bytes))
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(io.BytesIO(file_bytes))
    else:
        raise ValueError(f"Cannot load {ext} as tabular data. Use CSV or Excel.")
