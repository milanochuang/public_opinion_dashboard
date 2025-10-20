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
import streamlit.components.v1 as components

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

# 允許用 scale=0.8 之類的比例縮放整頁（給 iframe 用）
_scale_raw = qget("scale", "1.0")
try:
    scale = float(_scale_raw)
except Exception:
    scale = 1.0

# 允許用 scroll=數字（像素）控制載入時自動往下滾動的距離
_scroll_raw = qget("scroll", "0")
try:
    scroll_px = int(float(_scroll_raw))
except Exception:
    scroll_px = 0

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

# 若指定縮放比例，將整個 App 視覺縮放，方便在 iframe 中一頁看全
if scale != 1.0:
    st.markdown(f"""
    <style>
      /* 盡量廣泛支援：優先用 zoom；不支援時退回 transform */
      @supports (zoom: 1) {{
        .stApp {{
          zoom: {scale};
        }}
      }}
      @supports not (zoom: 1) {{
        .stApp {{
          transform: scale({scale});
          transform-origin: top left;
        }}
        /* 避免縮放後被裁切，擴充可視區尺寸 */
        html, body {{
          width: calc(100% / {scale});
          height: calc(100% / {scale});
        }}
      }}
    </style>
    """, unsafe_allow_html=True)

# 若指定了 scroll 參數，載入後自動將頁面往下滾動（單位：px）
if scroll_px:
    components.html(
        f"""
        <script>
          // 等待一個小節點循環，確保 Streamlit 主要內容已排版完成
          setTimeout(function() {{
            // 往下滾動當前（Streamlit app）文件，而非外層 parent 網站
            window.scrollTo({{ top: {scroll_px}, left: 0, behavior: 'auto' }});
          }}, 200);
        </script>
        """,
        height=0,
    )

# --- 全域樣式：把 checkbox 變成圓角按鈕（不依賴 :has，僅中性樣式） ---
st.markdown(
    """
    <style>
      /* 將 Streamlit 的 checkbox 視覺成圓角按鈕（中性樣式） */
      #party-row div[data-testid="stCheckbox"] > label,
      #wc-party-row div[data-testid="stCheckbox"] > label,
      .pill-row div[data-testid="stCheckbox"] > label { 
        border: 1px solid #e5e7eb; border-radius: 999px; padding: 8px 14px; background: #fff; 
        display: inline-flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;
        writing-mode: horizontal-tb; white-space: nowrap; line-height: 1.2;
      }
      /* 子類別/極性已選樣式（將由動態樣式覆蓋） */
      .pill-row div[data-testid="stCheckbox"] > label.selected {
        background: #111827; color: #fff; border-color: #111827;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# —— 全域間距微調：讓參數之間更緊湊 ——
st.markdown(
    """
    <style>
      /* —— 全域間距微調：讓參數之間更緊湊 —— */
      /* 1) 調小各種控件的下邊距 */
      div[data-testid="stSelectbox"],
      div[data-testid="stMultiSelect"],
      div[data-testid="stDateInput"],
      div[data-testid="stSlider"],
      div[data-testid="stCheckbox"] {
        margin-bottom: 0.25rem !important; /* 原本約 0.75–1rem */
      }

      /* 2) 勾選膠囊的間距與尺寸更緊湊 */
      #party-row div[data-testid="stCheckbox"] > label,
      #wc-party-row div[data-testid="stCheckbox"] > label {
        padding: 4px 8px; /* 再收斂：按鈕本體更薄 */
        margin-right: 0; /* 垂直排列不需要右間距 */
        margin-bottom: 0; /* 壓掉 label 本身的底邊距 */
        line-height: 1.0;
      }
      .pill-row div[data-testid="stCheckbox"] > label {
        padding: 6px 10px;
        margin-right: 6px;
      }

      /* 3) 控件群組上下留白變小（小標題/群組之間） */
      .block-container h2, .block-container h3, .block-container h4 { 
        margin-top: 0.4rem !important; 
        margin-bottom: 0.4rem !important;
      }

      /* 4) 讓列狀容器之間的上下距離縮小 */
      .pill-row { margin-bottom: 0.25rem; }

      /* 5) 兩欄月份選擇器的欄內留白也收斂一些 */
      section[data-testid="stHorizontalBlock"] > div > div { padding-bottom: 0.25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 壓掉多餘空白：移除固定高度，統一用小間距堆疊
st.markdown(
    """
    <style>
      /* 壓掉多餘空白：移除固定高度，統一用小間距堆疊 */
      #date-col, #wc-date-col {
        display: flex; flex-direction: column; gap: 6px; /* 兩個月份下拉之間的距離 */
        min-height: auto; justify-content: flex-start; align-items: stretch;
      }
      #party-col, #wc-party-col {
        display: flex; flex-direction: column; gap: 2px; /* 三個政黨之間的距離 */
        min-height: auto; justify-content: flex-start; align-items: stretch;
      }
      #pol-col, #wc-pol-col {
        display: flex; flex-direction: column; gap: 2px;
        min-height: auto; justify-content: flex-start; align-items: stretch;
      }
      #pol-col div[data-testid="stCheckbox"], #wc-pol-col div[data-testid="stCheckbox"] {
        margin-bottom: 0 !important; padding-bottom: 0 !important;
      }
      /* 讓每個政黨膠囊/checkbox 更貼近 */
      #party-col div[data-testid="stCheckbox"], #wc-party-col div[data-testid="stCheckbox"] {
        margin-bottom: 0 !important; padding-bottom: 0 !important;
      }
      /* 壓掉外層 block 可能的底部留白 */
      #party-col > div, #wc-party-col > div, #date-col > div, #wc-date-col > div { 
        margin-bottom: 0 !important; padding-bottom: 0 !important; 
      }
    </style>
    """,
    unsafe_allow_html=True,
)

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


# ===== 新增：以文章為單位顯示推文 =====
import pandas as pd
import streamlit as st

def article_thread_view(
    df: pd.DataFrame,
    default_start: str | None = None,
    default_end: str | None = None,
    page_size: int = 10,
):
    """
    以文章為單位顯示：文章資訊 + 該文所有推文。
    需求欄位：
      - article_id, article_title, content, url, article_datetime
      - comment, target, subcategory, text_span, polarity, date, puship_datetime, other_comment
    """
    def _to_dt(x):
        try:
            return pd.to_datetime(x, errors="coerce", utc=True)
        except Exception:
            return pd.NaT
    for col in ["date", "puship_datetime", "article_datetime"]:
        if col in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].apply(_to_dt)
    with st.container():
        # 與前面一致：以月份選擇起訖
        min_month = df["date"].dropna().min().to_period("M").to_timestamp()
        max_month = df["date"].dropna().max().to_period("M").to_timestamp()
        month_range = pd.date_range(start=min_month, end=max_month, freq="MS")
        month_labels = [d.strftime("%Y-%m") for d in month_range]
        parties = sorted(df["target"].dropna().unique().tolist()) if "target" in df.columns else []
        subcats = sorted(df["subcategory"].dropna().unique().tolist()) if "subcategory" in df.columns else []
        pols = sorted(df["polarity"].dropna().unique().tolist()) if "polarity" in df.columns else []

        # Three-column layout for filters
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            start_label = st.selectbox("起始月份（文章彙整）", month_labels, index=0, key="thread_start_month")
            end_label = st.selectbox("結束月份（文章彙整）", month_labels, index=len(month_labels)-1, key="thread_end_month")
        with col2:
            st.markdown("**政黨**（不勾選 = 全部）")
            party_checks = []
            for p in parties:
                party_checks.append((p, st.checkbox(p, key=f"thread_party_{p}", value=False)))
            sel_parties = [p for p, on in party_checks if on]
        with col3:
            st.markdown("**極性**（不勾選 = 全部）")
            pol_pos = st.checkbox("positive", key="thread_pol_pos", value=False)
            pol_neg = st.checkbox("negative", key="thread_pol_neg", value=False)
            sel_pols = [p for p, on in [("positive", pol_pos), ("negative", pol_neg)] if on]

        start_utc = pd.to_datetime(start_label + "-01").tz_localize("UTC")
        end_utc = (pd.to_datetime(end_label + "-01") + pd.offsets.MonthEnd(1) + pd.Timedelta(days=1)).tz_localize("UTC")
        q = st.text_input("搜尋（推文 comment）", placeholder="輸入關鍵字...").strip()

        # 子類別（用勾選；不勾選 = 全部）
        st.markdown("**子類別（Judgement）**（不勾選 = 全部）")
        st.markdown('<div class="pill-row">', unsafe_allow_html=True)
        n_sc_cols = 6 if len(subcats) >= 12 else 4 if len(subcats) > 6 else 3
        sc_cols = st.columns(n_sc_cols) if subcats else [st]
        sc_checks = []
        for i, s in enumerate(subcats):
            with sc_cols[i % len(sc_cols)]:
                sc_checks.append((s, st.checkbox(s, key=f"thread_subcat_{s}", value=False)))
        st.markdown('</div>', unsafe_allow_html=True)
        sel_subcats = [s for s, on in sc_checks if on]

        sort_by = st.selectbox("文章排序依據", ["最新在前", "最舊在前", "最多推文在前", "最少推文在前"], index=0)
    # ===== 以「符合篩選條件的推文（每筆）」為主體 =====
    # 1) 先用月份區間過濾（以文章時間為主；若沒有則用推文時間或 date）
    base = df.copy()
    if "article_datetime" in base.columns and not base["article_datetime"].isna().all():
        base = base[(base["article_datetime"] >= start_utc) & (base["article_datetime"] < end_utc)]
    else:
        time_col = "puship_datetime" if "puship_datetime" in base.columns else "date"
        base = base[(base[time_col] >= start_utc) & (base[time_col] < end_utc)]

    # 2) 關鍵字搜尋（針對 comment 欄位）
    if q:
        if "comment" not in base.columns:
            base["comment"] = ""
        mask = base["comment"].astype(str).str.contains(q, case=False, na=False)
        base = base[mask]

    # 3) 依政黨/子類別/極性過濾（以推文欄位為準）
    if sel_parties:
        base = base[base["target"].isin(sel_parties)]
    if sel_subcats:
        base = base[base["subcategory"].isin(sel_subcats)]
    if sel_pols:
        base = base[base["polarity"].isin(sel_pols)]

    # 4) 排序（沿用 UI；「最多/最少推文在前」改以日期排序）
    if sort_by in ["最新在前", "最多推文在前"]:
        key_col = "article_datetime" if ("article_datetime" in base.columns and not base["article_datetime"].isna().all()) else ("puship_datetime" if "puship_datetime" in base.columns else "date")
        base = base.sort_values(by=[key_col], ascending=False)
    elif sort_by in ["最舊在前", "最少推文在前"]:
        key_col = "article_datetime" if ("article_datetime" in base.columns and not base["article_datetime"].isna().all()) else ("puship_datetime" if "puship_datetime" in base.columns else "date")
        base = base.sort_values(by=[key_col], ascending=True)

    # 5) 分頁（每一筆推文=一張卡）
    total_comments = len(base)
    if total_comments == 0:
        st.info("沒有符合條件的推文。")
        return
    n_pages = (total_comments + page_size - 1) // page_size
    page = 1
    start_idx = 0
    end_idx = 0
    page_df = pd.DataFrame()
    # 頁碼控制和顯示移到渲染卡片之後

    # 6) 逐筆渲染：標題= comment · polarity · subcategory；展開後顯示文章資訊與 other_comment 表
    import ast
    # 先計算分頁資訊
    page = st.session_state.get("thread_page", 1) if "thread_page" in st.session_state else 1
    page = min(max(1, int(page)), max(1, n_pages))
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_comments)
    page_df = base.iloc[start_idx:end_idx]
    for _, r in page_df.iterrows():
        comment_txt = str(r.get("comment", "")).strip()
        pol = str(r.get("polarity", "")).strip()
        subcat = str(r.get("subcategory", "")).strip()
        expander_title = f"💬 {comment_txt} · {pol} · {subcat}" if comment_txt else "💬 （無推文內容）"
        with st.expander(expander_title, expanded=False):
            # 文章資訊
            art_title = r.get("article_title", "")
            url = r.get("url", "")
            aid = r.get("article_id", "")
            st.markdown(f"**{art_title or '(無標題)'}**")
            if url:
                st.markdown(f"[前往原文]({url})")
            if aid:
                st.caption(f"article_id: {aid}")
            content = r.get("content", "")
            if isinstance(content, str) and content.strip():
                st.markdown("**內文**")
                st.write(content)

            # other_comment 展開成表格（每列一則）
            oc_raw = r.get("other_comment", None)
            rows = []
            if pd.notna(oc_raw):
                try:
                    lst = ast.literal_eval(str(oc_raw))
                    if isinstance(lst, list):
                        rows = [{"推文內容": str(x)} for x in lst]
                    else:
                        rows = [{"推文內容": str(oc_raw)}]
                except Exception:
                    rows = [{"推文內容": str(oc_raw)}]
            if rows:
                oc_df = pd.DataFrame(rows)
                st.dataframe(oc_df, use_container_width=True, hide_index=True)
            else:
                st.info("此筆資料沒有其他推文。")

    # 8) 頁碼控制（放在最下方）
    st.caption(f"顯示第 {start_idx+1}–{end_idx} 筆，共 {total_comments} 筆")
    st.number_input(
        "頁碼",
        min_value=1,
        max_value=max(1, n_pages),
        value=page,
        step=1,
        key="thread_page",
    )

    # 9) 匯出目前頁面的推文（僅當頁）
    if st.button("下載目前頁面的推文 CSV"):
        st.download_button(
            "下載 CSV",
            page_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="comments_page.csv",
            mime="text/csv"
        )

def trend_line_and_filters(mode: str = "both"):
    """Render filters + (line chart and/or wordcloud) depending on mode.
    mode ∈ {"both", "line", "wordcloud"}
    """

    # 上方共用篩選：僅在 both/line 模式顯示
    if mode in {"both", "line"}:
        st.markdown('<a id="filters"></a>', unsafe_allow_html=True)
        st.subheader("🎯 選取日期與目標政黨")
        min_month = df["date"].dropna().min().to_period("M").to_timestamp()
        max_month = df["date"].dropna().max().to_period("M").to_timestamp()
        month_range = pd.date_range(start=min_month, end=max_month, freq="MS")
        month_labels = [d.strftime("%Y-%m") for d in month_range]

        # 日期（左）・政黨（中）・極性（右）同一列（等寬 1:1:1）
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            start_label = st.selectbox("起始月份（趨勢圖）", month_labels, index=0, key="start_month")
            end_label = st.selectbox("結束月份（趨勢圖）", month_labels, index=len(month_labels)-1, key="end_month")
            start_date = pd.to_datetime(start_label + "-01").tz_localize("UTC")
            end_date = (pd.to_datetime(end_label + "-01") + pd.offsets.MonthEnd(1)).tz_localize("UTC")
        with col2:
            st.markdown("**政黨**（不勾選 = 全部）")
            parties_present = df["target"].dropna().unique().tolist()
            dpp_on = st.checkbox("民主進步黨", key="party_dpp", value=False)
            kmt_on = st.checkbox("中國國民黨", key="party_kmt", value=False)
            tpp_on = st.checkbox("台灣民眾黨", key="party_tpp", value=False)
        with col3:
            st.markdown("**極性**（不勾選 = 全部）")
            pol_pos = st.checkbox("positive", key="pol_btn_pos", value=False)
            pol_neg = st.checkbox("negative", key="pol_btn_neg", value=False)

        # 依勾選結果決定篩選（無勾選 = 全部）
        selected_parties = []
        if dpp_on and "民主進步黨" in parties_present:
            selected_parties.append("民主進步黨")
        if kmt_on and "中國國民黨" in parties_present:
            selected_parties.append("中國國民黨")
        if tpp_on and "台灣民眾黨" in parties_present:
            selected_parties.append("台灣民眾黨")
        if not selected_parties:
            selected_parties = [p for p in ["民主進步黨", "中國國民黨", "台灣民眾黨"] if p in parties_present]

        # --- 子類別一整列平均散佈 ---
        # 全寬 row
        st.markdown("**子類別（Judgement）**（不勾選 = 全部）")
        st.markdown('<div class="pill-row">', unsafe_allow_html=True)
        all_subcats = [s for s in sorted(df["subcategory"].dropna().unique().tolist())]
        ncols = 6 if len(all_subcats) >= 12 else 4 if len(all_subcats) > 6 else 3
        sc_cols = st.columns(ncols)
        sc_checks = []
        for i, s in enumerate(all_subcats):
            with sc_cols[i % ncols]:
                sc_checks.append((s, st.checkbox(s, key=f"subcat_btn_{s}", value=False)))
        st.markdown('</div>', unsafe_allow_html=True)
        selected_subcats = [s for s, on in sc_checks if on]
        # 讓被勾選的子類別/極性膠囊視覺加深（不依賴 :has）
        st.markdown(
            """
            <style>
              .pill-row div[data-testid='stCheckbox'] input:checked + label { background:#111827 !important; color:#fff !important; border-color:#111827 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        # --- 極性已合併至三欄，同步取得 selected_polarity ---
        selected_polarity = [p for p, on in [("positive", pol_pos), ("negative", pol_neg)] if on]
        st.markdown(
            """
            <style>
              .pill-row div[data-testid='stCheckbox'] input:checked + label { background:#111827 !important; color:#fff !important; border-color:#111827 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        # wordcloud-only 模式不顯示共用篩選，但仍計算預設起訖月作為文字雲的預設值
        min_month = df["date"].dropna().min().to_period("M").to_timestamp()
        max_month = df["date"].dropna().max().to_period("M").to_timestamp()
        start_date = min_month.tz_localize("UTC") if min_month.tzinfo is None else min_month
        end_date = (max_month + pd.offsets.MonthEnd(1)).tz_localize("UTC") if max_month.tzinfo is None else (max_month + pd.offsets.MonthEnd(1))
        selected_parties = None
        selected_subcats = ["全部"]
        selected_polarity = ["全部"]

    filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    if selected_parties:  # 有勾選才過濾；否則保留全部
        filtered = filtered[filtered["target"].isin(selected_parties)]
    if selected_subcats:  # 有勾選才過濾
        filtered = filtered[filtered["subcategory"].isin(selected_subcats)]
    if selected_polarity:  # 有勾選才過濾
        filtered = filtered[filtered["polarity"].isin(selected_polarity)]

    if mode in {"both", "line"}:
        filtered["day"] = (filtered["date"] - pd.Timedelta(hours=8)).dt.floor("D")
        line_df = filtered.groupby(["day", "target", "subcategory", "polarity"]).size().reset_index(name="count")
        line_df["line_group"] = line_df["target"] + " - " + line_df["subcategory"] + " - " + line_df["polarity"]
        line = alt.Chart(line_df).mark_line(point=True).encode(
            x=alt.X("day:T", title="日期", axis=alt.Axis(format="%m/%d", labelAngle=0), scale=alt.Scale(domain=[start_date, end_date])),
            y=alt.Y("count:Q", title="評論數", scale=alt.Scale(domain=[0, 35])),
            color=alt.Color(
                "line_group:N",
                legend=alt.Legend(
                    title="政黨 + 子類別 + polarity",
                    labelLimit=1000,  # 不截斷標籤
                    columns=1,
                    orient="right"
                )
            ),
            tooltip=["day:T", "target:N", "subcategory:N", "polarity:N", "count:Q"]
        ).properties(width=800, height=320)
        st.altair_chart(line, use_container_width=False)

    if mode in {"both", "wordcloud"}:
        st.subheader("☁️ 評價詞文字雲")

        # 參數：月份範圍（與趨勢圖相同的月份選擇器）
        min_month_wc = df["date"].dropna().min().to_period("M").to_timestamp()
        max_month_wc = df["date"].dropna().max().to_period("M").to_timestamp()
        month_range_wc = pd.date_range(start=min_month_wc, end=max_month_wc, freq="MS")
        month_labels_wc = [d.strftime("%Y-%m") for d in month_range_wc]

        # 日期（左）・政黨（中）・極性（右）同一列（等寬 1:1:1）
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            wc_start_label = st.selectbox("起始月份（文字雲）", month_labels_wc, index=0, key="wc_start_month")
            wc_end_label = st.selectbox("結束月份（文字雲）", month_labels_wc, index=len(month_labels_wc)-1, key="wc_end_month")
        with col2:
            st.markdown("**政黨**（不勾選 = 全部）")
            parties_present_wc = df["target"].dropna().unique().tolist()
            wc_dpp_on = st.checkbox("民主進步黨", key="wc_party_dpp", value=False)
            wc_kmt_on = st.checkbox("中國國民黨", key="wc_party_kmt", value=False)
            wc_tpp_on = st.checkbox("台灣民眾黨", key="wc_party_tpp", value=False)
        with col3:
            st.markdown("**極性**（不勾選 = 全部）")
            wc_pol_pos = st.checkbox("positive", key="wc_pol_btn_pos", value=False)
            wc_pol_neg = st.checkbox("negative", key="wc_pol_btn_neg", value=False)

        wc_start_utc = pd.to_datetime(wc_start_label + "-01").tz_localize("UTC")
        wc_end_utc = (pd.to_datetime(wc_end_label + "-01") + pd.offsets.MonthEnd(1) + pd.Timedelta(days=1)).tz_localize("UTC")
        wc_selected_parties = []
        if wc_dpp_on and "民主進步黨" in parties_present_wc:
            wc_selected_parties.append("民主進步黨")
        if wc_kmt_on and "中國國民黨" in parties_present_wc:
            wc_selected_parties.append("中國國民黨")
        if wc_tpp_on and "台灣民眾黨" in parties_present_wc:
            wc_selected_parties.append("台灣民眾黨")
        if not wc_selected_parties:
            wc_selected_parties = [p for p in ["民主進步黨", "中國國民黨", "台灣民眾黨"] if p in parties_present_wc]

        # 子類別列（不勾選 = 全部）
        st.markdown("**子類別（Judgement）**（不勾選 = 全部）")
        st.markdown('<div class="pill-row">', unsafe_allow_html=True)
        wc_all_subcats = [s for s in sorted(df["subcategory"].dropna().unique().tolist())]
        wc_ncols = 6 if len(wc_all_subcats) >= 12 else 4 if len(wc_all_subcats) > 6 else 3
        wc_sc_cols = st.columns(wc_ncols)
        wc_sc_checks = []
        for i, s in enumerate(wc_all_subcats):
            with wc_sc_cols[i % wc_ncols]:
                wc_sc_checks.append((s, st.checkbox(s, key=f"wc_subcat_btn_{s}", value=False)))
        st.markdown('</div>', unsafe_allow_html=True)
        wc_selected_subcats = [s for s, on in wc_sc_checks if on]
        # 讓被勾選的子類別/極性膠囊視覺加深（不依賴 :has）
        st.markdown(
            """
            <style>
              .pill-row div[data-testid='stCheckbox'] input:checked + label { background:#111827 !important; color:#fff !important; border-color:#111827 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        # 極性已合併至三欄，同步取得 wc_selected_polarity
        wc_selected_polarity = [p for p, on in [("positive", wc_pol_pos), ("negative", wc_pol_neg)] if on]
        st.markdown(
            """
            <style>
              .pill-row div[data-testid='stCheckbox'] input:checked + label { background:#111827 !important; color:#fff !important; border-color:#111827 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # 依參數產生單一文字雲（多黨則合併文字）
        wdf = df[(df["target"].isin(wc_selected_parties)) & (df["date"] >= wc_start_utc) & (df["date"] < wc_end_utc)]
        if wc_selected_subcats:
            wdf = wdf[wdf["subcategory"].isin(wc_selected_subcats)]
        if wc_selected_polarity:
            wdf = wdf[wdf["polarity"].isin(wc_selected_polarity)]

        if not wdf.empty:
            text = " ".join(wdf["text_span"].astype(str).tolist())
            wc_img = WordCloud(font_path="Font.ttc", background_color="white", width=900, height=420).generate(text)
            plt.imshow(wc_img, interpolation="bilinear"); plt.axis("off")
            st.pyplot(plt)
            # 顯示詞頻表格
            from collections import Counter
            tokens = text.split()
            freq = Counter(tokens)
            freq_df = pd.DataFrame(freq.items(), columns=["token", "frequency"]).sort_values("frequency", ascending=False)
            st.dataframe(freq_df, use_container_width=True, hide_index=True)
            # 下載詞頻 CSV
            # st.download_button(
            #     "下載詞頻 CSV",
            #     freq_df.to_csv(index=False).encode("utf-8-sig"),
            #     file_name="wordcloud_token_frequency.csv",
            #     mime="text/csv",
            # )
        else:
            st.info("無資料可生成文字雲")


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

        # 篩選 + 趨勢 + 文字雲
        trend_line_and_filters()
        st.subheader("🧵 文章與推文彙整（依文章聚合）")
        article_thread_view(df, page_size=8)

    with tab1:
        intro_tab_content()

else:
    # ===== 片段模式 =====
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


    elif section in {"trend_line", "filters"}:
        trend_line_and_filters(mode="line")

    elif section in {"wordcloud"}:
        trend_line_and_filters(mode="wordcloud")


    elif section in {"intro"}:
        intro_tab_content()

    else:
        st.info("未知的 section，請使用：overview / overall_subcats / trend_line / wordcloud / intro / full")