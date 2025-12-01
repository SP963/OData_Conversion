import os
import argparse
import pandas as pd
import psycopg2
import io
from typing import List

TARGET_TABLE = 'public."TRP"'
TARGET_COLS = [
    "outlet",
    "date",
    "day",
    "guest_count",
    "category",
    "quantity",
    "cost_price",
    "selling_price",
    "total_sales",
    "total_cost_price",
    "profit",
]


def normalize_cols(cols: List[str]) -> List[str]:
    out = []
    for c in cols:
        s = str(c).strip()
        s = " ".join(s.split())  # collapse internal whitespace
        s = s.lower().replace(" ", "_")
        out.append(s)
    return out


def map_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = normalize_cols(df.columns)

    # Best-effort mapping from common variations to target columns
    col_map = {}
    for tgt in TARGET_COLS:
        # exact match
        if tgt in df.columns:
            col_map[tgt] = tgt
            continue
        # find approximate match
        for c in df.columns:
            if (
                tgt in c
                or c in tgt
                or tgt.split("_")[0] in c
                or tgt.split("_")[-1] in c
            ):
                col_map[tgt] = c
                break

    # build output DF with target order
    out = pd.DataFrame()
    for tgt in TARGET_COLS:
        src = col_map.get(tgt)
        if src is not None:
            out[tgt] = df[src]
        else:
            out[tgt] = pd.NA

    # parse date column (DD-MM-YYYY)
    out["date"] = pd.to_datetime(out["date"], dayfirst=True, errors="coerce").dt.date

    # numeric conversions
    for c in ["guest_count", "quantity"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")
    for c in [
        "cost_price",
        "selling_price",
        "total_sales",
        "total_cost_price",
        "profit",
    ]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # clean text fields
    for c in ["outlet", "day", "category"]:
        out[c] = out[c].astype(str).str.strip().replace({"nan": pd.NA})

    return out


def copy_df_to_postgres(
    df: pd.DataFrame, conn, table: str = TARGET_TABLE, cols: List[str] = TARGET_COLS
):
    # convert DataFrame to CSV in-memory, ensure header matches TARGET_COLS and date format YYYY-MM-DD
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=True, date_format="%Y-%m-%d")
    buf.seek(0)
    with conn.cursor() as cur:
        sql = f"COPY {table}({', '.join(cols)}) FROM STDIN WITH CSV HEADER"
        cur.copy_expert(sql, buf)
    conn.commit()


def get_conn():
    """Create database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", 5432)),
        dbname=os.getenv("PGDATABASE", "main"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
        sslmode=os.getenv("PGSSL", "require"),
    )


def main():
    # 🔥 HARD-CODE YOUR EXCEL FILE PATH HERE
    excel_path = "C:/Users/satya.mani/Downloads/DHPLData.xlsx"

    # 🔥 HARD-CODE SHEET NUMBER OR SHEET NAME HERE
    sheet_arg = 0  # use 0 for first sheet, or "Sheet1" for a named sheet

    # Read Excel directly
    df_raw = pd.read_excel(excel_path, sheet_name=sheet_arg, header=0)

    df = map_dataframe(df_raw)

    print("Preview of normalized data (first 5 rows):")
    print(df.head(5).to_string(index=False))

    conn = get_conn()
    try:
        copy_df_to_postgres(df, conn)
        print("COPY load completed successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
