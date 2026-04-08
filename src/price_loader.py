import pandas as pd
import yfinance as yf
import os
import time
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROCESSED_DATA_DIR


def get_tickers_from_signals() -> list[str]:
    signals_path = os.path.join(PROCESSED_DATA_DIR, "signals.csv")
    signals = pd.read_csv(signals_path)

    tickers = signals["ticker"].dropna().str.strip().str.upper().unique().tolist()

    return tickers


def download_ticker(ticker: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if data.empty:
            return None

        # flatten MultiIndex columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # remove duplicate columns
        data = data.loc[:, ~data.columns.duplicated()]

        # keep only what we need
        cols_to_keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
        data = data[cols_to_keep]

        # remove duplicate dates
        data = data[~data.index.duplicated(keep="first")]

        # add ticker and convert index to column
        data["ticker"] = ticker
        data = data.reset_index()

        # standardise the date column name
        date_col = data.columns[0]
        if date_col != "Date":
            data = data.rename(columns={date_col: "Date"})

        # remove timezone info from dates if present
        if pd.api.types.is_datetime64_any_dtype(data["Date"]):
            data["Date"] = data["Date"].dt.tz_localize(None)

        return data

    except Exception as e:
        print(f"  Error downloading {ticker}: {e}")
        return None


def download_all_prices():
    tickers = get_tickers_from_signals()
    print(f"Found {len(tickers)} unique tickers in signals")

    tickers.append("^GSPC")

    start_date = "2010-01-01"
    end_date = "2025-06-01"

    all_prices = []
    failed_tickers = []

    for i, ticker in enumerate(tickers):
        print(f"  [{i + 1}/{len(tickers)}] Downloading {ticker}...")

        data = download_ticker(ticker, start_date, end_date)

        if data is not None:
            all_prices.append(data)
        else:
            failed_tickers.append(ticker)
            print(f"    No data found for {ticker}")

        time.sleep(0.2)

    prices_df = pd.concat(all_prices, ignore_index=True)

    output_path = os.path.join(PROCESSED_DATA_DIR, "prices.csv")
    prices_df.to_csv(output_path, index=False)
    print(f"\nSaved price data to {output_path}")

    if failed_tickers:
        failed_path = os.path.join(PROCESSED_DATA_DIR, "failed_tickers.csv")
        pd.DataFrame({"ticker": failed_tickers}).to_csv(failed_path, index=False)
        print(f"{len(failed_tickers)} tickers failed - saved to {failed_path}")

    print(f"\nSuccessfully downloaded {len(all_prices)} out of {len(tickers)} tickers")

    return prices_df


if __name__ == "__main__":
    download_all_prices()