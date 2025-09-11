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
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1IFPlptD-G9W0_s6PKULvgioY5pSiCW4-79l-pMFjTRw/edit#gid=0")
    worksheet = sheet.sheet1
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    now_utc = datetime.now(timezone.utc)
    df = df[df["date"] >= now_utc - timedelta(days=30)]  # 近 30 天
    return df

df = load_data()
# ===== 2. KPI 數據卡 =====
st.markdown("<h1 style='text-align: center;'>台灣政黨線上評論分析儀表板</h1>", unsafe_allow_html=True)
if st.button("🔄 立即重新載入最新資料"):
    st.cache_data.clear()
    st.rerun()
st.subheader("📊 政黨評論總量變化")
col1, col2, col3, col4 = st.columns(4)
total = len(df)
dpp = len(df[df["target"] == "民進黨"])
kmt = len(df[df["target"] == "國民黨"])
tpp = len(df[df["target"] == "民眾黨"])
col1.metric("總評論數", total, "+3.2%")
col2.metric("民進黨評論數", dpp, "-1.5%")
col3.metric("國民黨評論數", kmt, "+6.7%")
col4.metric("民眾黨評論數", tpp, "+6.7%")

# ===== 3. 子類別分布圖（正負） =====
st.subheader("🧱 評價子類別分布（含正負極性）")
parties = df["target"].unique()
for party in parties:
    st.markdown(f"##### {party}")
    d = df[df["target"] == party]
    bar = d.groupby(["subcategory", "polarity"]).size().reset_index(name="count")
    fig = px.bar(bar, x="subcategory", y="count", color="polarity", barmode="group")
    st.plotly_chart(fig, use_container_width=True, key=f"{party}-bar-chart")

# ===== 新增日期與政黨篩選 =====
st.subheader("🎯 特定日期與政黨排名")
min_date = df["date"].min().date()
max_date = df["date"].max().date()
default_start = max(min_date, max_date - timedelta(days=7))
start_date, end_date = st.date_input("選擇日期區段", (default_start, max_date), min_value=min_date, max_value=max_date)

selected_parties = st.multiselect("選擇政黨", options=df["target"].unique().tolist(), default=df["target"].unique().tolist())

# 篩選資料
filtered = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]
if selected_parties:
    filtered = filtered[filtered["target"].isin(selected_parties)]

# ===== 4. 評價面向排名圖 =====
st.subheader("🏅 評價子類別 + polarity 排名")
rank = (
    filtered.groupby(["target", "subcategory", "polarity"])
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
    .head(10)
)
st.dataframe(rank, use_container_width=True)

# ===== 5. 趨勢折線圖（每小時） =====
st.subheader("📈 每小時評論趨勢")
df["hour"] = df["date"].dt.floor("H")
line_df = df.groupby(["hour", "target"]).size().reset_index(name="count")
line = alt.Chart(line_df).mark_line(point=True).encode(
    x=alt.X("hour:T", title="時間（每小時）", axis=alt.Axis(format="%m/%d %H:%M", tickMinStep=3600000, labelAngle=0)),
    y=alt.Y("count:Q", title="評論數"),
    color="target:N",
    tooltip=["hour:T", "target:N", "count:Q"]
).properties(width=800, height=400)
st.altair_chart(line, use_container_width=True)

# ===== 6. 評價詞文字雲 =====
st.subheader("☁️ 評價詞文字雲")
wc_party = st.selectbox("選擇政黨（文字雲）", df["target"].unique(), key="wordcloud_party")
wc_subcat = st.selectbox("選擇子類別", ["全部"] + sorted(df["subcategory"].unique().tolist()), key="wordcloud_subcat")
wc_df = df[df["target"] == wc_party]
if wc_subcat != "全部":
    wc_df = wc_df[wc_df["subcategory"] == wc_subcat]
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
