"""
Central configuration for the Market Intelligence System.
All tunable parameters, API keys, and asset definitions live here.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

# ═══════════════════════════════════════════════════════════
#  CURRENCY
# ═══════════════════════════════════════════════════════════
CURRENCY_SYMBOL = "₹"

# ═══════════════════════════════════════════════════════════
#  API KEYS
# ═══════════════════════════════════════════════════════════
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-1234efgh5678ijkl1234efgh5678ijkl1234efgh")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ═══════════════════════════════════════════════════════════
#  ASSETS
# ═══════════════════════════════════════════════════════════
ASSETS = ["BTC", "ETH", "SOL", "NIFTY", "SENSEX"]

# Initial simulated prices (in INR)
INITIAL_PRICES = {
    "BTC": 5602500.0,     # ~67500 USD × 83
    "ETH": 286350.0,      # ~3450 USD × 83
    "SOL": 12035.0,       # ~145 USD × 83
    "NIFTY": 22300.0,     # Already INR
    "SENSEX": 73500.0,    # Already INR
}

# Base volumes for simulation
BASE_VOLUMES = {
    "BTC": 1500.0,
    "ETH": 25000.0,
    "SOL": 500000.0,
    "NIFTY": 100000.0,
    "SENSEX": 50000.0,
}

# Volatility profiles (daily %)
VOLATILITY_PROFILES = {
    "BTC": 0.025,
    "ETH": 0.030,
    "SOL": 0.045,
    "NIFTY": 0.012,
    "SENSEX": 0.011,
}

# ═══════════════════════════════════════════════════════════
#  STREAMING PARAMETERS
# ═══════════════════════════════════════════════════════════
TICK_INTERVAL_SECONDS = 2          # How often to generate a tick
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
NEWS_DIR = os.path.join(DATA_DIR, "news")
PORTFOLIO_CSV = os.path.join(DATA_DIR, "portfolio.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# ═══════════════════════════════════════════════════════════
#  INDICATOR WINDOWS
# ═══════════════════════════════════════════════════════════
SMA_SHORT_WINDOW = 20
SMA_LONG_WINDOW = 50
EMA_SHORT_SPAN = 12
EMA_LONG_SPAN = 26
EMA_SIGNAL_SPAN = 9
RSI_PERIOD = 14
BOLLINGER_WINDOW = 20
BOLLINGER_STD_DEV = 2.0
VOLATILITY_WINDOW = 20

# ═══════════════════════════════════════════════════════════
#  REGIME DETECTION
# ═══════════════════════════════════════════════════════════
REGIME_VOLATILITY_CRASH_MULT = 3.0
REGIME_VOLATILITY_HIGH_MULT = 2.0
REGIME_PRICE_DROP_CRASH = 0.05      # 5% price drop → crash
REGIME_SMA_SLOPE_THRESHOLD = 0.001  # Minimum slope to declare trend

# ═══════════════════════════════════════════════════════════
#  ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════
PRICE_SPIKE_THRESHOLD = 2.5       # Number of std devs for spike
VOLUME_SURGE_MULTIPLIER = 3.0     # Volume > N × mean
VOL_BREAKOUT_THRESHOLD = 2.0      # Rolling vol > N × baseline
FLASH_CRASH_DROP_PCT = 0.05       # 5% drop
FLASH_CRASH_WINDOW_SEC = 60       # Within 60 seconds

# ═══════════════════════════════════════════════════════════
#  PORTFOLIO
# ═══════════════════════════════════════════════════════════
VAR_CONFIDENCE = 0.95             # 95% VaR
RISK_SCORE_MAX = 100

# ═══════════════════════════════════════════════════════════
#  CORRELATION
# ═══════════════════════════════════════════════════════════
CORRELATION_PAIRS = [("BTC", "ETH"), ("NIFTY", "SENSEX")]
CORRELATION_WINDOW = 30           # Number of data points
CORRELATION_BREAK_THRESHOLD = 0.3 # Change threshold

# ═══════════════════════════════════════════════════════════
#  RAG & LLM
# ═══════════════════════════════════════════════════════════
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
RAG_TOP_K = 5
CHUNK_SIZE = 300         # Tokens per chunk
CHUNK_OVERLAP = 50

# ═══════════════════════════════════════════════════════════
#  NARRATOR
# ═══════════════════════════════════════════════════════════
NARRATOR_INTERVAL_SECONDS = 300   # 5 minutes

# ═══════════════════════════════════════════════════════════
#  SERVER
# ═══════════════════════════════════════════════════════════
API_HOST = "0.0.0.0"
API_PORT = int(os.getenv("PORT", 8000))

# ═══════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
