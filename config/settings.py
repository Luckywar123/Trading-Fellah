"""Aggressive Sniper Bot v3.0 - Main Configuration"""

BOT_NAME = "Aggressive Sniper Bot v3.0"
VERSION = "3.0.0"
RUN_MODE = "LIVE"  # LIVE, PAPER, BACKTEST

# Market pairs
CRYPTO_PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
FOREX_PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]
STOCK_SYMBOLS = ["AAPL", "TSLA", "NVDA"]

# Timeframes
ENTRY_TIMEFRAME = "15m"
CONFIRMATION_TF = ["1h", "4h"]

# Engine cycle
SCAN_INTERVAL_SECONDS = 3

# Logging
LOG_LEVEL = "DEBUG"
LOG_FILE = "logs/sniper_v3.log"

# WebSocket port
WS_PORT = 8765

# Notifications
TELEGRAM = {"enabled": True, "token": "", "chat_id": ""}
DISCORD = {"enabled": True, "webhook": ""}
