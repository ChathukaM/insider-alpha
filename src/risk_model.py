import pandas as pd
import numpy as np
import statsmodels.api as sm
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROCESSED_DATA_DIR, FACTORS_DATA_DIR, HOLDING_PERIOD_DAYS


def load_data():
    trades = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "trades.csv"))
    trades["entry_date"] = pd.to_datetime(trades["entry_date"])
    trades["exit_date"] = pd.to_datetime(trades["exit_date"])

    factors = pd.read_csv(os.path.join(FACTORS_DATA_DIR, "ff5_daily.csv"))
    factors["Date"] = pd.to_datetime(factors["Date"])

    return trades, factors


def compute_trade_factor_exposures(trades: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """For each trade, compute the cumulative factor returns over the holding period."""
    results = []

    for _, trade in trades.iterrows():
        entry = trade["entry_date"]
        exit_date = trade["exit_date"]

        # get factor returns during this trade's holding period
        period_factors = factors[
            (factors["Date"] >= entry) & (factors["Date"] <= exit_date)
        ]

        if period_factors.empty:
            continue

        # cumulative factor returns over the holding period
        result = {
            "ticker": trade["ticker"],
            "entry_date": entry,
            "stock_return": trade["stock_return"],
            "Mkt-RF": period_factors["Mkt-RF"].sum(),
            "SMB": period_factors["SMB"].sum(),
            "HML": period_factors["HML"].sum(),
            "RMW": period_factors["RMW"].sum(),
            "CMA": period_factors["CMA"].sum(),
            "RF": period_factors["RF"].sum(),
        }

        # excess return = stock return minus risk-free rate
        result["excess_return"] = trade["stock_return"] - result["RF"]

        results.append(result)

    return pd.DataFrame(results)


def run_fama_french_regression(df: pd.DataFrame):
    """Run the 5-factor regression and print results."""
    y = df["excess_return"]
    X = df[["Mkt-RF", "SMB", "HML", "RMW", "CMA"]]
    X = sm.add_constant(X)

    model = sm.OLS(y, X).fit()

    print("=" * 60)
    print("FAMA-FRENCH 5-FACTOR REGRESSION")
    print("=" * 60)
    print(f"\nDependent variable: Trade excess returns (stock return - RF)")
    print(f"Number of observations: {len(df)}")
    print(f"R-squared: {model.rsquared:.4f}")
    print(f"\n{'Factor':<12} {'Coef':>10} {'t-stat':>10} {'p-value':>10}")
    print("-" * 44)

    factor_names = ["Alpha", "Mkt-RF", "SMB", "HML", "RMW", "CMA"]
    for name, coef, tval, pval in zip(
        factor_names, model.params, model.tvalues, model.pvalues
    ):
        sig = ""
        if pval < 0.01:
            sig = "***"
        elif pval < 0.05:
            sig = "**"
        elif pval < 0.10:
            sig = "*"
        print(f"{name:<12} {coef:>10.4f} {tval:>10.2f} {pval:>10.4f} {sig}")

    print("-" * 44)
    print(f"\nAlpha (intercept): {model.params.iloc[0]:.4f}")
    print(f"Alpha t-stat: {model.tvalues.iloc[0]:.2f}")

    if abs(model.tvalues.iloc[0]) > 2:
        print("-> Alpha IS statistically significant at 5% level")
    else:
        print("-> Alpha is NOT statistically significant at 5% level")

    # interpret factor loadings
    print("\nInterpretation:")
    if model.pvalues.iloc[2] < 0.05:
        direction = "small-cap" if model.params.iloc[2] > 0 else "large-cap"
        print(f"  - Significant SMB loading ({model.params.iloc[2]:.3f}): strategy tilts toward {direction} stocks")
    if model.pvalues.iloc[3] < 0.05:
        direction = "value" if model.params.iloc[3] > 0 else "growth"
        print(f"  - Significant HML loading ({model.params.iloc[3]:.3f}): strategy tilts toward {direction} stocks")
    if model.pvalues.iloc[1] < 0.05:
        print(f"  - Significant market beta ({model.params.iloc[1]:.3f}): strategy has market exposure")

    return model


def run_analysis():
    print("Loading data...")
    trades, factors = load_data()

    print("Computing factor exposures for each trade...")
    df = compute_trade_factor_exposures(trades, factors)

    print(f"Successfully matched {len(df)} trades to factor data\n")

    # full sample
    print("\n>>> FULL SAMPLE (2010-2024)")
    run_fama_french_regression(df)

    # ex-2020
    df["year"] = df["entry_date"].dt.year
    df_no_2020 = df[df["year"] != 2020]

    print("\n\n>>> EXCLUDING 2020")
    run_fama_french_regression(df_no_2020)

    # save for notebook
    output_path = os.path.join(PROCESSED_DATA_DIR, "trades_with_factors.csv")
    df.to_csv(output_path, index=False)
    print(f"\nSaved factor-adjusted data to {output_path}")


if __name__ == "__main__":
    run_analysis()