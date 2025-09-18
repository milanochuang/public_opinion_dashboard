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
import os# ===== 1. 資料讀取 =====
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
    return df

df = load_data()


# ===== 2. KPI 數據卡 =====
st.markdown("<h1 style='text-align: center;'>台灣政黨線上評論分析儀表板</h1>", unsafe_allow_html=True)

tab0, tab1 = st.tabs(["📊 儀表板", "📚 簡介"])

with tab0:
    if st.button("🔄 資料更新"):
        st.cache_data.clear()
        st.rerun()

    st.subheader("📊 全期間政黨評論總覽")
    col1, col2, col3, col4 = st.columns(4)

    total_all = len(df)
    dpp_all = (df["target"] == "民主進步黨").sum()
    kmt_all = (df["target"] == "中國國民黨").sum()
    tpp_all = (df["target"] == "台灣民眾黨").sum()

    col1.metric("總評論數", total_all)
    col2.metric("民進黨評論數", dpp_all)
    col3.metric("國民黨評論數", kmt_all)
    col4.metric("民眾黨評論數", tpp_all)

    st.subheader("📊 評價子類別分布")
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

    # 選擇月份
    # selected_month = st.date_input("📅 選擇月份", datetime.today().date().replace(day=1))
    # 修改為根據 df["date"] 的最小和最大日期決定月份範圍
    min_month = df["date"].min().to_period("M").to_timestamp()
    max_month = df["date"].max().to_period("M").to_timestamp()

    month_range = pd.date_range(start=min_month, end=max_month, freq="MS")
    month_labels = [d.strftime("%Y-%m") for d in month_range]

    selected_label = st.selectbox("📅 選擇月份", month_labels, index=len(month_labels)-1)
    month_start = pd.to_datetime(selected_label + "-01").tz_localize("UTC")
    next_month_start = (month_start + pd.offsets.MonthBegin(1))
    prev_month_start = (month_start - pd.offsets.MonthBegin(1))
    current_df = df[(df["date"] >= month_start) & (df["date"] < next_month_start)]
    prev_df = df[(df["date"] >= prev_month_start) & (df["date"] < month_start)]
    # print("current:", current_df['date'])
    print("month_start", month_start.month)
    # print(selected_label)
    st.subheader("📊 {}月份政黨評論總量變化".format(month_start.month))
    col1, col2, col3, col4 = st.columns(4)

    total_now = len(current_df)
    total_prev = len(prev_df)
    total_delta = total_now - total_prev

    dpp_now = (current_df["target"] == "民主進步黨").sum()
    dpp_prev = (prev_df["target"] == "民主進步黨").sum()
    # print("dpp_now, dpp_prev: ", dpp_now, dpp_prev)
    dpp_delta = dpp_now - dpp_prev

    kmt_now = (current_df["target"] == "中國國民黨").sum()
    kmt_prev = (prev_df["target"] == "中國國民黨").sum()
    kmt_delta = kmt_now - kmt_prev

    tpp_now = (current_df["target"] == "台灣民眾黨").sum()
    tpp_prev = (prev_df["target"] == "台灣民眾黨").sum()
    tpp_delta = tpp_now - tpp_prev

    col1.metric("總評論數", total_now)
    col2.metric("民進黨評論數", dpp_now, delta=f"{dpp_delta:+}")
    col3.metric("國民黨評論數", kmt_now, delta=f"{kmt_delta:+}")
    col4.metric("民眾黨評論數", tpp_now, delta=f"{tpp_delta:+}")

    # ===== 3. 子類別分布圖（正負） =====
    st.subheader("📊 評價子類別分布")

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
            bar,
            x="subcategory",
            y="count",
            color="polarity",
            barmode="group",
            color_discrete_map={"positive": "lightgreen", "negative": "lightcoral"}
        )
        fig.update_yaxes(range=[0, 50])
        st.plotly_chart(fig, use_container_width=True, key=f"month-{party}-bar-chart")

    # ===== 新增日期與政黨篩選 =====
    st.subheader("🎯 選取日期與目標政黨")
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

    # 篩選資料
    filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    if selected_parties:
        filtered = filtered[filtered["target"].isin(selected_parties)]
    if selected_subcats != ["全部"]:
        filtered = filtered[filtered["subcategory"].isin(selected_subcats)]
    if selected_polarity != ["全部"]:
        filtered = filtered[filtered["polarity"].isin(selected_polarity)]

    # ===== 4. 評價面向排名圖 =====
    st.subheader("🏅 評價子類別 + polarity 排名")
    rank = (
        filtered.groupby(["target", "subcategory", "polarity"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(10)
    )
    st.dataframe(rank, use_container_width=True, hide_index=True)

    # ===== 5. 趨勢折線圖（每小時） =====
    st.subheader("📈 趨勢折線圖")
    filtered["day"] = (filtered["date"] - pd.Timedelta(hours=8)).dt.floor("D")
    line_df = filtered.groupby(["day", "target", "subcategory", "polarity"]).size().reset_index(name="count")
    line_df["line_group"] = line_df["target"] + " - " + line_df["subcategory"] + " - " + line_df["polarity"]
    line = alt.Chart(line_df).mark_line(point=True).encode(
        x=alt.X(
            "day:T",
            title="日期",
            axis=alt.Axis(format="%m/%d", labelAngle=0),
            scale=alt.Scale(domain=[start_date, end_date])
        ),
        y=alt.Y("count:Q", title="評論數"),
        color=alt.Color("line_group:N", title="政黨 + 子類別 + polarity"),
        tooltip=["day:T", "target:N", "subcategory:N", "polarity:N", "count:Q"]
    ).properties(width=800, height=400)

    st.altair_chart(line, use_container_width=True)

    # ===== 6. 評價詞文字雲 =====
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
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        st.pyplot(plt)
    else:
        st.info("無資料可生成文字雲")

    # ===== 7. 原始資料表格 =====
    st.subheader("📋 原始評論資料")
    st.dataframe(df[["date", "target", "subcategory", "polarity", "text_span", "comment"]], use_container_width=True)

with tab1:
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