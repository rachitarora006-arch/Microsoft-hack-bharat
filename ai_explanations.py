"""
ai_explanations.py — LLM-powered market intelligence via RAG.

Provides:
  - Anomaly explanations (why did this event happen?)
  - Natural-language market Q&A (RAG-augmented)
  - Automated market narrator (periodic summary every 5 min)
  - Template-based fallback when no LLM API key is available
"""

import logging
import json
import time
import threading
from datetime import datetime, timezone

import config
from rag_module import retrieve, doc_store
from knowledge_base import get_knowledge_answer

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
#  LLM CLIENT
# ═══════════════════════════════════════════════════════════

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("✅ OpenAI client initialized")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI client failed: {e}. Using template fallback.")
            _openai_client = "unavailable"
    return _openai_client


def _llm_generate(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Generate text via OpenAI API with fallback."""
    client = _get_openai_client()
    if client == "unavailable" or not config.OPENAI_API_KEY:
        return None  # Signal to use template fallback

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM generation error: {e}")
        return None


# ═══════════════════════════════════════════════════════════
#  RAG Q&A
# ═══════════════════════════════════════════════════════════

def ask_market_question(question: str, market_context: dict = None) -> dict:
    """
    Answer a market question using RAG (retrieve relevant news + LLM).
    Falls back to template-based answer if LLM unavailable.
    """
    # Retrieve relevant documents
    docs = retrieve(question)
    context_chunks = [d.get("chunk", "") for d in docs[:config.RAG_TOP_K]]
    context_text = "\n---\n".join(context_chunks) if context_chunks else "No relevant news found."

    # Build market context string
    market_ctx = ""
    if market_context:
        market_ctx = f"\n\nCurrent Market Data:\n{json.dumps(market_context, indent=2)}"

    system_prompt = """You are a senior financial analyst AI assistant. You provide accurate, 
insightful market analysis based on the provided context and market data.
Be concise but thorough. Cite specific data points when available.
Always mention if the information might be delayed or limited."""

    user_prompt = f"""Question: {question}

Relevant News & Context:
{context_text}
{market_ctx}

Provide a clear, actionable analysis."""

    # Try LLM
    llm_response = _llm_generate(system_prompt, user_prompt)

    if llm_response:
        return {
            "question": question,
            "answer": llm_response,
            "sources": [{"title": d.get("title", ""), "source": d.get("source", "")} for d in docs[:3]],
            "method": "rag_llm",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Template fallback
    return _template_answer(question, docs, market_context)


def _template_answer(question: str, docs: list, market_context: dict = None) -> dict:
    """Generate a contextual answer without LLM by analyzing question intent and market data."""
    q_lower = question.lower().strip()
    C = config.CURRENCY_SYMBOL  # ₹

    # ── Knowledge Base Check (educational / project questions) ──
    kb_answer = get_knowledge_answer(q_lower)
    if kb_answer:
        return {
            "question": question,
            "answer": kb_answer,
            "sources": [{"title": d.get("title", ""), "source": d.get("source", "")} for d in docs[:3]] if docs else [],
            "method": "knowledge_base",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    answer_parts = []
    indicators = {}
    regimes = {}
    anomalies = {}
    portfolio = {}

    if market_context:
        indicators = market_context.get("indicators", {})
        regimes = market_context.get("regimes", {})
        anomalies = market_context.get("anomalies", {})
        portfolio = market_context.get("portfolio", {})

    # Alias map for natural-language asset names
    ASSET_ALIASES = {
        "bitcoin": "BTC", "btc": "BTC",
        "ethereum": "ETH", "eth": "ETH", "ether": "ETH",
        "solana": "SOL", "sol": "SOL",
        "nifty": "NIFTY", "nifty50": "NIFTY", "nifty 50": "NIFTY",
        "sensex": "SENSEX", "bse": "SENSEX",
    }

    def _match_assets(text: str) -> list:
        """Match asset symbols from natural language."""
        matched = set()
        for alias, sym in ASSET_ALIASES.items():
            if alias in text:
                matched.add(sym)
        for sym in config.ASSETS:
            if sym.lower() in text:
                matched.add(sym)
        return list(matched)

    matched_assets = _match_assets(q_lower)

    # ── Greeting / small talk ──
    if q_lower in ("hi", "hello", "hey", "help", "what can you do", "what can you do?", "yo", "sup", "namaste"):
        answer_parts.append("👋 Hello! I'm your Market Intelligence AI Assistant. I can help with:")
        answer_parts.append("  • Real-time asset analysis — ask about BTC, ETH, SOL, NIFTY, SENSEX")
        answer_parts.append("  • Portfolio insights — PnL, risk, drawdown")
        answer_parts.append("  • Market regime analysis — bullish, bearish, sideways detection")
        answer_parts.append("  • Anomaly explanations — why a price spike or crash happened")
        answer_parts.append("  • News context — what's driving the markets")
        answer_parts.append("  • Correlation data — how assets move together")
        answer_parts.append("  • Technical indicators — SMA, RSI, MACD, Bollinger Bands")
        answer_parts.append(f"\nAll prices are displayed in Indian Rupees ({C}).")
        answer_parts.append("\nTry: \"How is BTC doing?\", \"What's my portfolio risk?\", \"Summarize the market\"")
        answer_parts.append("\n⚡ Running in fast template mode (no LLM API key configured).")

    # ── System / feature questions ──
    elif any(w in q_lower for w in ["feature", "software", "system", "what is this", "about", "capabilities", "what do you do", "who are you", "are you ai", "are you real", "marketintel", "what is market"]):
        answer_parts.append("📊 This is the Live Market Intelligence System. Key features:")
        answer_parts.append("  📈 Real-time streaming prices for BTC, ETH, SOL, NIFTY, SENSEX")
        answer_parts.append("  📉 Technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands")
        answer_parts.append("  🏛️  Market regime detection (Bullish / Bearish / Sideways / High Volatility)")
        answer_parts.append("  🚨 Anomaly detection: price spikes, volume surges, flash crashes")
        answer_parts.append(f"  💼 Portfolio risk management: PnL, VaR, drawdown, risk scoring")
        answer_parts.append("  🔗 Cross-asset correlation tracking")
        answer_parts.append("  📝 Automated market narration (5-min summaries)")
        answer_parts.append("  🤖 AI-powered Q&A with RAG-based news retrieval")
        if indicators:
            answer_parts.append(f"\n📡 Currently tracking {len(indicators)} assets in real-time.")
        answer_parts.append("\n⚡ Currently running in template mode (no OpenAI API key). Add a key to unlock full AI answers.")

    # ── Portfolio questions ──
    elif any(w in q_lower for w in ["portfolio", "pnl", "p&l", "profit", "loss", "risk", "drawdown", "var", "position", "holding", "investment", "my money", "balance", "net worth"]):
        if portfolio:
            total_val = portfolio.get("total_value", 0)
            total_pnl = portfolio.get("total_pnl", 0)
            pnl_pct = portfolio.get("total_pnl_pct", 0)
            var_95 = portfolio.get("total_var_95", 0)
            avg_risk = portfolio.get("avg_risk_score", 0)
            max_dd = portfolio.get("max_drawdown_pct", 0)
            pnl_emoji = "📈" if total_pnl >= 0 else "📉"

            answer_parts.append(f"💼 Portfolio Summary:")
            answer_parts.append(f"  • Total Value: {C}{total_val:,.2f}")
            answer_parts.append(f"  {pnl_emoji} PnL: {'+'if total_pnl >= 0 else ''}{C}{total_pnl:,.2f} ({pnl_pct:+.2f}%)")
            answer_parts.append(f"  • VaR (95%): {C}{var_95:,.2f}")
            answer_parts.append(f"  • Max Drawdown: {max_dd:.2f}%")
            answer_parts.append(f"  • Risk Score: {avg_risk:.1f}/100")

            if avg_risk > 7:
                answer_parts.append("\n⚠️ Risk is elevated. Consider reducing high-volatility positions.")
            elif avg_risk < 3:
                answer_parts.append("\n✅ Portfolio risk is within comfortable levels.")
        else:
            answer_parts.append("💼 Portfolio data is still loading. Please try again shortly.")

    # ── Specific asset questions (including natural aliases like 'bitcoin') ──
    elif matched_assets:
        for symbol in matched_assets[:2]:
            data = indicators.get(symbol, {})
            regime = regimes.get(symbol, "Unknown")
            anom = anomalies.get(symbol, {})

            if data:
                price = data.get("price", 0)
                rsi = data.get("rsi", 0)
                sma20 = data.get("sma_short", 0)
                sma50 = data.get("sma_long", 0)
                vol = data.get("rolling_vol", 0)
                macd = data.get("macd_histogram", 0)

                answer_parts.append(f"📊 {symbol} Analysis:")
                answer_parts.append(f"  • Price: {C}{price:,.2f}")
                answer_parts.append(f"  • Regime: {regime}")
                answer_parts.append(f"  • RSI(14): {rsi:.1f} {'🔴 Overbought' if rsi > 70 else '🟢 Oversold' if rsi < 30 else '⚪ Neutral'}")
                answer_parts.append(f"  • SMA20: {C}{sma20:,.2f}  |  SMA50: {C}{sma50:,.2f}")
                answer_parts.append(f"  • MACD Histogram: {macd:.4f} {'📈' if macd > 0 else '📉'}")
                answer_parts.append(f"  • Volatility: {vol*100:.4f}%")

                # Trend analysis
                if price > sma20 > sma50:
                    answer_parts.append("  📈 Trend: Bullish — price above both moving averages")
                elif price < sma20 < sma50:
                    answer_parts.append("  📉 Trend: Bearish — price below both moving averages")
                else:
                    answer_parts.append("  ↔️ Trend: Mixed — watch for directional breakout")

                # Anomalies
                if isinstance(anom, dict) and anom.get("has_anomaly"):
                    alerts = anom.get("alerts", [])
                    for a in alerts[:2]:
                        answer_parts.append(f"  🚨 Alert: {a.get('type', '')} [{a.get('severity', '')}] — {a.get('details', '')}")
            else:
                answer_parts.append(f"📊 {symbol}: Data is loading, please try again shortly.")

    # ── Correlation questions ──
    elif any(w in q_lower for w in ["correlat", "relation", "linked", "connected", "together", "pair"]):
        correlations = market_context.get("correlations", {}) if market_context else {}
        if correlations:
            answer_parts.append("🔗 Asset Correlations:")
            for pair_key, corr_data in correlations.items():
                if isinstance(corr_data, dict):
                    val = corr_data.get("correlation", 0)
                    strength = "Strong" if abs(val) > 0.7 else "Moderate" if abs(val) > 0.4 else "Weak"
                    direction = "positive" if val > 0 else "negative"
                    answer_parts.append(f"  • {pair_key}: {val:.4f} ({strength} {direction} correlation)")
            answer_parts.append("\nCorrelation > 0.7 means assets tend to move together.")
            answer_parts.append("Correlation < -0.7 means they tend to move in opposite directions.")
        else:
            answer_parts.append("🔗 Correlation data is still being computed. Please try again shortly.")

    # ── Technical indicator questions ──
    elif any(w in q_lower for w in ["indicator", "technical", "sma", "rsi", "macd", "bollinger", "ema", "moving average"]):
        answer_parts.append("📉 Technical Indicators Explained:")
        answer_parts.append("  • SMA (Simple Moving Average): Smooths price over a window. SMA20 vs SMA50 crossover signals trends.")
        answer_parts.append("  • RSI (Relative Strength Index): 0-100 scale. >70 = overbought, <30 = oversold.")
        answer_parts.append("  • MACD: Momentum indicator. Positive histogram = bullish momentum, negative = bearish.")
        answer_parts.append("  • Bollinger Bands: Price volatility envelope. Touching upper band = potentially overbought.")
        answer_parts.append("")
        if indicators:
            answer_parts.append("Current readings:")
            for symbol in config.ASSETS:
                data = indicators.get(symbol, {})
                if data:
                    rsi = data.get("rsi", 0)
                    macd = data.get("macd_histogram", 0)
                    answer_parts.append(f"  • {symbol}: RSI={rsi:.1f}, MACD={macd:.4f}")

    # ── News questions ──
    elif any(w in q_lower for w in ["news", "article", "headline", "latest", "update", "what happened"]):
        if docs:
            answer_parts.append("📰 Latest News in Index:")
            for doc in docs[:5]:
                title = doc.get("title", "Unknown")
                source = doc.get("source", "")
                answer_parts.append(f"  • {title} ({source})")
        else:
            answer_parts.append("📰 No news articles have been indexed yet.")

    # ── Anomaly / alert questions ──
    elif any(w in q_lower for w in ["anomal", "alert", "spike", "crash", "surge", "unusual", "warning"]):
        active = {s: a for s, a in anomalies.items() if isinstance(a, dict) and a.get("has_anomaly")}
        if active:
            answer_parts.append("🚨 Active Anomalies:")
            for sym, anom_data in active.items():
                for alert in anom_data.get("alerts", [])[:3]:
                    answer_parts.append(f"  • {sym}: [{alert.get('severity', '')}] {alert.get('type', '')} — {alert.get('details', '')}")
        else:
            answer_parts.append("✅ No active anomalies detected across any tracked assets.")

    # ── Regime questions ──
    elif any(w in q_lower for w in ["regime", "bullish", "bearish", "sideways", "trend", "direction", "momentum"]):
        if regimes:
            answer_parts.append("🏛️ Market Regimes:")
            for sym, regime in regimes.items():
                emoji = "📈" if "BULL" in regime.upper() else "📉" if "BEAR" in regime.upper() else "↔️"
                answer_parts.append(f"  {emoji} {sym}: {regime}")
            answer_parts.append("\nRegimes are detected using SMA crossovers, volatility, and price momentum.")
        else:
            answer_parts.append("🏛️ Regime data is still being computed. Please try again shortly.")

    # ── Market summary questions ──
    elif any(w in q_lower for w in ["market", "summar", "overview", "today", "how", "status", "what's happening", "kya ho raha", "price", "all"]):
        answer_parts.append("📊 Market Overview:")
        for symbol in config.ASSETS:
            data = indicators.get(symbol, {})
            regime = regimes.get(symbol, "—")
            price = data.get("price", 0)
            rsi = data.get("rsi", 0)
            if price > 0:
                answer_parts.append(f"  • {symbol}: {C}{price:,.2f} | Regime: {regime} | RSI: {rsi:.0f}")

        # Anomaly summary
        active_alerts = [s for s, a in anomalies.items() if isinstance(a, dict) and a.get("has_anomaly")]
        if active_alerts:
            answer_parts.append(f"\n🚨 Active anomalies: {', '.join(active_alerts)}")
        else:
            answer_parts.append("\n✅ No active anomalies")

        # Portfolio quick view
        if portfolio:
            pnl = portfolio.get("total_pnl", 0)
            answer_parts.append(f"💼 Portfolio PnL: {'+'if pnl >= 0 else ''}{C}{pnl:,.2f}")

    # ── Why / cause questions ──
    elif any(w in q_lower for w in ["why", "cause", "reason", "explain", "what caused", "how come"]):
        answer_parts.append("Based on current market data and news:")

        # Check if a specific asset is mentioned
        mentioned = _match_assets(q_lower)
        for sym in mentioned:
            data = indicators.get(sym, {})
            regime = regimes.get(sym, "Unknown")
            rsi = data.get("rsi", 50)
            price = data.get("price", 0)
            answer_parts.append(f"\n{sym} is currently at {C}{price:,.2f} in {regime} regime (RSI: {rsi:.0f})")

        # Add news context
        if docs:
            answer_parts.append("\nRelated news that may be relevant:")
            for doc in docs[:3]:
                title = doc.get("title", "Unknown")
                source = doc.get("source", "")
                answer_parts.append(f"  • {title} ({source})")
        else:
            answer_parts.append("\nNo directly relevant news found in the current index.")

    # ── Generic fallback with actual market data ──
    else:
        answer_parts.append(f"Here's what I can tell you about the current market:")
        for symbol in config.ASSETS:
            data = indicators.get(symbol, {})
            regime = regimes.get(symbol, "—")
            price = data.get("price", 0)
            if price > 0:
                answer_parts.append(f"  • {symbol}: {C}{price:,.2f} ({regime})")

        answer_parts.append(f"\nYou can ask me questions like:")
        answer_parts.append(f"  • \"How is Bitcoin doing?\"")
        answer_parts.append(f"  • \"What's my portfolio risk?\"")
        answer_parts.append(f"  • \"Show me all anomalies\"")
        answer_parts.append(f"  • \"What are the correlations?\"")
        answer_parts.append(f"  • \"Explain the technical indicators\"")
        answer_parts.append(f"  • \"Summarize the market\"")

    return {
        "question": question,
        "answer": "\n".join(answer_parts),
        "sources": [{"title": d.get("title", ""), "source": d.get("source", "")} for d in docs[:3]] if docs else [],
        "method": "template_fallback",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════
#  ANOMALY EXPLAINER
# ═══════════════════════════════════════════════════════════

def explain_anomaly(anomaly: dict, market_context: dict = None) -> str:
    """Generate a human-readable explanation for a detected anomaly."""
    symbol = anomaly.get("symbol", "Unknown")
    alerts = anomaly.get("alerts", [])

    if not alerts:
        return f"No anomalies detected for {symbol}."

    # Retrieve related news
    query = f"{symbol} price movement volatility"
    docs = retrieve(query)
    context = "\n".join([d.get("chunk", "") for d in docs[:3]])

    alert_desc = "\n".join([f"- {a['type']}: {a['details']}" for a in alerts])

    system_prompt = """You are a financial analyst explaining market anomalies to traders.
Be specific about what happened and potential causes. Keep it under 150 words."""

    user_prompt = f"""Anomaly Alert for {symbol}:
{alert_desc}

Related News:
{context}

Explain what happened and potential implications."""

    explanation = _llm_generate(system_prompt, user_prompt, max_tokens=200)

    if explanation:
        return explanation

    # Template fallback
    lines = [f"⚠️ Anomaly Alert for {symbol}:"]
    for alert in alerts:
        lines.append(f"  [{alert['severity']}] {alert['type']}: {alert['details']}")
    if docs:
        lines.append("\nPossibly related news:")
        for d in docs[:2]:
            lines.append(f"  • {d.get('title', 'N/A')}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
#  MARKET NARRATOR
# ═══════════════════════════════════════════════════════════

_latest_narrative = {
    "summary": "Waiting for sufficient data to generate market narrative...",
    "generated_at": datetime.now(timezone.utc).isoformat(),
}
_narrator_lock = threading.Lock()


def generate_market_narrative(market_state: dict) -> str:
    """
    Generate an automated market summary covering:
    - Top gainers / losers
    - Most volatile asset
    - Regime changes
    - Risk overview
    """
    global _latest_narrative

    if not market_state or not market_state.get("indicators"):
        return _latest_narrative["summary"]

    indicators = market_state.get("indicators", {})
    regimes = market_state.get("regimes", {})
    anomalies = market_state.get("anomalies", {})
    portfolio = market_state.get("portfolio", {})

    # Compute stats
    gainers = []
    losers = []
    most_volatile = {"symbol": "N/A", "vol": 0}

    for symbol, data in indicators.items():
        if isinstance(data, dict):
            pnl_pct = data.get("pnl_pct", 0)
            vol = data.get("rolling_vol", 0)
            price = data.get("price", 0)

            if pnl_pct > 0:
                gainers.append((symbol, pnl_pct, price))
            else:
                losers.append((symbol, pnl_pct, price))

            if vol > most_volatile["vol"]:
                most_volatile = {"symbol": symbol, "vol": vol}

    gainers.sort(key=lambda x: -x[1])
    losers.sort(key=lambda x: x[1])

    # Build narrative context
    ctx_parts = [
        f"Top Gainers: {', '.join(f'{s} (+{p:.1f}%)' for s, p, _ in gainers[:3]) or 'None'}",
        f"Top Losers: {', '.join(f'{s} ({p:.1f}%)' for s, p, _ in losers[:3]) or 'None'}",
        f"Most Volatile: {most_volatile['symbol']} (vol={most_volatile['vol']:.4f})",
    ]

    # Regimes
    if regimes:
        regime_str = ", ".join(f"{s}: {r}" for s, r in regimes.items())
        ctx_parts.append(f"Market Regimes: {regime_str}")

    # Anomaly count
    total_anomalies = sum(1 for a in anomalies.values() if isinstance(a, dict) and a.get("has_anomaly"))
    ctx_parts.append(f"Active Anomalies: {total_anomalies}")

    # Portfolio
    if portfolio:
        total_pnl = portfolio.get("total_pnl", 0)
        risk = portfolio.get("avg_risk_score", 0)
        ctx_parts.append(f"Portfolio PnL: {config.CURRENCY_SYMBOL}{total_pnl:,.2f}")
        ctx_parts.append(f"Average Risk Score: {risk:.0f}/100")

    context = "\n".join(ctx_parts)

    system_prompt = """You are a professional market narrator providing a 5-minute market update.
Be concise, professional, and highlight actionable insights.
Format: brief overview → key movers → regime status → risk assessment.
Keep it under 200 words."""

    user_prompt = f"""Generate a market update summary based on this data:

{context}

Current time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"""

    narrative = _llm_generate(system_prompt, user_prompt, max_tokens=300)

    if not narrative:
        # Template narrative
        narrative = _template_narrative(context, gainers, losers, most_volatile, regimes, total_anomalies)

    with _narrator_lock:
        _latest_narrative = {
            "summary": narrative,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_snapshot": {
                "gainers": [(s, p) for s, p, _ in gainers[:3]],
                "losers": [(s, p) for s, p, _ in losers[:3]],
                "most_volatile": most_volatile["symbol"],
                "anomaly_count": total_anomalies,
            },
        }

    logger.info("📝 Market narrative generated")
    return narrative


def _template_narrative(context, gainers, losers, most_volatile, regimes, anomaly_count):
    """Template-based market narrative (no LLM required)."""
    now = datetime.now(timezone.utc).strftime('%H:%M UTC')
    lines = [
        f"═══ MARKET UPDATE ({now}) ═══",
        "",
    ]

    if gainers:
        lines.append(f"📈 TOP GAINERS: {', '.join(f'{s} (+{p:.1f}%)' for s, p, _ in gainers[:3])}")
    if losers:
        lines.append(f"📉 TOP LOSERS: {', '.join(f'{s} ({p:.1f}%)' for s, p, _ in losers[:3])}")

    lines.append(f"🌊 MOST VOLATILE: {most_volatile['symbol']} (volatility={most_volatile['vol']:.4f})")

    if regimes:
        lines.append(f"🏛️  REGIMES: {', '.join(f'{s}={r}' for s, r in regimes.items())}")

    if anomaly_count > 0:
        lines.append(f"🚨 ACTIVE ALERTS: {anomaly_count} anomalies detected")
    else:
        lines.append("✅ No anomalies detected")

    lines.append("")
    lines.append("═══════════════════════════════")
    return "\n".join(lines)


def get_latest_narrative() -> dict:
    """Return the most recent market narrative."""
    with _narrator_lock:
        return dict(_latest_narrative)
