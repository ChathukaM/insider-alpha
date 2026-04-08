import pandas as pd
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import START_YEAR, END_YEAR, RAW_DATA_DIR, PROCESSED_DATA_DIR


def load_tsv(folder: str, filename: str) -> pd.DataFrame:
    filepath = os.path.join(folder, filename)
    return pd.read_csv(filepath, sep="\t", encoding="latin-1", low_memory=False)


def load_quarter(year: int, quarter: int) -> pd.DataFrame:
    folder = os.path.join(RAW_DATA_DIR, f"{year}q{quarter}")

    submissions = load_tsv(folder, "SUBMISSION.tsv")
    owners = load_tsv(folder, "REPORTINGOWNER.tsv")
    transactions = load_tsv(folder, "NONDERIV_TRANS.tsv")

    
    submissions = submissions[submissions["DOCUMENT_TYPE"] == "4"]

    
    transactions = transactions[transactions["TRANS_CODE"] == "P"]

    if transactions.empty:
        return pd.DataFrame()

    
    filings = submissions.merge(owners, on="ACCESSION_NUMBER", how="inner")

    
    merged = filings.merge(transactions, on="ACCESSION_NUMBER", how="inner")

    return merged


def build_dataset(start_year: int, end_year: int) -> pd.DataFrame:
    all_quarters = []

    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            print(f"Processing {year} Q{quarter}...")

            df = load_quarter(year, quarter)
            if df.empty:
                print(f"  No purchase transactions found")
                continue

            all_quarters.append(df)
            print(f"  Found {len(df)} purchase transactions")

    full_df = pd.concat(all_quarters, ignore_index=True)

    
    columns = [
        "ACCESSION_NUMBER",
        "FILING_DATE",
        "ISSUERCIK",
        "ISSUERTRADINGSYMBOL",
        "ISSUERNAME",
        "AFF10B5ONE",
        "RPTOWNERCIK",
        "RPTOWNERNAME",
        "RPTOWNER_RELATIONSHIP",
        "RPTOWNER_TITLE",
        "TRANS_DATE",
        "TRANS_CODE",
        "TRANS_SHARES",
        "TRANS_PRICEPERSHARE",
        "TRANS_ACQUIRED_DISP_CD",
        "SHRS_OWND_FOLWNG_TRANS",
        "DIRECT_INDIRECT_OWNERSHIP",
    ]

    
    available_columns = [c for c in columns if c in full_df.columns]
    full_df = full_df[available_columns]

    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    output_path = os.path.join(PROCESSED_DATA_DIR, "insider_purchases.csv")
    full_df.to_csv(output_path, index=False)

    print(f"\nTotal: {len(full_df)} purchase transactions saved to {output_path}")
    return full_df


if __name__ == "__main__":
    build_dataset(START_YEAR, END_YEAR)