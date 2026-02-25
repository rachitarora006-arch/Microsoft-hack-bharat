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

    # ── Greeting / small talk ──
    if q_lower in ("hi", "hello", "hey", "help", "what can you do", "what can you do?"):
        answer_parts.append("👋 Hello! I'm your Market Intelligence AI Assistant. I can help with:")
        answer_parts.append("  • Real-time asset analysis — ask about BTC, ETH, SOL, NIFTY, SENSEX")
        answer_parts.append("  • Portfolio insights — PnL, risk, drawdown")
        answer_parts.append("  • Market regime analysis — bullish, bearish, sideways detection")
        answer_parts.append("  • Anomaly explanations — why a price spike or crash happened")
        answer_parts.append("  • News context — what's driving the markets")
        answer_parts.append("\nTry: \"How is BTC doing?\", \"What's my portfolio risk?\", \"Summarize the market\"")

    # ── System / feature questions ──
    elif any(w in q_lower for w in ["feature", "software", "system", "what is this", "about", "capabilities"]):
        answer_parts.append("📊 This is the Live Market Intelligence System. Key features:")
        answer_parts.append("  📈 Real-time streaming prices for BTC, ETH, SOL, NIFTY, SENSEX")
        answer_parts.append("  📉 Technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands")
        answer_parts.append("  🏛️  Market regime detection (Bullish / Bearish / Sideways / High Volatility)")
        answer_parts.append("  🚨 Anomaly detection: price spikes, volume surges, flash crashes")
        answer_parts.append("  💼 Portfolio risk management: PnL, VaR, drawdown, risk scoring")
        answer_parts.append("  🔗 Cross-asset correlation tracking")
        answer_parts.append("  📝 Automated market narration (5-min summaries)")
        answer_parts.append("  🤖 AI-powered Q&A with RAG-based news retrieval")
        if indicators:
            answer_parts.append(f"\n📡 Currently tracking {len(indicators)} assets in real-time.")

    # ── Portfolio questions ──
    elif any(w in q_lower for w in ["portfolio", "pnl", "risk", "drawdown", "var", "position", "holding"]):
        if portfolio:
            total_val = portfolio.get("total_value", 0)
            total_pnl = portfolio.get("total_pnl", 0)
            pnl_pct = portfolio.get("total_pnl_pct", 0)
            var_95 = portfolio.get("total_var_95", 0)
            avg_risk = portfolio.get("avg_risk_score", 0)
            max_dd = portfolio.get("max_drawdown_pct", 0)
            pnl_emoji = "📈" if total_pnl >= 0 else "📉"

            answer_parts.append(f"💼 Portfolio Summary:")
            answer_parts.append(f"  • Total Value: ${total_val:,.2f}")
            answer_parts.append(f"  {pnl_emoji} PnL: {'+'if total_pnl >= 0 else ''}${total_pnl:,.2f} ({pnl_pct:+.2f}%)")
            answer_parts.append(f"  • VaR (95%): ${var_95:,.2f}")
            answer_parts.append(f"  • Max Drawdown: {max_dd:.2f}%")
            answer_parts.append(f"  • Risk Score: {avg_risk:.1f}/100")

            if avg_risk > 7:
                answer_parts.append("\n⚠️ Risk is elevated. Consider reducing high-volatility positions.")
            elif avg_risk < 3:
                answer_parts.append("\n✅ Portfolio risk is within comfortable levels.")
        else:
            answer_parts.append("💼 Portfolio data is still loading. Please try again shortly.")

    # ── Specific asset questions ──
    elif any(sym.lower() in q_lower for sym in config.ASSETS):
        matched = [s for s in config.ASSETS if s.lower() in q_lower]
        for symbol in matched[:2]:
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
                answer_parts.append(f"  • Price: ${price:,.2f}")
                answer_parts.append(f"  • Regime: {regime}")
                answer_parts.append(f"  • RSI(14): {rsi:.1f} {'🔴 Overbought' if rsi > 70 else '🟢 Oversold' if rsi < 30 else '⚪ Neutral'}")
                answer_parts.append(f"  • SMA20: ${sma20:,.2f}  |  SMA50: ${sma50:,.2f}")
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

    # ── Market summary questions ──
    elif any(w in q_lower for w in ["market", "summar", "overview", "today", "how", "status", "what's happening"]):
        answer_parts.append("📊 Market Overview:")
        for symbol in config.ASSETS:
            data = indicators.get(symbol, {})
            regime = regimes.get(symbol, "—")
            price = data.get("price", 0)
            rsi = data.get("rsi", 0)
            if price > 0:
                answer_parts.append(f"  • {symbol}: ${price:,.2f} | Regime: {regime} | RSI: {rsi:.0f}")

        # Anomaly summary
        active_alerts = [s for s, a in anomalies.items() if isinstance(a, dict) and a.get("has_anomaly")]
        if active_alerts:
            answer_parts.append(f"\n🚨 Active anomalies: {', '.join(active_alerts)}")
        else:
            answer_parts.append("\n✅ No active anomalies")

        # Portfolio quick view
        if portfolio:
            pnl = portfolio.get("total_pnl", 0)
            answer_parts.append(f"💼 Portfolio PnL: {'+'if pnl >= 0 else ''}${pnl:,.2f}")

    # ── Why / cause questions ──
    elif any(w in q_lower for w in ["why", "cause", "reason", "explain"]):
        answer_parts.append("Based on current market data and news:")

        # Check if a specific asset is mentioned
        mentioned = [s for s in config.ASSETS if s.lower() in q_lower]
        for sym in mentioned:
            data = indicators.get(sym, {})
            regime = regimes.get(sym, "Unknown")
            rsi = data.get("rsi", 50)
            answer_parts.append(f"\n{sym} is currently in {regime} regime (RSI: {rsi:.0f})")

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
        for symbol in list(config.ASSETS)[:3]:
            data = indicators.get(symbol, {})
            regime = regimes.get(symbol, "—")
            price = data.get("price", 0)
            if price > 0:
                answer_parts.append(f"  • {symbol}: ${price:,.2f} ({regime})")

        answer_parts.append(f"\nYou can ask me specific questions like:")
        answer_parts.append(f"  • \"How is BTC doing?\"")
        answer_parts.append(f"  • \"What's my portfolio risk?\"")
        answer_parts.append(f"  • \"Summarize the market\"")
        answer_parts.append(f"  • \"Explain the SOL anomaly\"")

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
        ctx_parts.append(f"Portfolio PnL: ${total_pnl:,.2f}")
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
