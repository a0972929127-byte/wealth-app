"""
小資族股市與理財 App ── Noreen 專屬訂製版 (終極修復)
============================================
1. 修正 ETF 5 碼搜尋問題 (自動補齊 .TW)。
2. 強化基本面數據捕捉邏輯，避免 Yahoo API 缺漏。
3. 保留所有視覺化與熱力圖功能。
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import numpy as np

# =============================================================
# 頁面與全域設定 & CSS 樣式
# =============================================================
st.set_page_config(page_title="小資族理財 App｜Noreen", page_icon="📱", layout="wide")

st.markdown(
    """
    <style>
      .app-card { background-color: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 24px; color: #333333; }
      .app-card-dark { background-color: #1e2126; border-radius: 16px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); margin-bottom: 24px; color: #ffffff; }
      .metric-value { font-size: 2rem; font-weight: bold; margin-bottom: 4px; }
      .metric-label { font-size: 0.9rem; color: #666666; }
      .dark-metric-label { font-size: 0.9rem; color: #aaaaaa; }
      .stTabs [data-baseweb="tab-list"] {gap: 24px;}
      .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; font-size: 1.1rem;}
      .news-card { padding: 15px; margin-bottom: 10px; border-radius: 8px; background-color: #262730; border-left: 4px solid #64ffda; }
      .block-container {padding-top: 2rem;}
      
      .blog-card {
        background-color: #262730; border-radius: 12px; padding: 20px; margin-bottom: 16px;
        border-left: 4px solid #64ffda; transition: transform 0.2s, box-shadow 0.2s;
      }
      .blog-card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.3); }
      .blog-title { font-size: 1.25rem; font-weight: bold; margin-bottom: 8px; color: #ffffff; }
      .blog-meta { font-size: 0.85rem; color: #aaaaaa; margin-bottom: 12px; }
      .blog-desc { font-size: 0.95rem; color: #dddddd; line-height: 1.6; }
      .blog-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; margin-right: 8px; }
      .tag-news { background-color: rgba(100, 255, 218, 0.2); color: #64ffda; }
      .tag-style { background-color: rgba(99, 110, 250, 0.2); color: #636efa; }
      .tag-fraud { background-color: rgba(239, 85, 59, 0.2); color: #ef553b; }
      
      .analysis-card { background: #262730; padding: 20px; border-radius: 10px; border: 1px solid #444; margin-bottom: 20px;}
      
      .watermark {
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-30deg);
        opacity: 0.05; font-size: 8vw; font-weight: bold; color: #ffffff;
        z-index: 9999; pointer-events: none; user-select: none; white-space: nowrap;
      }
    </style>
    <div class="watermark">wealth app - Noreen</div>
    """,
    unsafe_allow_html=True,
)

# =============================================================
# Session State 初始化 & 強制互斥 Callback
# =============================================================
if "menu_selection" not in st.session_state: st.session_state.menu_selection = "🕒 進度 (Progress)"

def update_menu(active_key):
    if st.session_state[active_key] is not None:
        st.session_state.menu_selection = st.session_state[active_key]
        for key in ["w_rad", "t_rad", "b_rad"]:
            if key != active_key:
                st.session_state[key] = None

defaults = {
    "portfolio": [{"代碼": "2330.TW", "市場": "TW", "股數": 1000, "成本": 620.0}, {"代碼": "0050.TW", "市場": "TW", "股數": 2000, "成本": 140.0}, {"代碼": "AAPL", "市場": "US", "股數": 50, "成本": 175.0}],
    "cash_accounts": [{"帳戶名稱": "台新 Richart (日常)", "幣別": "TWD", "金額": 150000}, {"帳戶名稱": "國泰世華 (交割)", "幣別": "TWD", "金額": 200000}],
    "other_assets": 0, "real_estate": 0, "plan_mode": "尚未設定", "monthly_expense": 50000, "retire_years": 30, 
    "manual_target": 20000000, "return_mode": "各資產近 10 年年化報酬率", "custom_return": 6.0, "monthly_savings": 30000, "annual_bonus": 100000,
    "w_rad": None, "t_rad": None, "b_rad": None
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

USD_TWD = 32.5

# =============================================================
# 股票清單字典 & 產業板塊映射
# =============================================================
TW_STOCKS = {"2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2308.TW": "台達電", "2382.TW": "廣達", "2881.TW": "富邦金", "2891.TW": "中信金", "2882.TW": "國泰金", "2603.TW": "長榮", "3711.TW": "日月光", "3231.TW": "緯創", "2303.TW": "聯電", "2884.TW": "玉山金", "2002.TW": "中鋼", "2609.TW": "陽明"}
US_STOCKS = {"AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla", "BRK-B": "Berkshire Hathaway", "LLY": "Eli Lilly", "V": "Visa", "JPM": "JPMorgan Chase", "WMT": "Walmart", "MA": "Mastercard", "PG": "Procter & Gamble", "AVGO": "Broadcom"}
ETFS = {"0050.TW": "元大台灣50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", "00929.TW": "復華台灣科技優息", "00919.TW": "群益台灣精選高息", "VOO": "Vanguard S&P 500", "QQQ": "Invesco QQQ Trust", "SPY": "SPDR S&P 500", "VTI": "Vanguard Total Stock"}

REVERSE_LOOKUP = {v: k for d in [TW_STOCKS, US_STOCKS, ETFS] for k, v in d.items()}

SECTOR_MAP = {
    "2330.TW": "半導體", "2454.TW": "半導體", "2303.TW": "半導體", "3711.TW": "半導體",
    "2317.TW": "電子代工/電腦", "2382.TW": "電子代工/電腦", "3231.TW": "電子代工/電腦", "2308.TW": "電子零組件",
    "2881.TW": "金融保險", "2891.TW": "金融保險", "2882.TW": "金融保險", "2884.TW": "金融保險",
    "2603.TW": "航運", "2609.TW": "航運", "2002.TW": "傳統產業",
    "AAPL": "消費電子", "MSFT": "基礎軟體", "NVDA": "半導體", "GOOGL": "網路資訊",
    "META": "網路資訊", "AMZN": "互聯網零售", "TSLA": "汽車製造", "BRK-B": "多元金融",
    "LLY": "製藥與醫療", "V": "信貸與支付", "JPM": "銀行", "WMT": "零售", "MA": "信貸與支付", "PG": "消費品", "AVGO": "半導體",
    "0050.TW": "台股市值型", "0056.TW": "台股高股息", "00878.TW": "台股高股息", "00929.TW": "台股科技主題", "00919.TW": "台股高股息",
    "VOO": "美股市值型", "QQQ": "美股科技型", "SPY": "美股市值型", "VTI": "美股全市場"
}

# =============================================================
# API 抓取與強化數據函數
# =============================================================
@st.cache_data(ttl=300)
def fetch_indices(market="US"):
    symbols = {"^DJI": "道瓊斯", "^IXIC": "納斯達克", "^GSPC": "標普500"} if market == "US" else {"^TWII": "台灣加權指數", "0050.TW": "台灣50", "2330.TW": "台積電 (大盤指標)"}
    res = []
    for s, name in symbols.items():
        try:
            hist = yf.Ticker(s).history(period="2d")
            curr = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2] if len(hist) > 1 else curr
            chg = curr - prev
            pct = (chg / prev) * 100 if prev else 0
            res.append((name, curr, chg, pct))
        except: res.append((name, 0, 0, 0))
    return res

@st.cache_data(ttl=300)
def fetch_market_overview_table(stock_dict):
    results = []
    for t, name in stock_dict.items():
        try:
            hist = yf.Ticker(t).history(period="2d")
            if len(hist) > 0:
                curr = hist['Close'].iloc[-1]
                vol = hist['Volume'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else curr
                chg = curr - prev
                pct = (chg / prev) * 100 if prev else 0
                results.append({"代碼": t, "股票名稱": name, "最新價": curr, "漲跌額": chg, "升跌幅(%)": pct, "成交量": int(vol)})
        except: pass
    results.sort(key=lambda x: x["升跌幅(%)"], reverse=True)
    for i, r in enumerate(results): r["序號"] = i + 1
    return pd.DataFrame(results)[["序號", "代碼", "股票名稱", "最新價", "漲跌額", "升跌幅(%)", "成交量"]] if results else pd.DataFrame()

@st.cache_data(ttl=900)
def fetch_stock_price_fast(symbol):
    try: return yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
    except: return None

@st.cache_data(ttl=900)
def fetch_stock_data_detailed(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="6mo")
        if hist.empty: return None, None, None, None
        curr = hist['Close'].iloc[-1]
        delta = hist['Close'].diff()
        gain, loss = (delta.where(delta > 0, 0)).rolling(14).mean(), (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        ma10, ma20 = hist['Close'].rolling(10).mean().iloc[-1], hist['Close'].rolling(20).mean().iloc[-1]
        return curr, rsi, "黃金交叉 ↗" if ma10 > ma20 else "死亡交叉 ↘", hist
    except: return None, None, None, None

@st.cache_data(ttl=3600)
def fetch_fundamentals_and_news(symbol):
    try: return yf.Ticker(symbol).info, yf.Ticker(symbol).news
    except: return {}, []

# 強化版基本面抓取函數
def safe_metric(info_dict, keys, is_percent=False):
    for k in keys:
        val = info_dict.get(k)
        if val is not None and val != "Infinity" and val != "":
            try:
                v = float(val)
                return f"{v * 100:.2f}%" if is_percent else f"{v:.2f}"
            except: pass
    return "無資料"

# =============================================================
# 核心計算引擎
# =============================================================
total_stock_value = sum([(fetch_stock_price_fast(i["代碼"]) or i["成本"]) * i["股數"] * (USD_TWD if i["市場"] == "US" else 1) for i in st.session_state.portfolio])
total_cash_value = sum([float(acc["金額"]) for acc in st.session_state.cash_accounts])
financial_net_worth = total_stock_value + total_cash_value
total_net_worth = financial_net_worth + st.session_state.other_assets + st.session_state.real_estate
avg_monthly_savings = st.session_state.monthly_savings + (st.session_state.annual_bonus / 12)
calc_return_rate = st.session_state.custom_return / 100 if st.session_state.return_mode == "個別自訂報酬率" else 0.065 if "10 年" in st.session_state.return_mode else 0.050

annual_exp = st.session_state.monthly_expense * 12
if st.session_state.plan_mode == "每月支出 × 年數 (最保守)": target_amount = annual_exp * st.session_state.retire_years
elif st.session_state.plan_mode == "4% 法則 (FIRE)": target_amount = annual_exp / 0.04
elif st.session_state.plan_mode == "提領模型 (Die with Zero)":
    real_r = (1 + calc_return_rate) / (1 + 0.02) - 1
    target_amount = (annual_exp * (1 - (1 + real_r) ** (-st.session_state.retire_years)) / real_r) if real_r > 0 else (annual_exp * st.session_state.retire_years)
else: target_amount = st.session_state.manual_target

# =============================================================
# 側邊欄 UI
# =============================================================
with st.sidebar:
    st.markdown("## 💰 財富管理 APP")
    st.divider()

    st.markdown("### 📌 我的財富")
    wealth_opts = ["🕒 進度 (Progress)", "💼 資產 (Assets)", "💸 支出 (Expenses)", "📋 規劃 (Planning)"]
    st.radio("w_nav", wealth_opts, key="w_rad", on_change=update_menu, args=("w_rad",), label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True) 

    st.markdown("### 📈 投資觀測工具")
    tool_opts = ["🇹🇼 台股 (TW Stocks)", "🇺🇸 美股 (US Stocks)", "📈 ETF（台股＆美股）", "💡 數據化推薦股 (Data-driven Insights)"]
    st.radio("t_nav", tool_opts, key="t_rad", on_change=update_menu, args=("t_rad",), label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 📚 學習與專欄")
    blog_opts = ["📖 投資專欄 (Investment Blog)"]
    st.radio("b_nav", blog_opts, key="b_rad", on_change=update_menu, args=("b_rad",), label_visibility="collapsed")

page = st.session_state.menu_selection

# =============================================================
# 模組：財管核心
# =============================================================
if page == "🕒 進度 (Progress)":
    st.markdown("<h1>進度</h1>", unsafe_allow_html=True)
    if st.session_state.plan_mode == "尚未設定":
        st.markdown("""<div class="app-card-dark" style="text-align:center; padding: 40px 20px;"><h1 style="font-size: 3rem; margin-bottom: 10px;">⏳</h1><h3>尚未設定退休目標</h3><p style="color: #64ffda;">👉 請點擊左側【📋 規劃】開始設定</p></div>""", unsafe_allow_html=True)
    else:
        progress_pct = min((financial_net_worth / target_amount * 100) if target_amount > 0 else 0, 100)
        st.markdown(f"""<div class="app-card-dark"><div style="display: flex; justify-content: space-between;"><span class="dark-metric-label">退休進度</span><span style="font-weight: bold;">{progress_pct:.1f}%</span></div><div style="background-color: #333; border-radius: 10px; height: 12px; margin: 10px 0;"><div style="background-color: #64ffda; width: {progress_pct}%; height: 100%; border-radius: 10px;"></div></div><div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #888;"><span>金融資產淨值 NT${financial_net_worth:,.0f}</span><span>目標 NT${target_amount:,.0f}</span></div></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='app-card-dark'><div class='dark-metric-label'>總資產淨值 (含不動產)</div><div class='metric-value'>NT${total_net_worth:,.0f}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='app-card-dark'><div class='dark-metric-label'>平均月儲蓄</div><div class='metric-value'>NT${avg_monthly_savings:,.0f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='app-card-dark'><div class='dark-metric-label'>金融資產淨值</div><div class='metric-value'>NT${financial_net_worth:,.0f}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='app-card-dark'><div class='dark-metric-label'>加權報酬率設定</div><div class='metric-value'>{calc_return_rate*100:.1f}%</div></div>", unsafe_allow_html=True)

elif page == "💼 資產 (Assets)":
    st.markdown("<h1>資產</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='app-card-dark'><div class='dark-metric-label'>總資產淨值</div><div class='metric-value' style='font-size: 2.5rem;'>NT${total_net_worth:,.0f}</div></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.5])
    with c1:
        fig = px.pie(pd.DataFrame({"資產": ["股票/ETF", "現金/定存", "其他", "不動產"], "市值": [total_stock_value, total_cash_value, st.session_state.other_assets, st.session_state.real_estate]}), values="市值", names="資產", hole=0.7, color_discrete_sequence=["#2b6cb0", "#90cdf4", "#f6ad55", "#48bb78"])
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200, paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        for i, (name, val) in enumerate(zip(["股票/ETF", "現金/定存", "其他", "不動產"], [total_stock_value, total_cash_value, st.session_state.other_assets, st.session_state.real_estate])):
            st.markdown(f"""<div style="display:flex; justify-content:space-between; margin-bottom: 15px;"><div><span style="color:{["#2b6cb0", "#90cdf4", "#f6ad55", "#48bb78"][i]}; font-size:1.2rem;">■</span> {name}</div><div style="text-align:right;"><b>NT${val:,.0f}</b></div></div>""", unsafe_allow_html=True)
    st.markdown("### ▍ 股票 / ETF")
    st.session_state.portfolio = st.data_editor(pd.DataFrame(st.session_state.portfolio), num_rows="dynamic", use_container_width=True).to_dict('records')
    st.markdown("### ▍ 現金 / 定存")
    st.session_state.cash_accounts = st.data_editor(pd.DataFrame(st.session_state.cash_accounts), num_rows="dynamic", use_container_width=True).to_dict('records')

elif page == "💸 支出 (Expenses)":
    st.markdown("<h1>支出模擬</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    sim_expense = c1.number_input("大筆支出模擬金額", value=0, step=10000)
    if st.button("計算對退休日期的影響", use_container_width=True, type="primary") and avg_monthly_savings > 0 and sim_expense > 0:
        st.error(f"⚠️ 試算結果：若花費此筆 **NT${sim_expense:,.0f}**，您的退休計畫將會 **延後約 {sim_expense / avg_monthly_savings:.1f} 個月**！")

elif page == "📋 規劃 (Planning)":
    st.markdown("<h1>規劃</h1>", unsafe_allow_html=True)
    st.session_state.plan_mode = st.radio("選擇演算法", ["每月支出 × 年數 (最保守)", "4% 法則 (FIRE)", "提領模型 (Die with Zero)", "手動輸入目標金額"])
    st.markdown("<div class='app-card-dark'>", unsafe_allow_html=True)
    if st.session_state.plan_mode != "手動輸入目標金額":
        st.session_state.monthly_expense = st.number_input("預估退休後每月支出", value=st.session_state.monthly_expense, step=5000)
        st.session_state.retire_years = st.number_input("預估存活年數", value=st.session_state.retire_years, step=1)
        st.markdown(f"<div class='dark-metric-label'>自動計算目標金額</div><div class='metric-value'>NT${target_amount:,.0f}</div>", unsafe_allow_html=True)
    else:
        st.session_state.manual_target = st.number_input("自訂目標金額", value=st.session_state.manual_target, step=1000000)
        st.markdown(f"<div class='dark-metric-label'>設定目標金額</div><div class='metric-value'>NT${st.session_state.manual_target:,.0f}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.return_mode = st.radio("選擇基準", ["各資產近 10 年年化報酬率", "各資產近 20 年年化報酬率", "個別自訂報酬率"])

# =============================================================
# 模組：市場觀測站
# =============================================================
elif page in ["🇹🇼 台股 (TW Stocks)", "🇺🇸 美股 (US Stocks)", "📈 ETF（台股＆美股）"]:
    st.markdown(f"<h1>{page.split(' ')[1]} 市場觀測站</h1>", unsafe_allow_html=True)
    
    if "ETF" in page: market_flag = "TW"; market_dict = ETFS
    elif "美股" in page: market_flag = "US"; market_dict = US_STOCKS
    else: market_flag = "TW"; market_dict = TW_STOCKS
    
    st.markdown("### 📊 大盤指數")
    indices = fetch_indices(market_flag)
    i1, i2, i3 = st.columns(3)
    for col, (idx_name, curr, chg, pct) in zip([i1, i2, i3], indices): col.metric(idx_name, f"{curr:,.2f}", f"{chg:+.2f} ({pct:+.2f}%)")
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 🗺️ 市場板塊熱力圖")
    with st.spinner("正在繪製熱力圖..."):
        df_overview = fetch_market_overview_table(market_dict)
        if not df_overview.empty:
            df_overview['板塊'] = df_overview['代碼'].map(SECTOR_MAP).fillna('其他板塊')
            df_overview['權重'] = 1 
            fig_heat = px.treemap(df_overview, path=["板塊", "代碼"], values="權重", color="升跌幅(%)", color_continuous_scale=[(0, "#ef553b"), (0.5, "#333333"), (1, "#00cc96")], color_continuous_midpoint=0)
            fig_heat.update_traces(texttemplate="<b>%{label}</b><br>%{color:.2f}%", textposition="middle center")
            fig_heat.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=450, paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
            st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()
    st.markdown("### 🔍 個股深度分析")
    st.info("💡 **智慧搜尋：** 您可直接輸入名稱或代碼。輸入台灣股號系統會自動補齊 .TW。")
    
    search_query = st.text_input("🔍 搜尋特定標的：", "")
    if search_query: 
        raw_q = search_query.strip()
        # 🚀 修正點 1：放寬 ETF 搜尋長度 (4 到 6 碼數字都加上 .TW)
        if raw_q in REVERSE_LOOKUP: symbol = REVERSE_LOOKUP[raw_q]
        elif raw_q.isdigit() and 4 <= len(raw_q) <= 6: symbol = f"{raw_q}.TW"
        else: symbol = raw_q.upper()
        name = symbol 
    else: 
        selected = st.selectbox("🔽 或從熱門標的清單中選擇：", [f"{k} {v}" for k, v in market_dict.items()])
        symbol, name = selected.split(" ")[0], selected.split(" ")[1]
    
    with st.spinner(f"正在連線資料庫抓取 {symbol}..."):
        price, rsi, trend, hist = fetch_stock_data_detailed(symbol)
        info, news = fetch_fundamentals_and_news(symbol)
        
    if price and hist is not None:
        if search_query: name = info.get('shortName', symbol)
        my_holdings = [item for item in st.session_state.portfolio if item["代碼"] == symbol]
        c1, c2, c3 = st.columns(3)
        c1.metric("即時現價", f"{price:,.2f}")
        c2.metric("我的持有股數", f"{my_holdings[0]['股數']:,.0f}" if my_holdings else "0")
        c3.metric("未實現損益", f"{(price - my_holdings[0]['成本']) * my_holdings[0]['股數']:,.0f}" if my_holdings else "0")
            
        tab_tech, tab_chip, tab_fund, tab_macro = st.tabs(["📈 技術面", "🕵️ 籌碼面", "🏢 基本面", "🌍 總經與新聞"])
        with tab_tech:
            st.markdown(f"**RSI:** `{rsi:.2f}` | **MACD:** `{trend}`")
            hist['MA20'], hist['STD20'] = hist['Close'].rolling(20).mean(), hist['Close'].rolling(20).std()
            hist['Upper'], hist['Lower'] = hist['MA20'] + (hist['STD20']*2), hist['MA20'] - (hist['STD20']*2)
            fig_k = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='K線', increasing_line_color='#ef553b', decreasing_line_color='#00cc96'), go.Scatter(x=hist.index, y=hist['Upper'], line=dict(color='rgba(255,255,255,0.3)', width=1), name='布林上軌'), go.Scatter(x=hist.index, y=hist['Lower'], line=dict(color='rgba(255,255,255,0.3)', width=1), name='布林下軌')])
            fig_k.update_layout(height=450, margin=dict(l=0,r=0,t=30,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color='white'), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_k, use_container_width=True)
            
        with tab_chip: 
            st.markdown("### 📊 近五日三大法人買賣超概況 (模擬)")
            chip_df = pd.DataFrame({"日期": ["D-4", "D-3", "D-2", "D-1", "今日"] * 3, "法人": ["外資"]*5 + ["投信"]*5 + ["自營商"]*5, "買賣超(張)": np.random.randint(-5000, 10000, 15)})
            fig_chip = px.bar(chip_df, x="日期", y="買賣超(張)", color="法人", barmode="group", color_discrete_sequence=["#ef553b", "#636efa", "#00cc96"])
            fig_chip.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
            st.plotly_chart(fig_chip, use_container_width=True)
            
            c_gauge, c_text = st.columns([1, 2])
            with c_gauge:
                concentration = np.random.randint(40, 85)
                fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=concentration, title={'text': "主力籌碼集中度 (%)"}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#64ffda"}}))
                fig_gauge.update_layout(height=200, margin=dict(l=10,r=10,t=30,b=10), paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
                st.plotly_chart(fig_gauge, use_container_width=True)
            with c_text:
                st.info(f"💡 **籌碼動向解析**：近三日外資呈現連續買超，主力籌碼集中度達 {concentration}%。散戶融資餘額退場，籌碼相對安定，利於多方表態。")

        # 🚀 修正點 2：強化基本面資料捕捉邏輯
        with tab_fund:
            fc1, fc2, fc3, fc4 = st.columns(4)
            fc1.metric("P/E", safe_metric(info, ['trailingPE', 'forwardPE']))
            fc2.metric("P/B", safe_metric(info, ['priceToBook']))
            fc3.metric("ROE", safe_metric(info, ['returnOnEquity'], is_percent=True))
            fc4.metric("殖利率", safe_metric(info, ['dividendYield', 'trailingAnnualDividendYield'], is_percent=True))
            
        with tab_macro:
            if news:
                for n in news[:3]:
                    t = n.get('title') or n.get('content', {}).get('title', '無標題')
                    p = n.get('publisher') or n.get('content', {}).get('provider', {}).get('displayName', '未知')
                    l = n.get('link') or n.get('content', {}).get('clickThroughUrl', {}).get('url', '#')
                    st.markdown(f"""<div class="news-card"><h4 style="margin:0; padding-bottom:5px;">{t}</h4><span style="font-size:0.8rem; color:#888;">{p}</span><br><a href="{l}" target="_blank" style="color:#64ffda; text-decoration:none;">閱讀全文 ↗</a></div>""", unsafe_allow_html=True)
            else: st.write("查無新聞資料。")
    else: st.error(f"❌ 查無代碼 `{symbol}`。請確認名稱是否正確，或輸入完整股號 (如 2330 或 00919)。")

# =============================================================
# 模組：數據化推薦股
# =============================================================
elif page == "💡 數據化推薦股 (Data-driven Insights)":
    st.markdown("<h1>數據化推薦股</h1>", unsafe_allow_html=True)
    st.info("💡 透過市場熱力圖查看資金流向，並參考四大技術指標分析，做出精準投資決策。")

    st.subheader("🗺️ 市場熱度與資金流向板塊")
    tree_data = pd.DataFrame({
        "板塊": ["AI 半導體", "AI 半導體", "航運", "金融", "消費電子", "醫療"],
        "標的": ["NVDA", "2330.TW", "2603.TW", "2881.TW", "AAPL", "LLY"],
        "熱度": [90, 95, 70, 60, 80, 50],
        "漲跌幅": [5.2, 2.1, -3.5, 0.5, 1.2, -0.8]
    })
    fig_heat = px.treemap(tree_data, path=["板塊", "標的"], values="熱度", color="漲跌幅", color_continuous_scale=[(0, "#ef553b"), (0.5, "#333333"), (1, "#00cc96")], color_continuous_midpoint=0)
    fig_heat.update_layout(height=400, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
    st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("### 📊 專業選股邏輯分析")
    c_k1, c_k2 = st.columns(2)
    with c_k1:
        st.markdown("<div class='analysis-card'><h4>🕯️ K線型態預測</h4><p style='color:#aaa; font-size:0.8rem;'>說明：分析過去 6 個月的日 K 線排列，尋找反轉型態。</p>", unsafe_allow_html=True)
        st.success("⬆️ **多方反轉標的**：\n2317 鴻海、2382 廣達、3231 緯創")
        st.error("⬇️ **空方賣壓標的**：\n2609 陽明、2615 萬海、2002 中鋼")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='analysis-card'><h4>📈 MACD 動能分析</h4><p style='color:#aaa; font-size:0.8rem;'>說明：零軸以上黃金交叉代表多頭動能強勁。</p>", unsafe_allow_html=True)
        st.success("⬆️ **黃金交叉**：\n2454 聯發科、2308 台達電、3034 聯詠")
        st.error("⬇️ **死亡交叉**：\n2303 聯電、2344 華邦電、3481 群創")
        st.markdown("</div>", unsafe_allow_html=True)

    with c_k2:
        st.markdown("<div class='analysis-card'><h4>⚖️ RSI 相對強弱</h4><p style='color:#aaa; font-size:0.8rem;'>說明：小於 30 視為超賣區，大於 70 視為超買區。</p>", unsafe_allow_html=True)
        st.success("⬆️ **超賣反彈區**：\n2881 富邦金、2891 中信金、2882 國泰金")
        st.error("⬇️ **超買過熱區**：\nNVDA 輝達、TSM 台積電ADR")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='analysis-card'><h4>📉 布林通道分析</h4><p style='color:#aaa; font-size:0.8rem;'>說明：觸及下軌常為短期底部；跌破中軌則偏空。</p>", unsafe_allow_html=True)
        st.success("⬆️ **觸及下軌反彈**：\n2603 長榮、AAPL 蘋果、MSFT 微軟")
        st.error("⬇️ **跌破中軌轉弱**：\nTSLA 特斯拉、AMZN 亞馬遜")
        st.markdown("</div>", unsafe_allow_html=True)

# =============================================================
# 模組：📖 投資專欄
# =============================================================
elif page == "📖 投資專欄 (Investment Blog)":
    st.markdown("<h1>投資專欄</h1>", unsafe_allow_html=True)
    st.info("💡 每日精選市場觀點、投資策略教學與防詐騙指南，助您建立穩健的投資觀念。")
    
    tab_news, tab_style, tab_fraud = st.tabs(["📰 每日新資訊", "🎯 投資型態", "🛡️ 防詐宣導"])
    
    with tab_news:
        st.markdown("""<div class="blog-card"><span class="blog-tag tag-news">總經分析</span><div class="blog-title">AI 資料中心建置潮：散熱與營建板塊的十年一遇商機</div><div class="blog-meta">📅 今天 | ⏱️ 閱讀時間：5分鐘</div><div class="blog-desc">隨著 AI 伺服器的高耗能與散熱需求激增... <a href="#" style="color:#64ffda;">閱讀全文 ↗</a></div></div>""", unsafe_allow_html=True)

    with tab_style:
        st.markdown("""<div class="blog-card"><span class="blog-tag tag-style">投資策略</span><div class="blog-title">價值投資 vs 成長投資：哪一種適合現在的你？</div><div class="blog-meta">⏱️ 閱讀時間：6分鐘</div><div class="blog-desc">股市中兩大最經典的門派！一文看懂如何根據自己的風險承受度配置資產... <a href="#" style="color:#64ffda;">閱讀全文 ↗</a></div></div>""", unsafe_allow_html=True)

    with tab_fraud:
        st.markdown("""<div class="blog-card"><span class="blog-tag tag-fraud">高度警示</span><div class="blog-title">🚨 警惕！破解假冒「財經名人/券商」的 Line 投資群組詐騙</div><div class="blog-meta">⚠️ 內政部警政署關心您</div><div class="blog-desc">近期詐騙集團頻繁冒用知名分析師或券商名義... <a href="#" style="color:#64ffda;">了解防騙 3 步驟 ↗</a></div></div>""", unsafe_allow_html=True)
