/**
 * app.js — Market Intelligence Dashboard Application
 *
 * Handles:
 *  - WebSocket connection for real-time streaming updates
 *  - Price card updates with flash animations
 *  - Sparkline chart rendering (Canvas)
 *  - Technical indicator panel updates
 *  - Alerts feed with severity-coded entries
 *  - Portfolio metrics + SVG risk gauge
 *  - Correlation cards
 *  - AI Chat assistant (RAG-backed Q&A)
 *  - Market narrator
 *  - Toast notifications
 */

(function () {
    'use strict';

    // ═══════════════════════════════════════════════
    //  STATE
    // ═══════════════════════════════════════════════

    const API_BASE = '';
    const WS_URL = `ws://${location.host}/ws/market`;

    let ws = null;
    let selectedSymbol = 'BTC';
    let prevPrices = {};
    let sparkData = {};
    const MAX_SPARK_POINTS = 40;
    let alertItems = [];
    const MAX_ALERTS = 50;
    let reconnectAttempts = 0;
    let prevIndicators = {};

    // ═══════════════════════════════════════════════
    //  INIT
    // ═══════════════════════════════════════════════

    document.addEventListener('DOMContentLoaded', () => {
        initAssetSelector();
        initChat();
        connectWebSocket();
        fetchInitialData();
        setInterval(fetchNarrator, 60000);
        setInterval(fetchCorrelations, 15000);
        setInterval(fetchPortfolio, 10000);
    });

    // ═══════════════════════════════════════════════
    //  WEBSOCKET
    // ═══════════════════════════════════════════════

    function connectWebSocket() {
        updateConnectionStatus('connecting');

        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            reconnectAttempts = 0;
            updateConnectionStatus('connected');
            showToast('Connected to live stream', 'info');
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleWSMessage(msg);
            } catch (e) {
                console.error('WS parse error:', e);
            }
        };

        ws.onclose = () => {
            updateConnectionStatus('disconnected');
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            reconnectAttempts++;
            setTimeout(connectWebSocket, delay);
        };

        ws.onerror = () => {
            updateConnectionStatus('disconnected');
        };
    }

    function handleWSMessage(msg) {
        const { type, data } = msg;

        switch (type) {
            case 'tick':
                updatePriceCard(data);
                updateSparkline(data.symbol, data.price);
                if (data.symbol === selectedSymbol) {
                    updateIndicatorsPanel(data);
                }
                updateTickCount(data);
                break;
            case 'alert':
                addAlert(data);
                break;
            case 'regime':
                updateRegimeBadge(data.symbol, data.regime);
                break;
            case 'portfolio':
                updatePortfolio(data);
                break;
            case 'correlation':
                updateCorrelations(data);
                break;
            case 'narrator':
                updateNarrator(data);
                break;
        }
    }

    function updateConnectionStatus(status) {
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        dot.className = 'status-dot ' + (status === 'connected' ? 'connected' : 'disconnected');
        text.textContent = status === 'connected' ? 'Live' : status === 'connecting' ? 'Connecting...' : 'Offline';
    }

    // ═══════════════════════════════════════════════
    //  FETCH INITIAL DATA
    // ═══════════════════════════════════════════════

    async function fetchInitialData() {
        try {
            // Indicators
            const [indRes, regRes, portRes, corrRes, narrRes] = await Promise.all([
                fetch(`${API_BASE}/api/indicators`).then(r => r.json()),
                fetch(`${API_BASE}/api/regimes`).then(r => r.json()),
                fetch(`${API_BASE}/api/portfolio`).then(r => r.json()),
                fetch(`${API_BASE}/api/correlations`).then(r => r.json()),
                fetch(`${API_BASE}/api/narrator`).then(r => r.json()),
            ]);

            // Populate price cards from indicators
            if (indRes.assets) {
                for (const [sym, data] of Object.entries(indRes.assets)) {
                    updatePriceCard(data);
                    updateSparkline(sym, data.price);
                }
                if (indRes.assets[selectedSymbol]) {
                    updateIndicatorsPanel(indRes.assets[selectedSymbol]);
                }
            }

            // Regimes
            if (regRes.regimes) {
                for (const [sym, regime] of Object.entries(regRes.regimes)) {
                    updateRegimeBadge(sym, regime);
                }
            }

            // Portfolio
            if (portRes.summary) {
                updatePortfolio(portRes);
            }

            // Correlations
            if (corrRes.correlations) {
                corrRes.correlations.forEach(c => updateCorrelationCard(c));
            }

            // Narrator
            if (narrRes.summary) {
                updateNarrator(narrRes);
            }

            // Status
            const statusRes = await fetch(`${API_BASE}/api/status`).then(r => r.json());
            if (statusRes.tick_count) {
                document.getElementById('tickCount').textContent = `⚡ ${statusRes.tick_count}`;
            }
        } catch (e) {
            console.error('Failed to fetch initial data:', e);
        }
    }

    // ═══════════════════════════════════════════════
    //  PRICE CARDS
    // ═══════════════════════════════════════════════

    function updatePriceCard(data) {
        const sym = data.symbol;
        if (!sym) return;

        const priceEl = document.getElementById(`price-${sym}`);
        const changeEl = document.getElementById(`change-${sym}`);
        const volEl = document.getElementById(`vol-${sym}`);
        const rsiEl = document.getElementById(`rsi-${sym}`);
        const card = document.getElementById(`card-${sym}`);

        if (!priceEl) return;

        const price = parseFloat(data.price);
        const prevPrice = prevPrices[sym] || price;
        const changePct = prevPrice > 0 ? ((price - prevPrice) / prevPrice * 100) : 0;

        // Format price
        const formatted = price > 1000 ? price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
            : price.toFixed(4);
        priceEl.textContent = `$${formatted}`;

        // Flash animation
        if (card) {
            card.classList.remove('flash-up', 'flash-down');
            void card.offsetWidth; // trigger reflow
            if (price > prevPrice) card.classList.add('flash-up');
            else if (price < prevPrice) card.classList.add('flash-down');
        }

        // Change %
        if (changeEl) {
            const arrow = changePct >= 0 ? '▲' : '▼';
            changeEl.querySelector('.change-value').textContent = `${arrow} ${Math.abs(changePct).toFixed(3)}%`;
            changeEl.className = `card-change ${changePct >= 0 ? 'up' : 'down'}`;
        }

        // Volume
        if (volEl && data.volume !== undefined) {
            volEl.textContent = `Vol: ${formatNumber(data.volume)}`;
        }

        // RSI
        if (rsiEl && data.rsi !== undefined) {
            rsiEl.textContent = `RSI: ${parseFloat(data.rsi).toFixed(1)}`;
        }

        prevPrices[sym] = price;
    }

    // ═══════════════════════════════════════════════
    //  SPARKLINES
    // ═══════════════════════════════════════════════

    function updateSparkline(symbol, price) {
        if (!sparkData[symbol]) sparkData[symbol] = [];
        sparkData[symbol].push(parseFloat(price));
        if (sparkData[symbol].length > MAX_SPARK_POINTS) {
            sparkData[symbol].shift();
        }
        drawSparkline(symbol);
    }

    function drawSparkline(symbol) {
        const canvas = document.getElementById(`spark-${symbol}`);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const data = sparkData[symbol] || [];
        if (data.length < 2) return;

        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1;

        const isUp = data[data.length - 1] >= data[0];
        const color = isUp ? '#10b981' : '#ef4444';

        // Line
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.lineJoin = 'round';

        for (let i = 0; i < data.length; i++) {
            const x = (i / (data.length - 1)) * w;
            const y = h - ((data[i] - min) / range) * (h - 4) - 2;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Gradient fill
        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, isUp ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)');
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.fill();
    }

    // ═══════════════════════════════════════════════
    //  ASSET SELECTOR
    // ═══════════════════════════════════════════════

    function initAssetSelector() {
        document.querySelectorAll('.asset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.asset-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedSymbol = btn.dataset.symbol;

                // Update indicators panel
                document.getElementById('indAsset').textContent = selectedSymbol;
                fetchSymbolIndicators(selectedSymbol);

                // Highlight price card
                document.querySelectorAll('.price-card').forEach(c => c.classList.remove('active'));
                const card = document.getElementById(`card-${selectedSymbol}`);
                if (card) card.classList.add('active');
            });
        });

        // Also click on price cards
        document.querySelectorAll('.price-card').forEach(card => {
            card.addEventListener('click', () => {
                const sym = card.dataset.symbol;
                const btn = document.querySelector(`.asset-btn[data-symbol="${sym}"]`);
                if (btn) btn.click();
            });
        });

        // Set initial active
        const initCard = document.getElementById(`card-${selectedSymbol}`);
        if (initCard) initCard.classList.add('active');
    }

    async function fetchSymbolIndicators(symbol) {
        try {
            const res = await fetch(`${API_BASE}/api/indicators?symbol=${symbol}`);
            const data = await res.json();
            if (data.indicators) {
                updateIndicatorsPanel(data.indicators);
            }
        } catch (e) {
            console.error('Failed to fetch indicators:', e);
        }
    }

    // ═══════════════════════════════════════════════
    //  INDICATORS PANEL
    // ═══════════════════════════════════════════════

    function updateIndicatorsPanel(data) {
        const fields = ['sma_short', 'sma_long', 'ema12', 'ema26',
            'rsi', 'macd_line', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'rolling_vol'];

        fields.forEach(field => {
            const el = document.getElementById(`ind-${field}`);
            if (!el) return;

            const val = parseFloat(data[field]);
            if (isNaN(val)) return;

            // Format value
            if (field === 'rolling_vol') {
                el.textContent = (val * 100).toFixed(4) + '%';
            } else if (field === 'rsi') {
                el.textContent = val.toFixed(1);
            } else if (val > 1000) {
                el.textContent = val.toLocaleString('en-US', { maximumFractionDigits: 2 });
            } else {
                el.textContent = val.toFixed(4);
            }

            // Arrow indicators (compare with previous)
            const arrowEl = document.getElementById(`arrow-${field}`);
            if (arrowEl && prevIndicators[field] !== undefined) {
                const prev = prevIndicators[field];
                if (val > prev) {
                    arrowEl.textContent = '▲';
                    arrowEl.className = 'ind-arrow up';
                } else if (val < prev) {
                    arrowEl.textContent = '▼';
                    arrowEl.className = 'ind-arrow down';
                } else {
                    arrowEl.textContent = '—';
                    arrowEl.className = 'ind-arrow';
                }
            }
            prevIndicators[field] = val;
        });

        // RSI bar
        const rsiBar = document.getElementById('rsiBar');
        if (rsiBar && data.rsi !== undefined) {
            const rsi = parseFloat(data.rsi);
            rsiBar.style.width = rsi + '%';
            if (rsi > 70) rsiBar.style.background = '#ef4444';
            else if (rsi < 30) rsiBar.style.background = '#10b981';
            else rsiBar.style.background = '#6366f1';
        }
    }

    // ═══════════════════════════════════════════════
    //  REGIME BADGES
    // ═══════════════════════════════════════════════

    function updateRegimeBadge(symbol, regime) {
        const el = document.getElementById(`regime-${symbol}`);
        if (!el) return;
        el.textContent = regime;
        el.className = 'regime-badge ' + regime.toLowerCase().replace(' ', '_');
    }

    // ═══════════════════════════════════════════════
    //  ALERTS
    // ═══════════════════════════════════════════════

    function addAlert(data) {
        const alerts = data.alerts || [];
        const symbol = data.symbol;

        alerts.forEach(alert => {
            const item = {
                symbol,
                type: alert.type,
                severity: (alert.severity || 'LOW').toLowerCase(),
                details: alert.details,
                time: new Date().toLocaleTimeString(),
            };

            alertItems.unshift(item);
            if (alertItems.length > MAX_ALERTS) alertItems.pop();

            // Toast for high/extreme
            if (item.severity === 'high' || item.severity === 'extreme') {
                showToast(`🚨 ${symbol}: ${alert.type}`, `severity-${item.severity}`);
            }
        });

        renderAlerts();
    }

    function renderAlerts() {
        const feed = document.getElementById('alertsFeed');
        const badge = document.getElementById('alertCountBadge');

        if (alertItems.length === 0) {
            feed.innerHTML = '<div class="alert-empty">Monitoring for anomalies...</div>';
            badge.textContent = '0';
            return;
        }

        badge.textContent = alertItems.length;
        if (alertItems.length > 0) {
            badge.style.background = 'var(--red)';
            badge.style.color = '#fff';
        }

        feed.innerHTML = alertItems.slice(0, 20).map(a => `
            <div class="alert-item severity-${a.severity}">
                <div class="alert-severity">${a.severity.toUpperCase()}</div>
                <div class="alert-body">
                    <div class="alert-type">${a.symbol} — ${a.type}</div>
                    <div class="alert-detail">${a.details || ''}</div>
                </div>
                <div class="alert-time">${a.time}</div>
            </div>
        `).join('');
    }

    // ═══════════════════════════════════════════════
    //  PORTFOLIO
    // ═══════════════════════════════════════════════

    function updatePortfolio(data) {
        const s = data.summary || data;
        if (s.total_value !== undefined) {
            setText('portValue', `$${formatNumber(s.total_value)}`);

            const pnlEl = document.getElementById('portPnl');
            if (pnlEl) {
                pnlEl.textContent = `${s.total_pnl >= 0 ? '+' : ''}$${formatNumber(s.total_pnl)}`;
                pnlEl.className = `port-value ${s.total_pnl >= 0 ? 'positive' : 'negative'}`;
            }

            const pctEl = document.getElementById('portPnlPct');
            if (pctEl) {
                pctEl.textContent = `${s.total_pnl_pct >= 0 ? '+' : ''}${s.total_pnl_pct}%`;
                pctEl.className = `port-value ${s.total_pnl_pct >= 0 ? 'positive' : 'negative'}`;
            }

            setText('portVar', `$${formatNumber(s.total_var_95)}`);
            setText('portDrawdown', `${s.max_drawdown_pct}%`);

            // Risk gauge
            updateRiskGauge(s.avg_risk_score || 0);
        }

        // Positions table
        const positions = data.positions;
        if (positions) {
            const tbody = document.getElementById('positionsBody');
            if (tbody) {
                tbody.innerHTML = Object.values(positions).map(p => `
                    <tr>
                        <td style="font-weight:600">${p.symbol}</td>
                        <td>${p.quantity}</td>
                        <td>$${formatNumber(p.current_price)}</td>
                        <td class="${p.pnl >= 0 ? 'positive' : 'negative'}" style="color: ${p.pnl >= 0 ? 'var(--green)' : 'var(--red)'}">
                            ${p.pnl >= 0 ? '+' : ''}$${formatNumber(p.pnl)}
                        </td>
                        <td>${p.risk_score}</td>
                    </tr>
                `).join('');
            }
        }
    }

    function updateRiskGauge(score) {
        const arc = document.getElementById('gaugeArc');
        const text = document.getElementById('gaugeText');
        if (!arc || !text) return;

        const maxOffset = 251.2;
        const offset = maxOffset - (score / 100) * maxOffset;
        arc.style.strokeDashoffset = offset;
        text.textContent = Math.round(score);
    }

    async function fetchPortfolio() {
        try {
            const res = await fetch(`${API_BASE}/api/portfolio`);
            const data = await res.json();
            updatePortfolio(data);
        } catch (e) { }
    }

    // ═══════════════════════════════════════════════
    //  CORRELATIONS
    // ═══════════════════════════════════════════════

    function updateCorrelations(data) {
        if (Array.isArray(data)) {
            data.forEach(c => updateCorrelationCard(c));
        } else if (data.correlations) {
            data.correlations.forEach(c => updateCorrelationCard(c));
        }
    }

    function updateCorrelationCard(c) {
        const pair = c.pair;
        const valEl = document.getElementById(`corr-${pair}`);
        const barEl = document.getElementById(`corrBar-${pair}`);
        const changeEl = document.getElementById(`corrChange-${pair}`);

        if (valEl) {
            valEl.textContent = c.correlation.toFixed(4);
            valEl.style.color = c.correlation > 0 ? 'var(--green)' : c.correlation < 0 ? 'var(--red)' : 'var(--text-primary)';
        }
        if (barEl) {
            const pct = ((c.correlation + 1) / 2) * 100;
            barEl.style.width = pct + '%';
        }
        if (changeEl) {
            const change = c.change || 0;
            changeEl.textContent = `Δ ${change > 0 ? '+' : ''}${change.toFixed(4)}`;
        }
    }

    async function fetchCorrelations() {
        try {
            const res = await fetch(`${API_BASE}/api/correlations`);
            const data = await res.json();
            updateCorrelations(data);
        } catch (e) { }
    }

    // ═══════════════════════════════════════════════
    //  NARRATOR
    // ═══════════════════════════════════════════════

    function updateNarrator(data) {
        const el = document.getElementById('narratorContent');
        const timeEl = document.getElementById('narratorTime');

        if (data.summary) {
            el.innerHTML = `<div class="narrator-text">${escapeHtml(data.summary)}</div>`;
        }
        if (data.timestamp) {
            timeEl.textContent = new Date(data.timestamp).toLocaleTimeString();
        }
    }

    async function fetchNarrator() {
        try {
            const res = await fetch(`${API_BASE}/api/narrator`);
            const data = await res.json();
            if (data.summary) updateNarrator(data);
        } catch (e) { }
    }

    // ═══════════════════════════════════════════════
    //  AI CHAT
    // ═══════════════════════════════════════════════

    function initChat() {
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('chatSendBtn');

        sendBtn.addEventListener('click', sendChat);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendChat();
        });
    }

    async function sendChat() {
        const input = document.getElementById('chatInput');
        const question = input.value.trim();
        if (!question) return;

        input.value = '';
        addChatMessage('user', question);

        // Loading
        const loadingId = 'loading-' + Date.now();
        addChatMessage('bot', '<span class="shimmer" style="display:inline-block;width:120px;height:14px;border-radius:4px;"></span>', loadingId);

        try {
            const res = await fetch(`${API_BASE}/api/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question }),
            });
            const data = await res.json();

            // Remove loading
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();

            let answer = data.answer || 'Sorry, I could not generate an answer.';

            // Add sources
            let sourcesHtml = '';
            if (data.sources && data.sources.length > 0) {
                sourcesHtml = '<div class="sources">📰 Sources: ' +
                    data.sources.map(s => `<em>${s.title || s.source || 'News'}</em>`).join(', ') +
                    '</div>';
            }

            addChatMessage('bot', escapeHtml(answer).replace(/\n/g, '<br>') + sourcesHtml);
        } catch (e) {
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();
            addChatMessage('bot', 'Failed to connect to AI service.');
        }
    }

    function addChatMessage(role, content, id) {
        const container = document.getElementById('chatMessages');
        const msg = document.createElement('div');
        msg.className = `chat-msg ${role}`;
        if (id) msg.id = id;
        msg.innerHTML = `
            <div class="chat-avatar">${role === 'bot' ? 'AI' : 'You'}</div>
            <div class="chat-bubble">${content}</div>
        `;
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    // ═══════════════════════════════════════════════
    //  TOASTS
    // ═══════════════════════════════════════════════

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    // ═══════════════════════════════════════════════
    //  TICK COUNT
    // ═══════════════════════════════════════════════

    let tickCountLocal = 0;
    function updateTickCount() {
        tickCountLocal++;
        if (tickCountLocal % 5 === 0) {
            document.getElementById('tickCount').textContent = `⚡ ${tickCountLocal}`;
        }
    }

    // ═══════════════════════════════════════════════
    //  HELPERS
    // ═══════════════════════════════════════════════

    function setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    function formatNumber(n) {
        n = parseFloat(n);
        if (isNaN(n)) return '0';
        if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M';
        if (Math.abs(n) >= 1e3) return n.toLocaleString('en-US', { maximumFractionDigits: 2 });
        return n.toFixed(2);
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

})();
