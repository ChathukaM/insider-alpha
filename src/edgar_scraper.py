import requests
import pandas as pd
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SEC_USER_AGENT, START_YEAR, END_YEAR, PROCESSED_DATA_DIR


def download_master_index(year: int, quarter: int) -> str | None:
    url = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/master.idx"
    headers = {"User-Agent": SEC_USER_AGENT}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to download {year} Q{quarter}: status {response.status_code}")
        return None


def parse_master_index(raw_text: str, year: int, quarter: int) -> list[dict]:
    filings = []
    data_started = False

    for line in raw_text.splitlines():
        if line.startswith("---"):
            data_started = True
            continue

        if not data_started:
            continue

        parts = line.split("|")
        if len(parts) != 5:
            continue

        cik, company_name, form_type, date_filed, filename = parts

        if form_type.strip() == "4":
            filings.append({
                "cik": cik.strip(),
                "company_name": company_name.strip(),
                "form_type": form_type.strip(),
                "date_filed": date_filed.strip(),
                "filename": filename.strip(),
                "year": year,
                "quarter": quarter,
            })

    return filings


def build_filing_index(start_year: int, end_year: int) -> pd.DataFrame:
    all_filings = []

    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            print(f"Downloading {year} Q{quarter}...")

            raw_text = download_master_index(year, quarter)
            if raw_text is None:
                continue

            filings = parse_master_index(raw_text, year, quarter)
            all_filings.extend(filings)

            print(f"  {year} Q{quarter}: found {len(filings)} Form 4 filings")
            time.sleep(0.1)

    df = pd.DataFrame(all_filings)

    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    output_path = os.path.join(PROCESSED_DATA_DIR, "filing_index.csv")
    df.to_csv(output_path, index=False)

    print(f"\nTotal: {len(df)} Form 4 filings saved to {output_path}")
    return df


if __name__ == "__main__":
    build_filing_index(START_YEAR, END_YEAR)