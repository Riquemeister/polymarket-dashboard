#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║        POLYMARKET INTELLIGENCE DASHBOARD  v1.0              ║
║  Instalar dependências:                                      ║
║    pip install streamlit plotly requests pandas numpy        ║
║  Executar:                                                   ║
║    streamlit run polymarket_app.py                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import requests
import pandas as pd
import json
import numpy as np
from datetime import datetime, timezone
import plotly.graph_objects as go
import re, time

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Polymarket Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body, .stApp, .main { background-color: #0a1628 !important; color: #e0e6ef; }
.block-container { padding-top: 1.2rem; max-width: 1400px; }

.kpi-card {
    background: linear-gradient(135deg, #0d1b2a 0%, #132036 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
    margin-bottom: 0.5rem;
}
.kpi-label { font-size: 0.68rem; color: #667799; text-transform: uppercase; letter-spacing: 1.2px; }
.kpi-value { font-size: 1.9rem; font-weight: 800; color: #e0e6ef; line-height: 1.2; }
.kpi-sub   { font-size: 0.70rem; color: #445577; margin-top: 2px; }

.pill-green  { background:#06d6a020; border:1px solid #06d6a0; color:#06d6a0; border-radius:20px; padding:2px 10px; font-size:.78rem; font-weight:700; }
.pill-red    { background:#ef476f20; border:1px solid #ef476f; color:#ef476f; border-radius:20px; padding:2px 10px; font-size:.78rem; font-weight:700; }
.pill-yellow { background:#ffd16620; border:1px solid #ffd166; color:#ffd166; border-radius:20px; padding:2px 10px; font-size:.78rem; font-weight:700; }
.pill-grey   { background:#adb5bd20; border:1px solid #adb5bd; color:#adb5bd; border-radius:20px; padding:2px 10px; font-size:.78rem; font-weight:700; }

.rec-box-green  { background:#06d6a012; border-left:4px solid #06d6a0; padding:8px 12px; border-radius:0 8px 8px 0; color:#06d6a0; margin:8px 0; }
.rec-box-red    { background:#ef476f12; border-left:4px solid #ef476f; padding:8px 12px; border-radius:0 8px 8px 0; color:#ef476f; margin:8px 0; }
.rec-box-yellow { background:#ffd16612; border-left:4px solid #ffd166; padding:8px 12px; border-radius:0 8px 8px 0; color:#ffd166; margin:8px 0; }
.rec-box-grey   { background:#adb5bd12; border-left:4px solid #adb5bd; padding:8px 12px; border-radius:0 8px 8px 0; color:#adb5bd; margin:8px 0; }

.news-item { border-left:2px solid #1a4a7a; padding:5px 10px; margin:5px 0; font-size:.82rem; color:#99b0cc; }

.win-bar-wrap { background:#1a2a3a; border-radius:20px; height:10px; width:100%; margin:4px 0; }
.win-bar-fill { border-radius:20px; height:10px; }

[data-testid="stSidebar"] { background-color: #0d1b2a !important; border-right:1px solid #1a2a3a; }
h1,h2,h3,h4 { color:#e0e6ef; }
.stTabs [data-baseweb="tab"] { background-color:#0d1b2a; color:#667799; border-radius:8px 8px 0 0; }
.stTabs [aria-selected="true"] { background-color:#1a2a3a !important; color:#e0e6ef !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
GAMMA_API = "https://gamma-api.polymarket.com/markets"
GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
POLY_BASE = "https://polymarket.com/event/"

CAT_COLORS = {
    "Geopolitics":   "#ef476f",
    "Economics":     "#ffd166",
    "Politics":      "#06d6a0",
    "Sports/Esports":"#118ab2",
    "Crypto":        "#9b5de5",
    "Tech/AI":       "#f15bb5",
    "Other":         "#adb5bd",
}

REC_PILLS = {
    "BUY YES": ('<span class="pill-green">🟢 BUY YES</span>', "rec-box-green"),
    "BUY NO":  ('<span class="pill-red">🔴 BUY NO</span>',   "rec-box-red"),
    "WATCH":   ('<span class="pill-yellow">🟡 WATCH</span>',  "rec-box-yellow"),
    "AVOID":   ('<span class="pill-grey">⚫ AVOID</span>',    "rec-box-grey"),
}

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def categorize(q):
    ql = q.lower()
    if any(k in ql for k in ["fed","rate","bps","inflation","gdp","recession","tariff","trade","economy","interest"]):
        return "Economics"
    if any(k in ql for k in ["trump","biden","election","president","congress","senate","democrat","republican","prime minister","chancellor","parliament","vote","governor"]):
        return "Politics"
    if any(k in ql for k in ["ceasefire","war","ukraine","russia","iran","israel","conflict","military","nato","troops","nuclear","regime"]):
        return "Geopolitics"
    if any(k in ql for k in ["bitcoin","btc","crypto","eth","ethereum","bnb","sol","coin","token","defi"]):
        return "Crypto"
    if any(k in ql for k in ["tennis","football","soccer","nba","nfl","lol","esports","sport","league","match","cup","champion","ufc","mma","golf","f1","formula","rugby","cricket"]):
        return "Sports/Esports"
    if any(k in ql for k in ["ai","gpt","openai","tech","apple","google","microsoft","nvidia","amazon","meta","spacex","starship"]):
        return "Tech/AI"
    return "Other"

def extract_keywords(question, n=5):
    stopwords = {
        "will","the","a","an","by","of","in","to","for","is","are","be","have","has",
        "does","did","do","vs","and","or","at","on","from","with","after","before",
        "during","into","this","that","make","win","lose","next","last","year","month",
        "april","march","january","february","may","june","july","august","september",
        "october","november","december","2025","2026","2027","2028","2024"
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", question)
    filtered = [w for w in words if w.lower() not in stopwords]
    return " ".join(filtered[:n])

def win_rate_color(p):
    if p >= 65: return "#06d6a0"
    elif p >= 50: return "#ffd166"
    elif p >= 35: return "#ff9f43"
    return "#ef476f"

def quality_star(s):
    if s >= 80: return "⭐⭐⭐"
    elif s >= 50: return "⭐⭐"
    elif s >= 25: return "⭐"
    return "—"

# ─────────────────────────────────────────────────────────────────────────────
#  RECOMMENDATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def generate_recommendation(yes_p, spread, vol24, liq, p1d, p1w):
    if yes_p is None:
        return "AVOID", "Dados insuficientes para análise"
    p = yes_p * 100
    if spread > 0.08:
        return "AVOID", f"⚠️ Spread muito alto ({spread*100:.1f}%) — mercado ineficiente"
    if vol24 < 1000:
        return "AVOID", f"⚠️ Volume insuficiente (${vol24:.0f}) — risco de manipulação"
    if p > 97 or p < 3:
        return "AVOID", f"⚠️ Mercado praticamente resolvido ({p:.0f}% YES) — sem edge disponível"
    if p > 70 and p1d > 0.02 and vol24 > 50000:
        return "BUY YES", f"📈 Momentum forte (+{p1d*100:.1f}%/24h) a favor de YES com bom volume"
    if p < 30 and p1d < -0.02 and vol24 > 50000:
        return "BUY NO", f"📉 Momentum descendente ({p1d*100:.1f}%/24h) favorece NO com liquidez"
    if 35 <= p <= 65 and spread < 0.02 and vol24 > 100000:
        if p1d > 0.01:
            return "BUY YES", f"🎯 Mercado competitivo + momentum YES (+{p1d*100:.1f}%)"
        elif p1d < -0.01:
            return "BUY NO", f"🎯 Mercado competitivo + momentum NO ({p1d*100:.1f}%)"
        return "WATCH", "⚖️ Mercado equilibrado — aguardar catalisador externo"
    if 25 <= p <= 75 and vol24 > 10000:
        return "WATCH", f"👀 Mercado ativo ({p:.0f}% YES) — monitorizar evolução"
    if p > 70 and vol24 > 5000:
        return "BUY YES", f"✅ Probabilidade alta ({p:.0f}% YES) com liquidez adequada"
    if p < 30 and vol24 > 5000:
        return "BUY NO", f"✅ Probabilidade baixa ({p:.0f}% YES) — NO favorito"
    return "WATCH", "Mercado a monitorizar — sem sinal claro"

# ─────────────────────────────────────────────────────────────────────────────
#  DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_markets_raw(limit=100):
    try:
        r = requests.get(GAMMA_API, params={
            "active":"true","closed":"false",
            "limit":limit,"offset":0,
            "order":"volume24hr","ascending":"false"
        }, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erro API Polymarket: {e}")
        return []

@st.cache_data(ttl=900, show_spinner=False)
def fetch_news(keywords, timespan="3d", n=6):
    if not keywords.strip():
        return []
    try:
        r = requests.get(GDELT_API, params={
            "query": keywords,
            "mode": "artlist",
            "maxrecords": n,
            "format": "json",
            "sourcelang": "english",
            "timespan": timespan,
            "sort": "DateDesc"
        }, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        return [
            {"title": a.get("title",""), "url": a.get("url",""),
             "source": a.get("domain",""), "date": a.get("seendate","")}
            for a in data.get("articles", [])
        ]
    except:
        return []

def process_market(m):
    try:
        prices = json.loads(m.get("outcomePrices","[]")) if isinstance(m.get("outcomePrices"), str) else m.get("outcomePrices",[])
        yes_p  = float(prices[0]) if prices and len(prices) > 0 else None
        no_p   = float(prices[1]) if prices and len(prices) > 1 else None

        vol24  = float(m.get("volume24hr",  0) or 0)
        vol1w  = float(m.get("volume1wk",   0) or 0)
        liq    = float(m.get("liquidityNum",0) or 0)
        spread = float(m.get("spread",      0) or 0)
        p1d    = float(m.get("oneDayPriceChange",  0) or 0)
        p1w    = float(m.get("oneWeekPriceChange", 0) or 0)
        question = m.get("question","")
        cat = categorize(question)

        # Quality score
        qs = 0
        if liq    > 200000: qs += 25
        elif liq  >  20000: qs += 15
        elif liq  >   2000: qs += 8
        if vol24  > 500000: qs += 25
        elif vol24>  50000: qs += 18
        elif vol24>   5000: qs += 10
        elif vol24>    500: qs += 4
        if spread  < 0.005: qs += 25
        elif spread < 0.015: qs += 18
        elif spread < 0.03:  qs += 12
        elif spread < 0.06:  qs += 6
        if m.get("competitive", False): qs += 15
        if m.get("featured",    False): qs += 10

        # Win rate (adjusted probability)
        win_rate = None
        if yes_p is not None:
            eff = max(0.5, 1 - spread * 8)
            momentum_adj = p1d * 100 * 0.25 * eff
            win_rate = round(min(99, max(1, yes_p * 100 + momentum_adj)), 1)

        # Expected Value
        ev_yes = ev_no = None
        if yes_p and 0 < yes_p < 1:
            ev_yes = round((yes_p * (1-yes_p) - (1-yes_p) * yes_p) * 100, 2)
            if no_p:
                ev_no = round(((1-yes_p) * (1-no_p) - yes_p * no_p) * 100, 2)

        rec, rec_reason = generate_recommendation(yes_p, spread, vol24, liq, p1d, p1w)

        # Days to resolution
        days_left = None
        try:
            end_iso = m.get("endDateIso","")
            if end_iso:
                end_dt = datetime.fromisoformat(end_iso.replace("Z","+00:00"))
                days_left = (end_dt - datetime.now(timezone.utc)).days
        except: pass

        return {
            "id":              m.get("id",""),
            "slug":            m.get("slug",""),
            "question":        question,
            "category":        cat,
            "yes_prob":        round(yes_p*100,1) if yes_p is not None else None,
            "no_prob":         round(no_p*100, 1) if no_p  is not None else None,
            "win_rate":        win_rate,
            "ev_yes":          ev_yes,
            "ev_no":           ev_no,
            "volume24h":       vol24,
            "volume1w":        vol1w,
            "liquidity":       liq,
            "spread":          spread,
            "change_1d_pct":   round(p1d*100, 2),
            "change_1w_pct":   round(p1w*100, 2),
            "quality_score":   qs,
            "recommendation":  rec,
            "rec_reason":      rec_reason,
            "days_left":       days_left,
            "featured":        bool(m.get("featured",  False)),
            "competitive":     bool(m.get("competitive",False)),
            "keywords":        extract_keywords(question),
            "url":             POLY_BASE + m.get("slug",""),
        }
    except:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def load_all_markets():
    raw = fetch_markets_raw(100)
    rows = [process_market(m) for m in raw]
    return pd.DataFrame([r for r in rows if r is not None])

# ─────────────────────────────────────────────────────────────────────────────
#  CHARTS
# ─────────────────────────────────────────────────────────────────────────────
BG, PLOT_BG, GRID = "#0d1b2a", "#111c2e", "#1a2a3a"

def base_layout(title, h=300):
    return dict(
        title=title, title_font=dict(color="#ccd8ee", size=14),
        paper_bgcolor=BG, plot_bgcolor=PLOT_BG,
        font=dict(color="#99b0cc", size=11),
        margin=dict(l=8,r=8,t=48,b=8), height=h,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    )

def chart_top_volume(df, n=10):
    t = df.nlargest(n,"volume24h")
    fig = go.Figure(go.Bar(
        x=t["volume24h"],
        y=[q[:34]+"…" if len(q)>34 else q for q in t["question"]],
        orientation="h",
        marker_color=[CAT_COLORS.get(c,"#adb5bd") for c in t["category"]],
        text=[f"${v/1e6:.1f}m" if v>=1e6 else f"${v/1e3:.0f}k" for v in t["volume24h"]],
        textposition="inside", insidetextanchor="end",
        hovertemplate="%{y}<br>Vol: $%{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(**base_layout(f"🔥 Top {n} Volume 24h", 380))
    fig.update_xaxes(title_text="USDC", tickformat=".1s")
    return fig

def chart_category_volume(df):
    cv = df.groupby("category")["volume24h"].sum().sort_values(ascending=False)
    fig = go.Figure(go.Bar(
        x=list(cv.index), y=list(cv.values),
        marker_color=[CAT_COLORS.get(c,"#adb5bd") for c in cv.index],
        text=[f"${v/1e6:.1f}m" if v>=1e6 else f"${v/1e3:.0f}k" for v in cv.values],
        textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(**base_layout("📊 Volume por Categoria 24h", 300))
    fig.update_xaxes(title_text="Categoria", tickfont=dict(size=10))
    fig.update_yaxes(title_text="USDC", tickformat=".1s")
    return fig

def chart_scatter(df):
    sd = df[df["spread"]<0.12].copy()
    wr_colors = [win_rate_color(w) for w in sd["win_rate"].fillna(50)]
    fig = go.Figure(go.Scatter(
        x=sd["yes_prob"], y=sd["spread"]*100, mode="markers",
        marker=dict(
            size=np.clip(sd["volume24h"]/100000, 6, 26),
            color=wr_colors, opacity=0.82,
            line=dict(width=0.5, color="#0a1628")
        ),
        text=[q[:50] for q in sd["question"]],
        customdata=sd["win_rate"].fillna(0),
        hovertemplate="<b>%{text}</b><br>YES: %{x:.0f}%  Spread: %{y:.2f}%  Win Rate: %{customdata:.0f}%<extra></extra>",
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="#334466", line_width=1)
    fig.update_layout(**base_layout("🎯 YES% vs Spread  (cor = win rate)", 300))
    fig.update_xaxes(title_text="Prob YES (%)")
    fig.update_yaxes(title_text="Spread (%)")
    return fig

def chart_rec_distribution(df):
    rc = df["recommendation"].value_counts()
    colors_map = {"BUY YES":"#06d6a0","BUY NO":"#ef476f","WATCH":"#ffd166","AVOID":"#adb5bd"}
    fig = go.Figure(go.Bar(
        x=list(rc.index), y=list(rc.values),
        marker_color=[colors_map.get(r,"#adb5bd") for r in rc.index],
        text=list(rc.values), textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(**base_layout("🤖 Distribuição de Recomendações IA", 280))
    fig.update_yaxes(title_text="Nº Mercados")
    return fig

def chart_winrate_distribution(df):
    wr = df["win_rate"].dropna()
    fig = go.Figure(go.Histogram(
        x=wr, nbinsx=20,
        marker_color="#118ab2",
        opacity=0.85,
    ))
    fig.update_layout(**base_layout("📐 Distribuição Win Rate", 260))
    fig.update_xaxes(title_text="Win Rate (%)")
    fig.update_yaxes(title_text="Nº Mercados")
    return fig

# ─────────────────────────────────────────────────────────────────────────────
#  MARKET CARD
# ─────────────────────────────────────────────────────────────────────────────
def render_market(row):
    pill_html, box_cls = REC_PILLS.get(row["recommendation"], REC_PILLS["AVOID"])
    wr = row["win_rate"] or 50
    wr_bar_color = win_rate_color(wr)
    wr_pct = min(100, max(0, wr))

    label = (
        f"{pill_html}  **{row['question'][:80]}{'…' if len(row['question'])>80 else ''}**  "
        f"— YES {row['yes_prob']:.0f}%  ·  Vol ${row['volume24h']:,.0f}  ·  {row['category']}"
    )
    with st.expander(label, expanded=False):

        # ── Métricas ────────────────────────────────────────────────────────
        cols = st.columns(8)
        cols[0].metric("YES Prob",     f"{row['yes_prob']:.1f}%", f"{row['change_1d_pct']:+.1f}% hoje")
        cols[1].metric("NO Prob",      f"{row['no_prob']:.1f}%"  if row["no_prob"] else "—")
        cols[2].metric("Win Rate",     f"{wr:.1f}%")
        cols[3].metric("Qualidade",    f"{row['quality_score']}/100")
        cols[4].metric("Spread",       f"{row['spread']*100:.2f}%")
        cols[5].metric("Volume 24h",   f"${row['volume24h']:,.0f}")
        cols[6].metric("Liquidez",     f"${row['liquidity']:,.0f}")
        cols[7].metric("Dias p/ fim",  str(row["days_left"]) if row["days_left"] is not None else "?")

        # ── Win rate bar ────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="margin:6px 0 2px;font-size:.75rem;color:#667799">
            Win Rate Estimado: <b style="color:{wr_bar_color}">{wr:.1f}%</b>
            &nbsp;·&nbsp; Variação 1 semana: <b>{row["change_1w_pct"]:+.1f}%</b>
        </div>
        <div class="win-bar-wrap">
            <div class="win-bar-fill" style="width:{wr_pct}%;background:{wr_bar_color}"></div>
        </div>
        """, unsafe_allow_html=True)

        # ── Recomendação IA ─────────────────────────────────────────────────
        st.markdown(f"""
        <div class="{box_cls}">
            🤖 <b>Recomendação IA: {row["recommendation"]}</b><br>
            {row["rec_reason"]}
        </div>
        """, unsafe_allow_html=True)

        # ── Notas rápidas ───────────────────────────────────────────────────
        notes = []
        if row["days_left"] is not None and row["days_left"] <= 3:
            notes.append("⚡ Resolução iminente — movimento de preço esperado")
        if abs(row["change_1d_pct"]) > 5:
            notes.append(f"🔔 Movimento forte hoje: {row['change_1d_pct']:+.1f}%")
        if row["spread"] < 0.003:
            notes.append("✅ Mercado muito eficiente (spread < 0.3%)")
        if row["liquidity"] > 500000:
            notes.append("💧 Elevada liquidez — entrada/saída sem slippage")
        if row["competitive"]:
            notes.append("🏆 Marcado como mercado competitivo pela Polymarket")
        if notes:
            st.markdown("**📌 Alertas:**")
            for n in notes:
                st.markdown(f"- {n}")

        # ── Notícias em tempo real ──────────────────────────────────────────
        st.markdown("**📰 Notícias Recentes (GDELT):**")
        with st.spinner("A carregar notícias..."):
            news = fetch_news(row["keywords"], timespan="3d", n=6)

        if news:
            for art in news[:5]:
                d = art["date"][:8] if art["date"] else ""
                try:    d_fmt = datetime.strptime(d, "%Y%m%d").strftime("%d/%m")
                except: d_fmt = d
                st.markdown(f"""
                <div class="news-item">
                    📌 <a href="{art["url"]}" target="_blank"
                       style="color:#7eb3d8;text-decoration:none">{art["title"]}</a>
                    <span style="color:#334455"> · {art["source"]} · {d_fmt}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Sem notícias recentes encontradas para este mercado.")

        # ── Link Polymarket ─────────────────────────────────────────────────
        st.markdown(
            f"🔗 **[Abrir no Polymarket]({row['url']})** &nbsp;·&nbsp; "
            f"Qualidade: {quality_star(row['quality_score'])} ({row['quality_score']}/100)",
            unsafe_allow_html=False
        )

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
def main():

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown("""
    <h1 style="margin-bottom:0;font-size:2rem">
        📈 Polymarket Intelligence Dashboard
    </h1>
    <p style="color:#556688;margin-top:2px;font-size:.9rem">
        Dados em tempo real · Análise IA · Notícias GDELT · Win Rate estimado
    </p>
    """, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Controlo")
        if st.button("🔄 Atualizar Agora", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Cache: 5 min · Notícias: 15 min")
        st.divider()

        cats = ["Todas"] + sorted(CAT_COLORS.keys())
        sel_cat = st.selectbox("📂 Categoria", cats)

        recs_all = ["Todas", "BUY YES", "BUY NO", "WATCH", "AVOID"]
        sel_rec = st.selectbox("🤖 Recomendação", recs_all)

        min_vol = st.slider("💰 Volume Mínimo 24h ($)", 0, 500_000, 0, step=5_000, format="$%d")
        max_spr = st.slider("📉 Spread Máximo (%)", 0.0, 15.0, 10.0, step=0.5)
        min_qs  = st.slider("⭐ Qualidade Mínima", 0, 100, 0)
        min_wr  = st.slider("🎯 Win Rate Mín. (%)", 0, 100, 0)
        only_ft = st.checkbox("⭐ Só Featured")
        sort_by = st.selectbox("📊 Ordenar por", ["Volume 24h","Win Rate","Qualidade","Spread","Dias p/ Fim"])

        st.divider()
        st.markdown("""
**🟢 BUY YES** — momentum + prob alta  
**🔴 BUY NO** — momentum descendente  
**🟡 WATCH** — incerto, monitorizar  
**⚫ AVOID** — spread alto / sem edge  

**Win Rate** = probabilidade implícita  
ajustada para momentum e eficiência  
        """)

    # ── Load ─────────────────────────────────────────────────────────────────
    with st.spinner("⏳ A carregar mercados Polymarket..."):
        df = load_all_markets()

    if df.empty:
        st.error("Não foi possível carregar dados. Verifica a ligação à internet.")
        return

    # ── Apply filters ─────────────────────────────────────────────────────────
    flt = df.copy()
    if sel_cat != "Todas":
        flt = flt[flt["category"] == sel_cat]
    if sel_rec != "Todas":
        flt = flt[flt["recommendation"] == sel_rec]
    flt = flt[flt["volume24h"] >= min_vol]
    flt = flt[flt["spread"]    <= max_spr / 100]
    flt = flt[flt["quality_score"] >= min_qs]
    if "win_rate" in flt.columns:
        flt = flt[flt["win_rate"].fillna(0) >= min_wr]
    if only_ft:
        flt = flt[flt["featured"] == True]

    sort_map = {
        "Volume 24h": "volume24h", "Win Rate": "win_rate",
        "Qualidade": "quality_score", "Spread": "spread", "Dias p/ Fim": "days_left"
    }
    asc = sort_by == "Spread"
    flt = flt.sort_values(sort_map[sort_by], ascending=asc, na_position="last").reset_index(drop=True)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    n_by = flt["recommendation"].value_counts().to_dict()
    total_vol = flt["volume24h"].sum()
    avg_wr    = flt["win_rate"].mean()
    avg_spr   = flt["spread"].mean() * 100

    k = st.columns(6)
    def kpi(col, label, val, sub=""):
        col.markdown(f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
                     f'<div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>',
                     unsafe_allow_html=True)

    kpi(k[0], "Mercados",      len(flt),               f"de {len(df)} total")
    kpi(k[1], "Volume 24h",    f"${total_vol/1e6:.1f}m","USDC")
    kpi(k[2], "🟢 BUY YES",    n_by.get("BUY YES",0),  "recomendações")
    kpi(k[3], "🔴 BUY NO",     n_by.get("BUY NO",0),   "recomendações")
    kpi(k[4], "Win Rate Médio",f"{avg_wr:.1f}%"        if not np.isnan(avg_wr) else "—","estimado")
    kpi(k[5], "Spread Médio",  f"{avg_spr:.2f}%",       "eficiência")

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Visão Geral")

    c1, c2 = st.columns([1.3, 1])
    with c1: st.plotly_chart(chart_top_volume(flt, 10), use_container_width=True)
    with c2: st.plotly_chart(chart_category_volume(flt), use_container_width=True)

    c3, c4, c5 = st.columns(3)
    with c3: st.plotly_chart(chart_scatter(flt), use_container_width=True)
    with c4: st.plotly_chart(chart_rec_distribution(flt), use_container_width=True)
    with c5: st.plotly_chart(chart_winrate_distribution(flt), use_container_width=True)

    # ── Markets tabs ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 🗂️ Mercados — {len(flt)} resultados")

    tab_yes, tab_no, tab_watch, tab_avoid, tab_all = st.tabs([
        f"🟢 BUY YES ({n_by.get('BUY YES',0)})",
        f"🔴 BUY NO ({n_by.get('BUY NO',0)})",
        f"🟡 WATCH ({n_by.get('WATCH',0)})",
        f"⚫ AVOID ({n_by.get('AVOID',0)})",
        f"📋 Todos ({len(flt)})",
    ])

    for tab, rec in zip([tab_yes, tab_no, tab_watch, tab_avoid], ["BUY YES","BUY NO","WATCH","AVOID"]):
        with tab:
            sub = flt[flt["recommendation"] == rec]
            if sub.empty:
                st.info("Nenhum mercado com estes filtros.")
            else:
                for _, row in sub.head(25).iterrows():
                    render_market(row)

    with tab_all:
        for _, row in flt.head(50).iterrows():
            render_market(row)

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("---")
    export_cols = ["question","category","yes_prob","win_rate","recommendation",
                   "rec_reason","volume24h","liquidity","spread","quality_score",
                   "change_1d_pct","change_1w_pct","days_left","url"]
    csv = flt[export_cols].to_csv(index=False)
    st.download_button(
        "📥 Exportar CSV completo",
        data=csv,
        file_name=f"polymarket_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown(
        f"<p style='color:#334455;font-size:.72rem;text-align:center'>"
        f"Fonte: Polymarket Gamma API · Notícias: GDELT Project · "
        f"Gerado: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</p>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
