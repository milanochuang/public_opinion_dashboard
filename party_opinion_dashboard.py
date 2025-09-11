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
# st.markdown("<h1 style='text-align: center;'>台灣政黨線上評論分析儀表板</h1>", unsafe_allow_html=True)

# col_title, col_button = st.columns([5, 1])

# with col_title:
st.markdown("<h1 style='text-align: center;'>台灣政黨線上評論分析儀表板</h1>", unsafe_allow_html=True)

# with col_button:
if st.button("🔄 資料更新"):
    st.cache_data.clear()
    st.rerun()

st.subheader("📊 政黨評論總量變化")
col1, col2, col3, col4 = st.columns(4)

# 當前小時 & 前一小時（基準往前推 1 小時）
now_hour = df["date"].dt.floor("H").max() - timedelta(hours=1)
prev_hour = now_hour - timedelta(hours=1)
current_df = df[df["date"].dt.floor("H") == now_hour]
prev_df = df[df["date"].dt.floor("H") == prev_hour]

# 總評論數
total = len(df)
total_now = len(current_df)
total_prev = len(prev_df)
total_delta = total_now - total_prev

# 民進黨
dpp_now = (current_df["target"] == "民進黨").sum()
dpp_prev = (prev_df["target"] == "民進黨").sum()
dpp_delta = dpp_now - dpp_prev

# 國民黨
kmt_now = (current_df["target"] == "國民黨").sum()
kmt_prev = (prev_df["target"] == "國民黨").sum()
kmt_delta = kmt_now - kmt_prev

# 民眾黨
tpp_now = (current_df["target"] == "民眾黨").sum()
tpp_prev = (prev_df["target"] == "民眾黨").sum()
tpp_delta = tpp_now - tpp_prev

col1.metric("本小時評論數", total)
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
    st.plotly_chart(fig, use_container_width=True, key=f"{party}-bar-chart")

# ===== 新增日期與政黨篩選 =====
st.subheader("🎯 選取日期與目標政黨")
min_date = df["date"].min().date()
max_date = df["date"].max().date()
default_start = max(min_date, max_date - timedelta(days=7))

col1, col2, col3, col4 = st.columns(4)
with col1:
    start_date, end_date = st.date_input("選擇日期區段", (default_start, max_date), min_value=min_date, max_value=max_date)
with col2:
    selected_parties = st.multiselect("選擇政黨", options=df["target"].unique().tolist(), default=df["target"].unique().tolist())
with col3:
    all_subcats = sorted(df["subcategory"].dropna().unique().tolist())
    selected_subcats = st.multiselect("選擇子類別", options=["全部"] + all_subcats, default="全部")
with col4:
    selected_polarity = st.multiselect("選擇正負極性", options=["全部", "positive", "negative"], default="全部")

# 篩選資料
filtered = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]
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
filtered["hour"] = (filtered["date"] - pd.Timedelta(hours=8)).dt.floor("H")
line_df = filtered.groupby(["hour", "target", "subcategory", "polarity"]).size().reset_index(name="count")
line_df["line_group"] = line_df["target"] + " - " + line_df["subcategory"] + " - " + line_df["polarity"]
line = alt.Chart(line_df).mark_line(point=True).encode(
    x=alt.X("hour:T", title="時間", axis=alt.Axis(format="%m/%d %H:%M", tickMinStep=3600000, labelAngle=0)),
    y=alt.Y("count:Q", title="評論數"),
    color=alt.Color("line_group:N", title="政黨 + 子類別 + polarity"),
    tooltip=["hour:T", "target:N", "subcategory:N", "polarity:N", "count:Q"]
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
