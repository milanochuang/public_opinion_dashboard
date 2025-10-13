def trend_line_and_filters(mode="both"):
    if mode != "wordcloud":
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

    if mode == "wordcloud":
        start_date = df["date"].min().tz_localize("UTC") if df["date"].dt.tz is None else df["date"].min()
        end_date = df["date"].max().tz_localize("UTC") if df["date"].dt.tz is None else df["date"].max()

    # 文字雲
    st.subheader("☁️ 評價詞文字雲")
    wc_party = st.selectbox("選擇政黨（文字雲）", df["target"].unique(), key="wordcloud_party")
    wc_subcat = st.selectbox("選擇子類別", ["全部"] + sorted(df["subcategory"].unique().tolist()), key="wordcloud_subcat")
    wc_polarity = st.selectbox("選擇正負極性", ["全部", "positive", "negative"], key="wordcloud_polarity")

    # 新增：文字雲專用日期範圍選取（以當前篩選的起訖作為預設值）
    # 備註：date_input 回傳日期（無時區），此處將其轉為 UTC 的起訖時間區間 [wc_start_utc, wc_end_utc)
    default_wc_start = (start_date.tz_convert("UTC") if hasattr(start_date, "tzinfo") and start_date.tzinfo else start_date).date()
    default_wc_end = (end_date.tz_convert("UTC") if hasattr(end_date, "tzinfo") and end_date.tzinfo else end_date).date()
    wc_date_range = st.date_input(
        "選擇日期範圍（文字雲）",
        value=(default_wc_start, default_wc_end),
        key="wordcloud_date_range"
    )
    if isinstance(wc_date_range, (list, tuple)) and len(wc_date_range) == 2:
        wc_start_utc = pd.to_datetime(wc_date_range[0]).tz_localize("UTC")
        wc_end_utc = (pd.to_datetime(wc_date_range[1]) + pd.Timedelta(days=1)).tz_localize("UTC")
    else:
        # 若使用者只選單日，視為該日整天
        wc_start_utc = pd.to_datetime(wc_date_range).tz_localize("UTC")
        wc_end_utc = (pd.to_datetime(wc_date_range) + pd.Timedelta(days=1)).tz_localize("UTC")

    # 依文字雲日期範圍過濾
    wc_df = df[(df["target"] == wc_party) & (df["date"] >= wc_start_utc) & (df["date"] < wc_end_utc)]
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