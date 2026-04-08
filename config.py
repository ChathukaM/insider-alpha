import os
from dotenv import load_dotenv


# SEC EDGAR settings
load_dotenv()
SEC_USER_AGENT = os.environ["SEC_USER_AGENT"]
SEC_RATE_LIMIT = 10

# Date range for historical backtest
START_YEAR = 2010
END_YEAR = 2024

# Signal parameters
MIN_TRANSACTION_VALUE = 100_000
HOLDING_PERIOD_DAYS = 60
CLUSTER_WINDOW_DAYS = 30
CLUSTER_MIN_BUYERS = 3
MIN_CLUSTER_VALUE = 500_000

# File paths
RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"
FACTORS_DATA_DIR = "data/factors"