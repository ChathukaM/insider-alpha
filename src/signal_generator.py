import pandas as pd
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MIN_TRANSACTION_VALUE,
    CLUSTER_WINDOW_DAYS,
    CLUSTER_MIN_BUYERS,
    MIN_CLUSTER_VALUE,
    PROCESSED_DATA_DIR,
)


def load_purchases() -> pd.DataFrame:
    filepath = os.path.join(PROCESSED_DATA_DIR, "insider_purchases.csv")
    df = pd.read_csv(filepath, low_memory=False)

    df["FILING_DATE"] = pd.to_datetime(df["FILING_DATE"], format="%d-%b-%Y")
    df["TRANS_DATE"] = pd.to_datetime(df["TRANS_DATE"], format="%d-%b-%Y")

    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    initial_count = len(df)

    df = df[df["AFF10B5ONE"] != 1]
    print(f"  After removing 10b5-1 plans: {len(df)}")

    officer_director_mask = df["RPTOWNER_RELATIONSHIP"].str.contains(
        "Director|Officer", case=False, na=False
    )
    df = df[officer_director_mask]
    print(f"  After keeping officers/directors only: {len(df)}")

    df = df[df["DIRECT_INDIRECT_OWNERSHIP"] == "D"]
    print(f"  After keeping direct holdings only: {len(df)}")

    df["DOLLAR_VALUE"] = df["TRANS_SHARES"] * df["TRANS_PRICEPERSHARE"]
    df = df[df["DOLLAR_VALUE"] >= MIN_TRANSACTION_VALUE]
    print(f"  After ${MIN_TRANSACTION_VALUE:,} minimum: {len(df)}")

    df["SHARES_BEFORE"] = df["SHRS_OWND_FOLWNG_TRANS"] - df["TRANS_SHARES"]
    df["RELATIVE_INCREASE"] = df["TRANS_SHARES"] / df["SHARES_BEFORE"].clip(lower=1)

    print(f"\n  Filtered {initial_count} -> {len(df)} transactions")
    return df


def find_cluster_buys(df: pd.DataFrame) -> pd.DataFrame:
    signals = []

    for ticker, company_df in df.groupby("ISSUERTRADINGSYMBOL"):
        company_df = company_df.sort_values("FILING_DATE")

        for _, row in company_df.iterrows():
            filing_date = row["FILING_DATE"]
            window_start = filing_date - pd.Timedelta(days=CLUSTER_WINDOW_DAYS)

            window = company_df[
                (company_df["FILING_DATE"] >= window_start)
                & (company_df["FILING_DATE"] <= filing_date)
            ]

            distinct_buyers = window["RPTOWNERCIK"].nunique()
            total_value = window["DOLLAR_VALUE"].sum()

            if distinct_buyers >= CLUSTER_MIN_BUYERS and total_value >= MIN_CLUSTER_VALUE:
                signals.append({
                    "signal_date": filing_date,
                    "ticker": ticker,
                    "issuer_cik": row["ISSUERCIK"],
                    "company_name": row["ISSUERNAME"],
                    "num_buyers": distinct_buyers,
                    "total_value": total_value,
                    "max_relative_increase": window["RELATIVE_INCREASE"].max(),
                    "buyers": ", ".join(window["RPTOWNERNAME"].dropna().astype(str).unique()),
                    "titles": ", ".join(window["RPTOWNER_TITLE"].dropna().astype(str).unique()),
                })

    signals_df = pd.DataFrame(signals)

    signals_df = signals_df.drop_duplicates(subset=["ticker", "signal_date"])
    signals_df = signals_df.sort_values("signal_date").reset_index(drop=True)

    return signals_df


def generate_signals():
    print("Loading purchases...")
    df = load_purchases()

    print(f"\nApplying filters to {len(df)} purchases...")
    filtered = apply_filters(df)

    print(f"\nSearching for cluster buys...")
    signals = find_cluster_buys(filtered)

    output_path = os.path.join(PROCESSED_DATA_DIR, "signals.csv")
    signals.to_csv(output_path, index=False)

    print(f"\nFound {len(signals)} cluster buy signals")
    print(f"Saved to {output_path}")

    if not signals.empty:
        print(f"\nSignals per year:")
        signals["year"] = signals["signal_date"].dt.year
        print(signals.groupby("year").size().to_string())

    return signals


if __name__ == "__main__":
    generate_signals()