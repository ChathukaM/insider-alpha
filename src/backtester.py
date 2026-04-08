import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import HOLDING_PERIOD_DAYS, PROCESSED_DATA_DIR


def load_data():
    signals = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "signals.csv"))
    prices = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "prices.csv"))
    failed = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "failed_tickers.csv"))

    # parse dates
    signals["signal_date"] = pd.to_datetime(signals["signal_date"])
    prices["Date"] = pd.to_datetime(prices["Date"], format="mixed")

    # remove signals where we have no price data
    failed_set = set(failed["ticker"].str.strip().str.upper())
    signals["ticker_clean"] = signals["ticker"].str.strip().str.upper()
    signals = signals[~signals["ticker_clean"].isin(failed_set)]

    return signals, prices


def get_trading_dates(ticker_prices: pd.DataFrame) -> pd.DatetimeIndex:
    """Get sorted list of trading dates for a ticker."""
    return ticker_prices["Date"].sort_values().reset_index(drop=True)


def simulate_trade(
    signal_date: pd.Timestamp,
    ticker: str,
    prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    holding_period: int,
) -> dict | None:
    """Simulate a single trade and return the result."""

    # get price data for this ticker
    ticker_prices = prices[prices["ticker"] == ticker].sort_values("Date")

    if ticker_prices.empty:
        return None

    trading_dates = ticker_prices["Date"].values

    # find the first trading day AFTER the signal date (next day open)
    future_dates = trading_dates[trading_dates > signal_date]

    if len(future_dates) < holding_period + 1:
        return None

    entry_date = future_dates[0]
    exit_date = future_dates[holding_period]

    # get entry price (open of entry day) and exit price (close of exit day)
    entry_row = ticker_prices[ticker_prices["Date"] == entry_date]
    exit_row = ticker_prices[ticker_prices["Date"] == exit_date]

    if entry_row.empty or exit_row.empty:
        return None

    entry_price = entry_row["Open"].values[0]
    exit_price = exit_row["Close"].values[0]

    if entry_price <= 0 or np.isnan(entry_price) or np.isnan(exit_price):
        return None

    # calculate stock return
    stock_return = (exit_price - entry_price) / entry_price

    # calculate benchmark return over same period
    bench = benchmark_prices[
        (benchmark_prices["Date"] >= entry_date)
        & (benchmark_prices["Date"] <= exit_date)
    ]

    if bench.empty:
        benchmark_return = 0.0
    else:
        bench_entry = bench.iloc[0]["Open"]
        bench_exit = bench.iloc[-1]["Close"]
        benchmark_return = (bench_exit - bench_entry) / bench_entry

    abnormal_return = stock_return - benchmark_return

    return {
        "ticker": ticker,
        "signal_date": signal_date,
        "entry_date": entry_date,
        "exit_date": exit_date,
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "stock_return": round(stock_return, 4),
        "benchmark_return": round(benchmark_return, 4),
        "abnormal_return": round(abnormal_return, 4),
    }


def run_backtest():
    print("Loading data...")
    signals, prices = load_data()

    # separate benchmark prices
    benchmark_prices = prices[prices["ticker"] == "^RUT"].copy()
    stock_prices = prices[prices["ticker"] != "^GSPC"].copy()

    print(f"Running backtest on {len(signals)} signals...")

    trades = []
    skipped = 0

    for i, row in signals.iterrows():
        ticker = row["ticker_clean"]
        signal_date = row["signal_date"]

        result = simulate_trade(
            signal_date, ticker, stock_prices, benchmark_prices, HOLDING_PERIOD_DAYS
        )

        if result is not None:
            # carry over signal metadata
            result["num_buyers"] = row["num_buyers"]
            result["total_value"] = row["total_value"]
            trades.append(result)
        else:
            skipped += 1

    trades_df = pd.DataFrame(trades)

    # save individual trades
    trades_path = os.path.join(PROCESSED_DATA_DIR, "trades.csv")
    trades_df.to_csv(trades_path, index=False)

    print(f"\nCompleted {len(trades_df)} trades ({skipped} skipped)")
    print(f"Trades saved to {trades_path}")

    # print summary statistics
    print_summary(trades_df)

    return trades_df


def print_summary(trades: pd.DataFrame):
    if trades.empty:
        print("No trades to summarise.")
        return

    print("\n" + "=" * 50)
    print("BACKTEST RESULTS")
    print("=" * 50)

    # basic stats
    total_trades = len(trades)
    winners = len(trades[trades["stock_return"] > 0])
    losers = len(trades[trades["stock_return"] <= 0])
    hit_rate = winners / total_trades

    print(f"\nTotal trades:    {total_trades}")
    print(f"Winners:         {winners}")
    print(f"Losers:          {losers}")
    print(f"Hit rate:        {hit_rate:.1%}")

    # return stats
    avg_return = trades["stock_return"].mean()
    avg_abnormal = trades["abnormal_return"].mean()
    median_return = trades["stock_return"].median()
    avg_winner = trades[trades["stock_return"] > 0]["stock_return"].mean()
    avg_loser = trades[trades["stock_return"] <= 0]["stock_return"].mean()

    print(f"\nAvg return:      {avg_return:.2%}")
    print(f"Avg abnormal:    {avg_abnormal:.2%}")
    print(f"Median return:   {median_return:.2%}")
    print(f"Avg winner:      {avg_winner:.2%}")
    print(f"Avg loser:       {avg_loser:.2%}")

    # risk stats
    std_return = trades["stock_return"].std()
    sharpe = (avg_return / std_return) * np.sqrt(252 / HOLDING_PERIOD_DAYS)
    max_drawdown = trades["stock_return"].min()
    best_trade = trades["stock_return"].max()

    print(f"\nSharpe ratio:    {sharpe:.2f}")
    print(f"Std deviation:   {std_return:.2%}")
    print(f"Best trade:      {best_trade:.2%}")
    print(f"Worst trade:     {max_drawdown:.2%}")

    # abnormal return significance
    t_stat = avg_abnormal / (trades["abnormal_return"].std() / np.sqrt(total_trades))
    print(f"\nAbnormal return t-stat: {t_stat:.2f}")
    if abs(t_stat) > 2:
        print("  -> Statistically significant at 5% level")
    else:
        print("  -> NOT statistically significant at 5% level")

    # yearly breakdown
    trades["year"] = pd.to_datetime(trades["signal_date"]).dt.year
    print("\nBy year:")
    yearly = trades.groupby("year").agg(
        trades=("stock_return", "count"),
        avg_return=("stock_return", "mean"),
        avg_abnormal=("abnormal_return", "mean"),
        hit_rate=("stock_return", lambda x: (x > 0).mean()),
    )
    for year, row in yearly.iterrows():
        print(
            f"  {year}: {int(row['trades'])} trades, "
            f"avg return {row['avg_return']:.2%}, "
            f"abnormal {row['avg_abnormal']:.2%}, "
            f"hit rate {row['hit_rate']:.1%}"
        )

    print("\n" + "=" * 50)


if __name__ == "__main__":
    run_backtest()