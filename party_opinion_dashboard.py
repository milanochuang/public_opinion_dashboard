import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import jieba
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta, timezone
import os

# =========================
# 0) 片段模式：讀取查詢參數
# =========================
def qget(name, default=None):
    """讀取單一 query 參數（自動相容新舊 API）"""
    try:
        # Streamlit 1.30+（若是多值，取第一個）
        val = st.query_params.get(name, default)
        # st.query_params 回傳字串或 None；舊版會是 list
        return val if not isinstance(val, list) else (val[0] if val else default)
    except Exception:
        return st.experimental_get_query_params().get(name, [default])[0]

def qget_list(name):
    """讀取以逗號分隔的多值參數為 list"""
    raw = qget(name)
    if raw is None or raw == "":
        return None
    return [s for s in map(str.strip, raw.split(",")) if s]

section = (qget("section", "full") or "full").lower()
embedded = str(qget("embedded", "false")).lower() in {"true", "1", "yes"}
# 允許用 month=YYYY-MM 指定月份
month_param = qget("month")  # 例如 "2025-09"

# 內嵌模式：隱藏雜訊（給 iframe 漂亮畫面）
if embedded:
    st.markdown("""
    <style>
      header, footer {visibility: hidden;}
      .stDeployButton, .viewerBadge_container__1QSob {display: none !important;}
      .stAppToolbar {display: none !important;}
      body {overflow: hidden;}
    </style>
    """, unsafe_allow_html=True)

# ===== 1. 資料讀取 =====
@st.cache_data(ttl=3600)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp" in st.secrets:
        creds_dict = st.secrets["gcp"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("sheet_key.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1LoiXIOYv6A5Ws3cn_95wNRmXIWltQgSbXOTQ5lLWDzA/edit?gid=1977939127#gid=1977939127")
    worksheet = sheet.sheet1
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    # 全部時間的最小/最大月份（UTC）
    df["_month_floor"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df

df = load_data()

# 小工具：依 month_label（YYYY-MM）切資料
def month_slice(df, label_yyyy_mm: str):
    month_start = pd.to_datetime(label_yyyy_mm + "-01").tz_localize("UTC")
    next_month_start = (month_start + pd.offsets.MonthBegin(1))
    prev_month_start = (month_start - pd.offsets.MonthBegin(1))
    current_df = df[(df["date"] >= month_start) & (df["date"] < next_month_start)]
    prev_df = df[(df["date"] >= prev_month_start) & (df["date"] < month_start)]
    return month_start, current_df, prev_df

# ===== 共用元件 =====
def title_header():
    st.markdown("<h1 style='text-align: center;'>台灣政黨線上評論分析儀表板</h1>", unsafe_allow_html=True)

def kpi_all_time():
    total_all = len(df)
    dpp_all = (df["target"] == "民主進步黨").sum()
    kmt_all = (df["target"] == "中國國民黨").sum()
    tpp_all = (df["target"] == "台灣民眾黨").sum()

    st.subheader("📊 全期間政黨評論總覽")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("總評論數", total_all)
    col2.metric("民進黨評論數", dpp_all)
    col3.metric("國民黨評論數", kmt_all)
    col4.metric("民眾黨評論數", tpp_all)

def overall_subcats():
    st.subheader("📊 評價子類別分布（全期間）")
    party_logos = {
        "民進黨": "https://upload.wikimedia.org/wikipedia/zh/c/c1/Emblem_of_Democratic_Progressive_Party_%28new%29.svg",
        "國民黨": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Emblem_of_the_Kuomintang.svg",
        "民眾黨": "https://upload.wikimedia.org/wikipedia/commons/0/0c/Emblem_of_Taiwan_People%27s_Party_2019.svg"
    }
    parties = df["target"].unique()
    for party in parties:
        logo_url = party_logos.get(party, "")
        st.markdown(
            f"<h4><img src='{logo_url}' width='30' style='vertical-align: middle;'> {party}</h4>",
            unsafe_allow_html=True
        )
        d = df[df["target"] == party]
        bar = d.groupby(["subcategory", "polarity"]).size().reset_index(name="count")
        fig = px.bar(
            bar,
            x="subcategory",
            y="count",
            color="polarity",
            barmode="group",
            color_discrete_map={"positive": "lightgreen", "negative": "lightcoral"}
        )
        fig.update_yaxes(range=[0, df["subcategory"].value_counts().max() * 1.1])
        st.plotly_chart(fig, use_container_width=True, key=f"all-{party}-bar-chart")

def month_kpis_and_subcats(selected_label: str):
    # KPI（當月 vs 上月）
    month_start, current_df, prev_df = month_slice(df, selected_label)

    st.subheader(f"📊 {month_start.month} 月份政黨評論總量變化")
    col1, col2, col3, col4 = st.columns(4)

    total_now = len(current_df)
    total_prev = len(prev_df)

    dpp_now = (current_df["target"] == "民主進步黨").sum()
    dpp_prev = (prev_df["target"] == "民主進步黨").sum()

    kmt_now = (current_df["target"] == "中國國民黨").sum()
    kmt_prev = (prev_df["target"] == "中國國民黨").sum()

    tpp_now = (current_df["target"] == "台灣民眾黨").sum()
    tpp_prev = (prev_df["target"] == "台灣民眾黨").sum()

    col1.metric("總評論數", total_now, delta=f"{total_now - total_prev:+}")
    col2.metric("民進黨評論數", dpp_now, delta=f"{dpp_now - dpp_prev:+}")
    col3.metric("國民黨評論數", kmt_now, delta=f"{kmt_now - kmt_prev:+}")
    col4.metric("民眾黨評論數", tpp_now, delta=f"{tpp_now - tpp_prev:+}")

    # 當月子類別分布
    st.subheader("📊 評價子類別分布（當月）")
    party_logos = {
        "民進黨": "https://upload.wikimedia.org/wikipedia/zh/c/c1/Emblem_of_Democratic_Progressive_Party_%28new%29.svg",
        "國民黨": "https://upload.wikimedia.org/wikipedia/commons/a/a1/Emblem_of_the_Kuomintang.svg",
        "民眾黨": "https://upload.wikimedia.org/wikipedia/commons/0/0c/Emblem_of_Taiwan_People%27s_Party_2019.svg"
    }
    parties = df["target"].unique()
    for party in parties:
        logo_url = party_logos.get(party, "")
        st.markdown(
            f"<h4><img src='{logo_url}' width='30' style='vertical-align: middle;'> {party}</h4>",
            unsafe_allow_html=True
        )
        d = current_df[current_df["target"] == party]
        bar = d.groupby(["subcategory", "polarity"]).size().reset_index(name="count")
        fig = px.bar(
            bar, x="subcategory", y="count", color="polarity", barmode="group",
            color_discrete_map={"positive": "lightgreen", "negative": "lightcoral"}
        )
        fig.update_yaxes(range=[0, 50])
        st.plotly_chart(fig, use_container_width=True, key=f"month-{party}-bar-chart")

def trend_line_and_filters():
    st.subheader("🎯 選取日期與目標政黨ddd")
    min_month = df["date"].dropna().min().to_period("M").to_timestamp()
    max_month = df["date"].dropna().max().to_period("M").to_timestamp()
    month_range = pd.date_range(start=min_month, end=max_month, freq="MS")
    month_labels = [d.strftime("%Y-%m") for d in month_range]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_label = st.selectbox("起始月份", month_labels, index=0, key="start_month")
        end_label = st.selectbox("結束月份", month_labels, index=len(month_labels)-1, key="end_month")
        start_date = pd.to_datetime(start_label + "-01").tz_localize("UTC")
        end_date = (pd.to_datetime(end_label + "-01") + pd.offsets.MonthEnd(1)).tz_localize("UTC")
    with col2:
        selected_parties = st.multiselect("選擇政黨", options=df["target"].unique().tolist(), default=df["target"].unique().tolist())
    with col3:
        all_subcats = sorted(df["subcategory"].dropna().unique().tolist())
        selected_subcats = st.multiselect("選擇子類別", options=["全部"] + all_subcats, default="全部")
    with col4:
        selected_polarity = st.multiselect("選擇正負極性", options=["全部", "positive", "negative"], default="全部")

    filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    if selected_parties:
        filtered = filtered[filtered["target"].isin(selected_parties)]
    if selected_subcats != ["全部"]:
        filtered = filtered[filtered["subcategory"].isin(selected_subcats)]
    if selected_polarity != ["全部"]:
        filtered = filtered[filtered["polarity"].isin(selected_polarity)]

    st.subheader("📈 趨勢折線圖")
    filtered["day"] = (filtered["date"] - pd.Timedelta(hours=8)).dt.floor("D")
    line_df = filtered.groupby(["day", "target", "subcategory", "polarity"]).size().reset_index(name="count")
    line_df["line_group"] = line_df["target"] + " - " + line_df["subcategory"] + " - " + line_df["polarity"]
    line = alt.Chart(line_df).mark_line(point=True).encode(
        x=alt.X("day:T", title="日期", axis=alt.Axis(format="%m/%d", labelAngle=0), scale=alt.Scale(domain=[start_date, end_date])),
        y=alt.Y("count:Q", title="評論數", scale=alt.Scale(domain=[0, 35])),
        color=alt.Color("line_group:N", title="政黨 + 子類別 + polarity"),
        tooltip=["day:T", "target:N", "subcategory:N", "polarity:N", "count:Q"]
    ).properties(width=800, height=400)
    st.altair_chart(line, use_container_width=True)

    # 文字雲
    st.subheader("☁️ 評價詞文字雲")
    wc_party = st.selectbox("選擇政黨（文字雲）", df["target"].unique(), key="wordcloud_party")
    wc_subcat = st.selectbox("選擇子類別", ["全部"] + sorted(df["subcategory"].unique().tolist()), key="wordcloud_subcat")
    wc_polarity = st.selectbox("選擇正負極性", ["全部", "positive", "negative"], key="wordcloud_polarity")
    wc_df = df[(df["target"] == wc_party) & (df["date"] >= start_date) & (df["date"] <= end_date)]
    if wc_subcat != "全部":
        wc_df = wc_df[wc_df["subcategory"] == wc_subcat]
    if wc_polarity != "全部":
        wc_df = wc_df[wc_df["polarity"] == wc_polarity]
    if not wc_df.empty:
        text = " ".join(wc_df["text_span"].astype(str).tolist())
        wc = WordCloud(font_path="Font.ttc", background_color="white", width=800, height=400).generate(text)
        plt.imshow(wc, interpolation="bilinear"); plt.axis("off")
        st.pyplot(plt)
    else:
        st.info("無資料可生成文字雲")

def raw_table():
    st.subheader("📋 原始評論資料")
    st.dataframe(df[["date", "target", "subcategory", "polarity", "text_span", "comment"]], use_container_width=True)

def intro_tab_content():
    st.markdown("### Appraisal framework")
    st.markdown("""
    Appraisal framework 是系統功能語言學中用來分析語言中表達評價、情感、態度等立場的理論架構。  
    其中 *Judgement* 是三大主類別（Attitude → Affect, Judgement, Appreciation）之一，專注於對人的行為進行評價。

    **Judgement 主要子類別：**
    - **Capacity 能力**：是否有能力達成任務（如「有能力」、「無能」、「很專業」）
    - **Tenacity 毅力**：是否堅持不懈、有恆心（如「努力」、「懶惰」）
    - **Veracity 誠實**：是否說實話、不欺瞞（如「誠實」、「說謊」）
    - **Propriety 品德**：是否合乎道德與社會規範（如「正直」、「貪污」）
    - **Normality 常態性**：是否符合期待、是否奇怪（如「正常」、「怪異」）
    """)

# =========================
# 主要渲染（full 或 片段）
# =========================
if section == "full":
    # 原本的完整頁面（含分頁）
    title_header()
    tab0, tab1 = st.tabs(["📊 儀表板", "📚 簡介"])

    with tab0:
        if st.button("🔄 資料更新"):
            st.cache_data.clear()
            st.rerun()

        # 全期間 KPI + 子類別分布
        kpi_all_time()
        overall_subcats()

        # 月份選單（互動版）
        min_month = df["_month_floor"].min()
        max_month = df["_month_floor"].max()
        month_range = pd.date_range(start=min_month, end=max_month, freq="MS")
        month_labels = [d.strftime("%Y-%m") for d in month_range]
        selected_label = st.selectbox("📅 選擇月份", month_labels, index=len(month_labels)-1)
        month_kpis_and_subcats(selected_label)

        # 篩選 + 趨勢 + 文字雲 + 原始表
        trend_line_and_filters()
        raw_table()

    with tab1:
        intro_tab_content()

else:
    # ===== 片段模式 =====
    # 預設顯示標題，以免全空白；若不要標題可拿掉
    title_header()

    # month 參數：片段需要月份時可用
    if month_param is None:
        # 自動抓最後一個月份
        last_label = df["_month_floor"].max().strftime("%Y-%m")
    else:
        last_label = month_param

    # 根據 section 選擇要渲染的片段
    if section in {"overview", "kpis_all_time"}:
        kpi_all_time()

    elif section in {"overall_subcats", "overall"}:
        overall_subcats()

    elif section in {"month_kpis", "month_overview"}:
        month_kpis_and_subcats(last_label)

    elif section in {"month_subcats"}:
        # 同上，month_kpis_and_subcats 已含子類別分布
        month_kpis_and_subcats(last_label)

    elif section in {"trend_line", "filters"}:
        trend_line_and_filters()

    elif section in {"wordcloud"}:
        # 簡化：直接呼叫 trend_line_and_filters，因為文字雲依賴互動選擇
        trend_line_and_filters()

    elif section in {"raw_table", "table"}:
        raw_table()

    elif section in {"intro"}:
        intro_tab_content()

    else:
        st.info("未知的 section，請使用：overview / overall_subcats / month_kpis / trend_line / wordcloud / raw_table / intro / full")