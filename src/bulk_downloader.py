import requests
import zipfile
import os
import time
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SEC_USER_AGENT, START_YEAR, END_YEAR, RAW_DATA_DIR


def download_quarter(year: int, quarter: int) -> str | None:
    url = f"https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{year}q{quarter}_form345.zip"
    headers = {"User-Agent": SEC_USER_AGENT}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"  Failed: status {response.status_code}")
        return None

    zip_path = os.path.join(RAW_DATA_DIR, f"{year}q{quarter}_form345.zip")
    with open(zip_path, "wb") as f:
        f.write(response.content)

    return zip_path


def extract_quarter(zip_path: str, year: int, quarter: int) -> str:
    extract_dir = os.path.join(RAW_DATA_DIR, f"{year}q{quarter}")
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    os.remove(zip_path)
    return extract_dir


def download_all():
    os.makedirs(RAW_DATA_DIR, exist_ok=True)

    for year in range(START_YEAR, END_YEAR + 1):
        for quarter in range(1, 5):
            print(f"Downloading {year} Q{quarter}...")

            zip_path = download_quarter(year, quarter)
            if zip_path is None:
                continue

            extract_dir = extract_quarter(zip_path, year, quarter)
            files = os.listdir(extract_dir)
            print(f"  Extracted {len(files)} files to {extract_dir}")

            time.sleep(0.5)

    print("\nDone.")


if __name__ == "__main__":
    download_all()