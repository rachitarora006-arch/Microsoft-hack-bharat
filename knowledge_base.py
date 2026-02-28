"""
knowledge_base.py — Comprehensive knowledge base for the AI Assistant.

Provides detailed information about:
  - The MarketIntel project architecture and features
  - Stock market concepts and education
  - Cryptocurrency fundamentals
  - Indian market specifics (NIFTY, SENSEX)
  - Technical analysis education
"""

# ═══════════════════════════════════════════════════════════
#  PROJECT KNOWLEDGE
# ═══════════════════════════════════════════════════════════

PROJECT_INFO = {
    "overview": (
        "📊 MarketIntel — Live Market Intelligence System\n\n"
        "MarketIntel is a real-time market intelligence platform that simulates live streaming "
        "of financial data and applies advanced analytics, anomaly detection, and AI-powered insights. "
        "It is built with Python (FastAPI) on the backend and vanilla HTML/CSS/JS on the frontend.\n\n"
        "Key Components:\n"
        "  • Streaming Engine — Custom concurrent data pipeline using Python threading\n"
        "  • Technical Indicators — SMA, EMA, RSI, MACD, Bollinger Bands computed in real-time\n"
        "  • Regime Detection — Classifies market state as Bullish, Bearish, Sideways, or High Volatility\n"
        "  • Anomaly Detection — Identifies price spikes, flash crashes, and volume surges\n"
        "  • Portfolio Engine — Tracks PnL, Value at Risk (VaR), drawdown, and risk scores\n"
        "  • Correlation Engine — Computes Pearson correlations between asset pairs\n"
        "  • RAG Module — Embeds news articles using MiniLM and stores in a FAISS-like vector index for semantic search\n"
        "  • AI Explanations — Uses OpenAI GPT-4o-mini for market narration and Q&A (with template fallback)\n"
        "  • WebSocket Server — Full-duplex real-time data broadcasting to the dashboard\n\n"
        "Tech Stack: Python, FastAPI, WebSockets, SentenceTransformers, OpenAI API, HTML/CSS/JS"
    ),
    "architecture": (
        "🏗️ MarketIntel Architecture:\n\n"
        "1. DATA INGESTION LAYER\n"
        "   • ingestion.py generates simulated market ticks (price + volume) every 2 seconds\n"
        "   • News articles are read from CSV files in the data/news directory\n"
        "   • Each tick includes: symbol, price, volume, timestamp\n\n"
        "2. PROCESSING LAYER\n"
        "   • streaming_engine.py orchestrates concurrent processing using Python threads\n"
        "   • indicators.py computes all technical indicators on each tick\n"
        "   • regime_detection.py classifies market state based on SMA slopes and volatility\n"
        "   • anomaly_detection.py checks for statistical outliers (Z-scores, volume surges)\n"
        "   • correlation_engine.py maintains rolling Pearson correlations\n"
        "   • portfolio_engine.py recalculates PnL and risk metrics per tick\n\n"
        "3. AI LAYER\n"
        "   • rag_module.py chunks and embeds news using SentenceTransformer (MiniLM)\n"
        "   • FAISS-like in-memory vector DB with hybrid search (vector + BM25)\n"
        "   • ai_explanations.py assembles context and prompts GPT-4o-mini\n\n"
        "4. PRESENTATION LAYER\n"
        "   • FastAPI serves REST APIs and WebSocket endpoint (/ws/market)\n"
        "   • Frontend dashboard connects via WebSocket for real-time updates\n"
        "   • All data is broadcast as JSON every tick cycle"
    ),
    "streaming_engine": (
        "⚡ Streaming Engine (streaming_engine.py):\n\n"
        "The streaming engine is the heart of MarketIntel. It runs concurrently and orchestrates:\n"
        "  • Market data generation (price ticks every 2 seconds)\n"
        "  • News file watching (monitors data/news directory for new CSVs)\n"
        "  • Callback-based processing (each tick triggers indicator, regime, anomaly calculations)\n"
        "  • WebSocket broadcasting (sends processed data to all connected clients)\n\n"
        "It uses Python's threading module for concurrent execution and maintains shared state "
        "that all modules can read from. The engine is designed to be fault-tolerant — if one "
        "processing module fails, others continue operating."
    ),
    "rag": (
        "🧠 RAG Module (Retrieval-Augmented Generation):\n\n"
        "When you ask the AI Assistant a question, here's what happens:\n"
        "  1. Your question is embedded into a vector using SentenceTransformer (MiniLM-L6-v2)\n"
        "  2. The vector is compared against all indexed news article chunks using cosine similarity\n"
        "  3. BM25 keyword search also runs in parallel for better recall\n"
        "  4. Results are fused using Reciprocal Rank Fusion (RRF)\n"
        "  5. Top-K relevant chunks are combined with live market state data\n"
        "  6. This context is sent to GPT-4o-mini with a system prompt\n"
        "  7. The LLM generates a contextual, data-backed answer\n\n"
        "If no OpenAI API key is configured, the system falls back to template-based answers "
        "using the same market data but without LLM generation."
    ),
}

# ═══════════════════════════════════════════════════════════
#  STOCK MARKET KNOWLEDGE
# ═══════════════════════════════════════════════════════════

STOCK_MARKET_KNOWLEDGE = {
    "basics": (
        "📈 Stock Market Basics:\n\n"
        "A stock market is a marketplace where shares of publicly listed companies are traded. "
        "Buyers and sellers come together to exchange ownership of company shares at agreed prices.\n\n"
        "Key Concepts:\n"
        "  • Share/Stock: A unit of ownership in a company\n"
        "  • Bull Market: A market where prices are rising (optimism)\n"
        "  • Bear Market: A market where prices are falling (pessimism)\n"
        "  • Index: A benchmark that tracks a group of stocks (e.g., NIFTY 50, SENSEX)\n"
        "  • IPO: Initial Public Offering — when a company first sells shares to the public\n"
        "  • Market Cap: Total value of a company's shares = Price × Total Shares\n"
        "  • Volume: Number of shares traded in a given period\n"
        "  • Liquidity: How easily an asset can be bought/sold without affecting its price\n"
        "  • Volatility: How much a price fluctuates — higher volatility = higher risk/reward\n"
        "  • Dividend: A portion of company profits paid to shareholders"
    ),
    "nifty": (
        "🇮🇳 NIFTY 50 (National Stock Exchange Fifty):\n\n"
        "NIFTY 50 is India's benchmark stock market index, managed by NSE (National Stock Exchange).\n\n"
        "Key Facts:\n"
        "  • Tracks the top 50 companies listed on the NSE by market cap\n"
        "  • Covers 13 sectors of the Indian economy\n"
        "  • Base year: 1995, Base value: 1000\n"
        "  • Calculated using free-float market capitalization methodology\n"
        "  • Major constituents include: Reliance, TCS, HDFC Bank, Infosys, ICICI Bank\n"
        "  • Trading hours: 9:15 AM to 3:30 PM IST (Monday-Friday)\n"
        "  • Regulated by SEBI (Securities and Exchange Board of India)\n\n"
        "NIFTY is used as a barometer for the overall health of the Indian economy. "
        "When NIFTY rises, it generally indicates investor confidence in Indian markets."
    ),
    "sensex": (
        "🇮🇳 SENSEX (Sensitive Index):\n\n"
        "SENSEX is the oldest stock market index in India, managed by BSE (Bombay Stock Exchange).\n\n"
        "Key Facts:\n"
        "  • Tracks the top 30 companies listed on the BSE\n"
        "  • Base year: 1978-79, Base value: 100\n"
        "  • One of the most widely followed indices in Asia\n"
        "  • Major constituents include: Reliance, TCS, HDFC Bank, Infosys, Bharti Airtel\n"
        "  • BSE is Asia's oldest stock exchange (established 1875)\n"
        "  • Also uses free-float market capitalization methodology\n\n"
        "SENSEX and NIFTY usually move in the same direction since they track similar large-cap companies, "
        "but SENSEX tracks fewer companies (30 vs 50)."
    ),
    "trading": (
        "💹 Types of Trading:\n\n"
        "  • Day Trading: Buying and selling within the same trading day. No overnight positions.\n"
        "  • Swing Trading: Holding positions for days to weeks, riding short-term trends.\n"
        "  • Position Trading: Holding for weeks to months based on fundamental analysis.\n"
        "  • Scalping: Making many small trades for tiny profits, usually lasting seconds to minutes.\n"
        "  • Algorithmic Trading: Using computer programs to execute trades based on predefined rules.\n\n"
        "Risk Management Principles:\n"
        "  • Never risk more than 1-2% of your portfolio on a single trade\n"
        "  • Always use stop-losses to limit downside\n"
        "  • Diversify across sectors and asset classes\n"
        "  • Position sizing should account for volatility\n"
        "  • Keep a trading journal to track and learn from your decisions"
    ),
    "orders": (
        "📋 Types of Orders:\n\n"
        "  • Market Order: Buy/sell immediately at the current market price\n"
        "  • Limit Order: Buy/sell at a specific price or better\n"
        "  • Stop-Loss Order: Automatically sell if price drops below a set level\n"
        "  • Stop-Limit Order: Combines stop-loss with a limit price\n"
        "  • Bracket Order: A set of 3 orders — entry, target, and stop-loss\n"
        "  • Cover Order: A market order with a compulsory stop-loss\n"
        "  • AMO (After Market Order): Placed outside trading hours for next-day execution"
    ),
}

# ═══════════════════════════════════════════════════════════
#  TECHNICAL ANALYSIS KNOWLEDGE
# ═══════════════════════════════════════════════════════════

TECHNICAL_ANALYSIS = {
    "overview": (
        "📉 Technical Analysis Overview:\n\n"
        "Technical analysis is the study of past market data (primarily price and volume) to predict "
        "future price movements. It assumes that all known information is already reflected in the price.\n\n"
        "Three Core Principles:\n"
        "  1. Market action discounts everything (price reflects all information)\n"
        "  2. Prices move in trends (uptrend, downtrend, sideways)\n"
        "  3. History tends to repeat itself (patterns recur)\n\n"
        "This system computes the following indicators in real-time:\n"
        "  • SMA (Simple Moving Average) — 20-period and 50-period\n"
        "  • EMA (Exponential Moving Average) — 12-period and 26-period\n"
        "  • RSI (Relative Strength Index) — 14-period\n"
        "  • MACD (Moving Average Convergence Divergence)\n"
        "  • Bollinger Bands — 20-period with 2 standard deviations"
    ),
    "sma": (
        "📊 SMA (Simple Moving Average):\n\n"
        "The SMA smooths out price data by calculating the average price over a specified number of periods.\n\n"
        "Formula: SMA = Sum of prices over N periods ÷ N\n\n"
        "How this system uses it:\n"
        "  • SMA-20 (short-term): Responds faster to price changes\n"
        "  • SMA-50 (long-term): Shows the broader trend direction\n\n"
        "Trading Signals:\n"
        "  • Golden Cross: SMA-20 crosses ABOVE SMA-50 → Bullish signal 📈\n"
        "  • Death Cross: SMA-20 crosses BELOW SMA-50 → Bearish signal 📉\n"
        "  • Price above both SMAs = Strong uptrend\n"
        "  • Price below both SMAs = Strong downtrend\n"
        "  • Price between SMAs = Indecision / consolidation"
    ),
    "ema": (
        "📊 EMA (Exponential Moving Average):\n\n"
        "EMA gives more weight to recent prices, making it more responsive than SMA.\n\n"
        "This system uses:\n"
        "  • EMA-12 (short-term) and EMA-26 (long-term) — used to compute MACD\n\n"
        "Key differences from SMA:\n"
        "  • Reacts faster to recent price changes\n"
        "  • Better for short-term trading decisions\n"
        "  • More commonly used in MACD calculations\n"
        "  • Gives earlier signals but may produce more false signals"
    ),
    "rsi": (
        "📊 RSI (Relative Strength Index):\n\n"
        "RSI measures the speed and magnitude of recent price changes on a 0-100 scale.\n\n"
        "Formula: RSI = 100 - (100 / (1 + RS)), where RS = Avg Gain / Avg Loss over 14 periods\n\n"
        "Interpretation:\n"
        "  • RSI > 70 → Overbought 🔴 (price may be too high, potential reversal down)\n"
        "  • RSI < 30 → Oversold 🟢 (price may be too low, potential reversal up)\n"
        "  • RSI 40-60 → Neutral zone\n"
        "  • RSI 50 → Midline, often acts as support/resistance\n\n"
        "Advanced Usage:\n"
        "  • Divergence: If price makes a new high but RSI doesn't → weakness, potential reversal\n"
        "  • Hidden divergence: Price makes higher low, RSI makes lower low → trend continuation\n"
        "  • RSI can stay overbought/oversold for extended periods in strong trends"
    ),
    "macd": (
        "📊 MACD (Moving Average Convergence Divergence):\n\n"
        "MACD shows the relationship between two EMAs and helps identify momentum shifts.\n\n"
        "Components:\n"
        "  • MACD Line = EMA-12 minus EMA-26\n"
        "  • Signal Line = 9-period EMA of the MACD Line\n"
        "  • Histogram = MACD Line minus Signal Line\n\n"
        "Trading Signals:\n"
        "  • Histogram > 0 (positive) → Bullish momentum 📈\n"
        "  • Histogram < 0 (negative) → Bearish momentum 📉\n"
        "  • MACD crosses above Signal → Buy signal\n"
        "  • MACD crosses below Signal → Sell signal\n"
        "  • Zero-line crossover → Trend change confirmation\n\n"
        "The histogram bars in this dashboard grow/shrink to show momentum strength."
    ),
    "bollinger": (
        "📊 Bollinger Bands:\n\n"
        "Bollinger Bands create an envelope around price using standard deviations.\n\n"
        "Components:\n"
        "  • Middle Band = 20-period SMA\n"
        "  • Upper Band = SMA + (2 × standard deviation)\n"
        "  • Lower Band = SMA - (2 × standard deviation)\n\n"
        "Interpretation:\n"
        "  • Price near Upper Band → Potentially overbought, may reverse down\n"
        "  • Price near Lower Band → Potentially oversold, may reverse up\n"
        "  • Band Squeeze (bands narrow) → Low volatility, breakout imminent\n"
        "  • Band Expansion → High volatility, strong trend\n"
        "  • ~95% of price action occurs within the bands"
    ),
    "regime": (
        "🏛️ Market Regime Detection:\n\n"
        "This system classifies each asset into one of four market regimes:\n\n"
        "  📈 BULLISH: Price trending upward\n"
        "    — SMA-20 above SMA-50 with positive slope\n"
        "    — Generally favorable for long positions\n\n"
        "  📉 BEARISH: Price trending downward\n"
        "    — SMA-20 below SMA-50 with negative slope\n"
        "    — Consider reducing exposure or hedging\n\n"
        "  ↔️ SIDEWAYS: No clear trend\n"
        "    — SMA slopes near zero, price oscillating in a range\n"
        "    — Range-bound trading strategies work best\n\n"
        "  🌊 HIGH_VOLATILITY: Extreme price swings\n"
        "    — Rolling volatility exceeds 2× baseline\n"
        "    — Often precedes major moves; trade with caution and tight stops"
    ),
    "anomaly": (
        "🚨 Anomaly Detection:\n\n"
        "The system monitors for three types of anomalies:\n\n"
        "  1. PRICE_SPIKE / PRICE_DROP:\n"
        "    — Triggered when price moves >2.5 standard deviations from the rolling mean\n"
        "    — Severity: LOW (2.5σ), MEDIUM (3.5σ), HIGH (5σ), CRITICAL (>7σ)\n\n"
        "  2. VOLUME_SURGE:\n"
        "    — Triggered when volume exceeds 3× the rolling average\n"
        "    — Often precedes or accompanies major price moves\n"
        "    — Can indicate institutional buying/selling\n\n"
        "  3. FLASH_CRASH:\n"
        "    — Triggered when price drops >5% within 60 seconds\n"
        "    — The most severe anomaly type\n"
        "    — Can be caused by panic selling, algorithmic errors, or liquidity crises"
    ),
    "portfolio": (
        "💼 Portfolio Risk Management:\n\n"
        "This system tracks several portfolio metrics:\n\n"
        "  • PnL (Profit & Loss): Current value minus initial investment cost\n"
        "  • PnL %: Percentage return on your total investment\n"
        "  • Total Value: Sum of all current position values\n\n"
        "  • VaR (Value at Risk) at 95%:\n"
        "    — The maximum expected loss over one day with 95% confidence\n"
        "    — Example: VaR of ₹50,000 means there's a 5% chance of losing more than ₹50K in a day\n\n"
        "  • Max Drawdown: Largest peak-to-trough decline in portfolio value\n"
        "    — Measures the worst loss you would have experienced\n\n"
        "  • Risk Score (0-100): A composite score combining volatility, drawdown, and VaR\n"
        "    — 0-30: Low risk (conservative) ✅\n"
        "    — 30-60: Moderate risk ⚠️\n"
        "    — 60-100: High risk 🔴"
    ),
}

# ═══════════════════════════════════════════════════════════
#  CRYPTO KNOWLEDGE
# ═══════════════════════════════════════════════════════════

CRYPTO_KNOWLEDGE = {
    "basics": (
        "🔗 Cryptocurrency Basics:\n\n"
        "A cryptocurrency is a digital or virtual currency that uses cryptography for security "
        "and operates on a decentralized network (blockchain).\n\n"
        "Key Concepts:\n"
        "  • Blockchain: A distributed, immutable ledger recording all transactions\n"
        "  • Decentralization: No single entity controls the network\n"
        "  • Mining/Staking: Mechanisms to validate transactions and secure the network\n"
        "  • Wallet: Software/hardware that stores your private keys for accessing crypto\n"
        "  • Private Key: A secret code that gives you ownership of your crypto\n"
        "  • Public Key: An address others use to send you crypto\n"
        "  • Gas Fees: Transaction fees paid to network validators\n"
        "  • Market Cap: Total value = Price × Circulating Supply\n"
        "  • DeFi: Decentralized Finance — financial services built on blockchain\n"
        "  • NFT: Non-Fungible Token — unique digital assets on blockchain\n"
        "  • Stablecoin: Crypto pegged to fiat currency (e.g., USDT, USDC)"
    ),
    "bitcoin": (
        "₿ Bitcoin (BTC):\n\n"
        "Bitcoin is the world's first and largest cryptocurrency, created in 2009 by the pseudonymous Satoshi Nakamoto.\n\n"
        "Key Facts:\n"
        "  • Total Supply: 21 million BTC (hard cap, deflationary)\n"
        "  • Current Circulating: ~19.6 million BTC\n"
        "  • Consensus: Proof of Work (PoW) — miners solve complex math problems\n"
        "  • Block Time: ~10 minutes per block\n"
        "  • Halving: Every ~4 years, mining reward is cut in half (next: ~2028)\n"
        "  • Smallest unit: 1 Satoshi = 0.00000001 BTC\n\n"
        "Why it matters:\n"
        "  • Often called 'digital gold' — a store of value\n"
        "  • Most liquid and widely traded crypto\n"
        "  • Institutional adoption growing (ETFs, corporate treasuries)\n"
        "  • High volatility compared to traditional assets\n"
        "  • Dominance: BTC typically represents 40-50% of total crypto market cap"
    ),
    "ethereum": (
        "⟠ Ethereum (ETH):\n\n"
        "Ethereum is a programmable blockchain platform created by Vitalik Buterin in 2015. "
        "It's not just a currency — it's a platform for decentralized applications (dApps).\n\n"
        "Key Facts:\n"
        "  • Consensus: Proof of Stake (PoS) since 'The Merge' in Sept 2022\n"
        "  • Smart Contracts: Self-executing code that runs on the blockchain\n"
        "  • Gas: Fees paid in ETH (measured in Gwei) for computation\n"
        "  • EVM: Ethereum Virtual Machine — runs smart contracts\n"
        "  • ERC-20: Standard for fungible tokens on Ethereum\n"
        "  • ERC-721: Standard for NFTs\n\n"
        "Ethereum powers:\n"
        "  • DeFi (Decentralized Finance) — lending, borrowing, DEXs\n"
        "  • NFTs (digital art, gaming assets)\n"
        "  • DAOs (Decentralized Autonomous Organizations)\n"
        "  • Layer 2 scaling solutions (Optimism, Arbitrum, zkSync)"
    ),
    "solana": (
        "◎ Solana (SOL):\n\n"
        "Solana is a high-performance blockchain designed for speed and low transaction costs.\n\n"
        "Key Facts:\n"
        "  • Speed: ~400ms block time, ~65,000 TPS (theoretical)\n"
        "  • Consensus: Proof of History (PoH) + Proof of Stake (PoS)\n"
        "  • Transaction Cost: Fractions of a penny (~₹0.01-0.02)\n"
        "  • Founded by Anatoly Yakovenko (ex-Qualcomm) in 2020\n\n"
        "Why it's popular:\n"
        "  • Extremely fast and cheap transactions\n"
        "  • Growing DeFi and NFT ecosystem\n"
        "  • Mobile-first strategy (Saga phone, Solana Mobile Stack)\n"
        "  • Used for high-frequency trading applications\n\n"
        "Risks:\n"
        "  • Has experienced network outages in the past\n"
        "  • More centralized than Ethereum (fewer validators)\n"
        "  • Higher volatility than BTC and ETH"
    ),
    "defi": (
        "🏦 DeFi (Decentralized Finance):\n\n"
        "DeFi recreates traditional financial services on blockchain without intermediaries.\n\n"
        "Major DeFi categories:\n"
        "  • DEX (Decentralized Exchange): Trade crypto without a centralized exchange (Uniswap, Jupiter)\n"
        "  • Lending/Borrowing: Supply assets to earn interest or borrow against collateral (Aave, Compound)\n"
        "  • Yield Farming: Earning rewards by providing liquidity to protocols\n"
        "  • Stablecoins: Crypto pegged to fiat (USDT, USDC, DAI)\n"
        "  • Liquid Staking: Stake tokens while retaining liquidity (Lido, Marinade)\n\n"
        "Risks in DeFi:\n"
        "  • Smart contract bugs and exploits\n"
        "  • Impermanent loss when providing liquidity\n"
        "  • Regulatory uncertainty\n"
        "  • Rug pulls and scam projects"
    ),
    "india_crypto": (
        "🇮🇳 Crypto in India:\n\n"
        "The Indian crypto market has unique characteristics:\n\n"
        "  • Taxation: 30% flat tax on crypto gains (no deductions for losses)\n"
        "  • TDS: 1% Tax Deducted at Source on all crypto transactions\n"
        "  • Exchanges: WazirX, CoinDCX, CoinSwitch, ZebPay\n"
        "  • Regulation: Crypto is legal but not legal tender; regulated under PMLA\n"
        "  • RBI Stance: Generally cautious; proposed CBDC (Digital Rupee)\n"
        "  • Digital Rupee (e₹): RBI's pilot CBDC launched in 2022\n\n"
        "Important notes for Indian investors:\n"
        "  • Losses from one crypto cannot be offset against gains from another\n"
        "  • No distinction between short-term and long-term gains (all 30%)\n"
        "  • Mining/staking rewards are taxed at fair market value"
    ),
}


# ═══════════════════════════════════════════════════════════
#  KNOWLEDGE ROUTER
# ═══════════════════════════════════════════════════════════

def get_knowledge_answer(question: str) -> str | None:
    """
    Route a question to the appropriate knowledge base entry.
    Returns the answer string, or None if no match found.
    """
    q = question.lower().strip()

    # ── Project-specific questions ──
    if any(w in q for w in ["marketintel", "what is this", "this project", "this system", "this app", "this platform", "about this"]):
        return PROJECT_INFO["overview"]
    if any(w in q for w in ["architecture", "how does it work", "how it works", "tech stack", "technology", "built with", "how is it built"]):
        return PROJECT_INFO["architecture"]
    if any(w in q for w in ["streaming engine", "streaming", "data pipeline", "pipeline", "how data flows"]):
        return PROJECT_INFO["streaming_engine"]
    if any(w in q for w in ["rag", "retrieval", "vector", "embedding", "how does ai work", "how does the ai"]):
        return PROJECT_INFO["rag"]

    # ── Stock market education ──
    if any(w in q for w in ["stock market basics", "what is stock", "what are stocks", "share market", "equity market", "how does stock market work"]):
        return STOCK_MARKET_KNOWLEDGE["basics"]
    if any(w in q for w in ["nifty 50", "nifty50", "what is nifty", "about nifty", "nse", "national stock exchange"]):
        return STOCK_MARKET_KNOWLEDGE["nifty"]
    if any(w in q for w in ["sensex", "bse", "bombay stock exchange", "what is sensex", "about sensex"]):
        return STOCK_MARKET_KNOWLEDGE["sensex"]
    if any(w in q for w in ["type of trading", "trading types", "day trading", "swing trading", "scalping", "how to trade"]):
        return STOCK_MARKET_KNOWLEDGE["trading"]
    if any(w in q for w in ["order type", "market order", "limit order", "stop loss", "stop-loss", "bracket order"]):
        return STOCK_MARKET_KNOWLEDGE["orders"]

    # ── Technical analysis education ──
    if any(w in q for w in ["technical analysis", "what is technical", "chart analysis", "price analysis"]):
        return TECHNICAL_ANALYSIS["overview"]
    if any(w in q for w in ["what is sma", "simple moving average", "moving average", "sma explain", "explain sma"]):
        return TECHNICAL_ANALYSIS["sma"]
    if any(w in q for w in ["what is ema", "exponential moving", "ema explain", "explain ema"]):
        return TECHNICAL_ANALYSIS["ema"]
    if any(w in q for w in ["what is rsi", "relative strength", "rsi explain", "explain rsi", "overbought", "oversold"]):
        return TECHNICAL_ANALYSIS["rsi"]
    if any(w in q for w in ["what is macd", "macd explain", "explain macd", "convergence divergence"]):
        return TECHNICAL_ANALYSIS["macd"]
    if any(w in q for w in ["bollinger", "what is bb", "band", "bb explain"]):
        return TECHNICAL_ANALYSIS["bollinger"]
    if any(w in q for w in ["what is regime", "regime explain", "market regime", "regime detection"]):
        return TECHNICAL_ANALYSIS["regime"]
    if any(w in q for w in ["anomaly explain", "what is anomaly", "how anomal", "flash crash explain", "spike explain", "how detect"]):
        return TECHNICAL_ANALYSIS["anomaly"]
    if any(w in q for w in ["portfolio explain", "what is var", "value at risk", "what is pnl", "what is drawdown", "risk score explain", "what is risk score"]):
        return TECHNICAL_ANALYSIS["portfolio"]

    # ── Crypto education ──
    if any(w in q for w in ["crypto basics", "what is crypto", "cryptocurrency", "what is blockchain", "blockchain"]):
        return CRYPTO_KNOWLEDGE["basics"]
    if any(w in q for w in ["what is bitcoin", "about bitcoin", "bitcoin explain", "tell me about btc", "btc history", "satoshi"]):
        return CRYPTO_KNOWLEDGE["bitcoin"]
    if any(w in q for w in ["what is ethereum", "about ethereum", "ethereum explain", "tell me about eth", "smart contract", "vitalik"]):
        return CRYPTO_KNOWLEDGE["ethereum"]
    if any(w in q for w in ["what is solana", "about solana", "solana explain", "tell me about sol"]):
        return CRYPTO_KNOWLEDGE["solana"]
    if any(w in q for w in ["what is defi", "decentralized finance", "defi explain", "yield farming", "liquidity"]):
        return CRYPTO_KNOWLEDGE["defi"]
    if any(w in q for w in ["crypto india", "crypto tax", "indian crypto", "wazirx", "crypto regulation india", "digital rupee"]):
        return CRYPTO_KNOWLEDGE["india_crypto"]

    return None
