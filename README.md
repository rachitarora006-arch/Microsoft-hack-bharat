# 📈 Live Stock & Crypto Market Intelligence System

> **Real-time, event-driven market intelligence platform** with streaming financial analysis, anomaly detection, portfolio risk management, and AI-powered insights — built with Python, FastAPI, WebSockets, and a custom cross-platform streaming engine.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-Live-brightgreen?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

---

##  OVERVIEW

This is a **production-ready, full-stack market intelligence system** that continuously ingests market data, computes technical indicators, detects anomalies and regime shifts, manages portfolio risk, and delivers AI-powered insights — all via a stunning dark-mode fintech dashboard with **live WebSocket streaming**.

### Key Highlights

- 🔴 **Real-Time Streaming** — Prices, indicators, alerts, and portfolio metrics update instantly via WebSocket (no page refresh)
- 📊 **12 Technical Indicators** — SMA, EMA, RSI, MACD, Bollinger Bands, rolling volatility, all computed incrementally
- 🏛️ **Market Regime Detection** — Automatically classifies each asset as Bullish, Bearish, Sideways, High Volatility, or Crash
- 🚨 **Anomaly Detection** — Price spikes, volume surges, volatility breakouts, and flash crashes with severity grading (LOW → EXTREME)
- 💼 **Portfolio Risk Engine** — Live PnL, Value at Risk (VaR), drawdown, and composite risk scoring
- 🔗 **Cross-Asset Correlation** — Rolling Pearson correlation with break alerts for configured pairs
- 🤖 **AI-Powered Q&A** — RAG-based chat assistant using news retrieval + market context
- 📝 **Market Narrator** — Auto-generated 5-minute market summaries
- 🔔 **Toast Notifications** — Instant browser alerts for high-severity anomalies

---

## 🖥️ Dashboard Preview

The system features a professional **dark-mode fintech dashboard** with 7 real-time panels:

| Panel | Features |
|-------|----------|
| **Price Cards** | Live prices, sparkline charts, regime badges, RSI, volume, flash animations (green/red) |
| **Technical Indicators** | 12 metrics with trend arrows (▲/▼), RSI progress bar |
| **Live Alerts** | Severity-coded feed (blue/yellow/orange/red) with toast popups |
| **Portfolio** | Summary cards, SVG risk gauge (0-100), positions table with per-asset PnL |
| **Correlations** | BTC-ETH and NIFTY-SENSEX with gradient bars and delta tracking |
| **Market Narrator** | Auto-generated prose summary updated every 5 minutes |
| **AI Chat** | Natural language Q&A about markets, portfolio, anomalies |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                  CUSTOM STREAMING ENGINE (Cross-Platform)            │
│                                                                      │
│  ┌──────────┐    ┌────────────┐    ┌─────────────────────────────┐  │
│  │ Simulated │───▶│ Indicators │───▶│ Regime Detection            │  │
│  │ Market    │    │ SMA/EMA/   │    │ Bullish/Bearish/Sideways/   │  │
│  │ Data Gen  │    │ RSI/MACD/  │    │ HighVolatility/Crash        │  │
│  └──────────┘    │ Bollinger  │    └─────────────────────────────┘  │
│                   └─────┬──────┘                │                    │
│                         │          ┌────────────▼────────────────┐  │
│                         ├─────────▶│ Anomaly Detection           │  │
│                         │          │ Spikes/Surges/FlashCrash    │  │
│  ┌──────────┐           │          └────────────────────────────┘  │
│  │ News CSV  │───▶ RAG Index ───▶ AI Q&A + Market Narrator          │
│  │ Watcher   │   (Vector + BM25)                                    │
│  └──────────┘                                                        │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │ Portfolio     │  │ Correlation  │  │ WebSocket Broadcast    │    │
│  │ Risk Engine   │  │ Engine       │  │ Manager                │    │
│  │ PnL/VaR/DD   │  │ BTC-ETH etc  │  │ Real-time → Browser    │    │
│  └──────────────┘  └──────────────┘  └────────────────────────┘    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                   ┌───────▼─────────┐
                   │  FastAPI + WS    │
                   │  REST + WebSocket│
                   │  :8000           │
                   └───────┬─────────┘
                           │
                   ┌───────▼─────────┐
                   │  Dark-Mode       │
                   │  Fintech         │
                   │  Dashboard       │
                   └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/market-intelligence.git
cd market-intelligence

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Set OpenAI API key for enhanced AI features
set OPENAI_API_KEY=your-key-here    # Windows
export OPENAI_API_KEY=your-key-here  # Linux/Mac

# 4. Run the system
python main.py
```

Open **http://localhost:8000** in your browser. The dashboard will connect via WebSocket and start streaming live data instantly.

### Docker

```bash
docker-compose up --build
```

---

## 📁 Project Structure

```
Microsoft-hack-bharat/
├── main.py                  # Orchestrator — wires all modules, REST + WebSocket server
├── config.py                # Centralized configuration
├── streaming_engine.py      # Custom cross-platform streaming engine
├── websocket_manager.py     # WebSocket connection & broadcast manager
├── ingestion.py             # Market data generator + news CSV watcher
├── indicators.py            # SMA, EMA, RSI, MACD, Bollinger Bands, volatility
├── regime_detection.py      # 5-state market regime classifier
├── anomaly_detection.py     # Price spike, volume surge, flash crash detector
├── portfolio_engine.py      # PnL, VaR, drawdown, risk scoring
├── correlation_engine.py    # Rolling Pearson correlation + break alerts
├── rag_module.py            # Document store (vector + BM25 hybrid search)
├── ai_explanations.py       # AI Q&A, anomaly explainer, market narrator
├── frontend/
│   ├── index.html           # Dashboard layout (7 panels)
│   ├── css/dashboard.css    # Dark fintech design system
│   └── js/app.js            # WebSocket client, sparklines, charts, chat
├── data/
│   ├── portfolio.csv        # Portfolio positions
│   └── news/seed_news.csv   # Seed news articles for RAG
├── Dockerfile               # Production Docker image
├── docker-compose.yml       # Multi-container deployment
└── requirements.txt         # Python dependencies
```

---

## 🔌 API Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard (serves the frontend) |
| `/api/status` | GET | System status, tick count, uptime, assets tracked |
| `/api/indicators?symbol=BTC` | GET | All technical indicators for a symbol (or all assets) |
| `/api/regimes?symbol=ETH` | GET | Market regime classification |
| `/api/anomalies?severity=HIGH` | GET | Anomaly alerts filtered by severity |
| `/api/portfolio` | GET | Portfolio summary + all positions |
| `/api/correlations` | GET | Cross-asset correlation pairs |
| `/api/narrator` | GET | Latest auto-generated market summary |
| `/api/ask` | POST | AI-powered market Q&A (RAG) |
| `/api/anomalies/explain?symbol=BTC` | GET | AI explanation for anomalies |
| `/health` | GET | Health check endpoint |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/market` | Real-time stream of ticks, indicators, alerts, regimes, portfolios, correlations |

### Example Requests

```bash
# Get BTC indicators
curl http://localhost:8000/api/indicators?symbol=BTC

# Ask a market question
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Why is BTC falling right now?"}'

# Get portfolio status
curl http://localhost:8000/api/portfolio

# Check system health
curl http://localhost:8000/health
```

---

## 📊 Features Deep Dive

### Technical Indicators (12 metrics)

| Indicator | Description |
|-----------|-------------|
| SMA-20, SMA-50 | Short/long-term Simple Moving Average |
| EMA-12, EMA-26 | Exponential Moving Average (MACD components) |
| RSI (14) | Relative Strength Index — overbought/oversold detection |
| MACD Line, Signal, Histogram | Moving Average Convergence Divergence |
| Bollinger Bands (Upper/Mid/Lower) | Volatility envelope (2σ) |
| Rolling Volatility | 20-period annualized price volatility |

### Market Regime Detection

The system classifies each asset into one of 5 states:

| Regime | Condition |
|--------|-----------|
| 🟢 **BULLISH** | Price above both SMAs, positive slope |
| 🔴 **BEARISH** | Price below both SMAs, negative slope |
| 🟡 **SIDEWAYS** | Low volatility, mixed signals |
| 🟠 **HIGH_VOLATILITY** | Elevated volatility with uncertain direction |
| ⛔ **CRASH** | Extreme drop with volume surge |

### Anomaly Detection

| Alert Type | Trigger |
|------------|---------|
| PRICE_SPIKE | Price move > 2.5σ from rolling mean |
| VOLUME_SURGE | Volume > 3× rolling average |
| VOLATILITY_BREAKOUT | Rolling vol > 2× baseline |
| FLASH_CRASH | > 5% drop within 60 seconds |

### AI Chat Assistant

The assistant understands different question categories:

| Question Type | Example | What You Get |
|--------------|---------|-------------|
| Greeting | "hi", "help" | Capabilities overview |
| Asset query | "How is BTC doing?" | Full technical analysis with price, RSI, trend, anomalies |
| Portfolio | "What's my portfolio risk?" | PnL, VaR, drawdown, risk score |
| Market overview | "Summarize the market" | All assets with regime + anomaly status |
| Why questions | "Why is SOL crashing?" | Regime + RSI context + related news |
| Features | "What can this system do?" | Complete feature list |

---

## ⚙️ Configuration

All settings are centralized in `config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TICK_INTERVAL_SECONDS` | 2 | Market data generation frequency |
| `NARRATOR_INTERVAL_SECONDS` | 300 | Market summary interval (5 min) |
| `PRICE_SPIKE_THRESHOLD` | 2.5 | Std devs for price spike alert |
| `VOLUME_SURGE_MULTIPLIER` | 3.0 | Volume multiplier for surge alert |
| `CORRELATION_BREAK_THRESHOLD` | 0.3 | Correlation change threshold |
| `RSI_PERIOD` | 14 | RSI lookback period |
| `SMA_SHORT_PERIOD` | 20 | Short SMA window |
| `SMA_LONG_PERIOD` | 50 | Long SMA window |

### Environment Variables

```bash
OPENAI_API_KEY=your-key-here     # For enhanced LLM features (optional)
OPENAI_MODEL=gpt-4o-mini         # LLM model to use
LOG_LEVEL=INFO                   # Logging level
```

> **Note:** The system works fully without an OpenAI API key — AI features fall back to intelligent template-based responses using live market data.

---

## 📈 Assets Tracked

| Type | Assets | Base Price |
|------|--------|------------|
| Crypto | BTC, ETH, SOL | $68K, $3.5K, $145 |
| Indian Markets | NIFTY, SENSEX | $21.5K, $71K |

---

## 📰 Adding Live News

Drop CSV files into `data/news/` with these columns:
```
title,body,source,published_at
"Breaking News Title","Full article body text","Reuters","2024-01-15"
```

The RAG index updates **automatically** — no restart needed. The CSV watcher continuously monitors the directory.

---

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The Docker setup includes health checks at `/health`.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **Streaming** | Custom cross-platform engine (Pathway-compatible design) |
| **Real-Time** | WebSocket (native browser API) |
| **Frontend** | HTML5, Vanilla CSS, Vanilla JavaScript |
| **AI / NLP** | OpenAI GPT (optional), SentenceTransformers (embeddings) |
| **Search** | Hybrid Vector + BM25 retrieval |
| **Data** | NumPy, Pandas |
| **Deployment** | Docker, Docker Compose |

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
