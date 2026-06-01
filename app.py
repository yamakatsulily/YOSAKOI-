import streamlit as st
import pandas as pd
import urllib.parse
import re
import unicodedata

st.set_page_config(page_title="YOSAKOI現地投稿くん", layout="centered", initial_sidebar_state="expanded")

# ==========================================
# 🎨 デザイン・CSS
# ==========================================
st.markdown("""
<style>
    .block-container { padding-top: 4.5rem; padding-bottom: 2rem; }
    div.stButton > button { border-radius: 8px; font-weight: bold; }
    .custom-title { text-align: center; font-size: 1.8rem; font-weight: 800; color: #333; line-height: 1.2; }
    .custom-subtitle { text-align: center; font-size: 0.8rem; color: #666; margin-bottom: 20px; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 0. 共通関数（超強力スキャナー）
# ==========================================
def normalize_text(text):
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFKC', text).lower()
    return text.replace("櫻", "桜").replace("樂", "楽").replace("眞", "真").replace("邊", "辺").replace("澤", "沢").replace("濱", "浜")

def extract_teams_from_blob(blob, df_teams):
    if not blob: return []
    norm_blob = re.sub(r'[^a-z0-9\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]', '', normalize_text(blob))
    found_teams = []
    for index, row in df_teams.iterrows():
        t_name = row["名前"]
        norm_team = normalize_text(t_name)
        clean_team = re.sub(r'[^a-z0-9\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]', '', norm_team)
        if len(clean_team) < 2: continue
        if norm_blob.find(clean_team) != -1: found_teams.append((norm_blob.find(clean_team), t_name))
        else:
            core_team = re.sub(r"[a-z0-9]", "", clean_team)
            if len(core_team) >= 2 and norm_blob.find(core_team) != -1: found_teams.append((norm_blob.find(core_team), t_name))
    found_teams.sort(key=lambda x: x[0])
    result = []
    for item in found_teams:
        if item[1] not in result: result.append(item[1])
    return result

# ==========================================
# 1. データ読み込み
# ==========================================
TEAM_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=0&single=true&output=csv"
TEMPLATE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=2050053305&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try: return pd.read_csv(url).fillna("")
    except: return pd.DataFrame()

df_teams = load_data(TEAM_SHEET_URL).rename(columns={"チーム名": "名前", "ふりがな": "かな", "Xアカウント": "X", "インスタグラム": "インスタ", "ハッシュタグ": "タグ"})
df_templates = load_data(TEMPLATE_SHEET_URL).rename(columns={"行事名": "イベント名", "Twitter用": "X用", "Instagram用": "インスタ用", "合同用": "合同用"})

if not df_teams.empty:
    df_teams["検索用"] = df_teams["名前"].apply(normalize_text) + df_teams["かな"].apply(normalize_text)

# ==========================================
# 2. UI構築（サイドバー）
# ==========================================
with st.sidebar:
    st.header("⚙️ 投稿設定")
    if not df_templates.empty:
        event_names = df_templates["イベント名"].tolist()
        if "selected_event" not in st.session_state: st.session_state.selected_event = event_names[0]
        target_event = st.selectbox("🎪 イベントを選択", event_names, index=event_names.index(st.session_state.selected_event))
        if "last_loaded_event" not in st.session_state or st.session_state.last_loaded_event != target_event:
            row = df_templates[df_templates["イベント名"] == target_event].iloc[0]
            st.session_state.editing_x = row["X用"]
            st.session_state.editing_i = row["インスタ用"]
            st.session_state.joint_base_text = row["合同用"] if "合同用" in row and row["合同用"] else "現地から速報！🔥\n{teams}\n\n#YOSAKOIソーラン祭り"
            st.session_state.last_loaded_event = target_event
        st.write("📝 ベース文章の微調整")
        st.session_state.editing_x = st.text_area("🐦 X用ベース", st.session_state.editing_x, height=120)
        st.session_state.editing_i = st.text_area("📸 インスタ用ベース", st.session_state.editing_i, height=120)

# ==========================================
# 3. メイン画面
# ==========================================
st.markdown("<p class='custom-title'>🎤 YOSAKOI現地投稿くん</p>", unsafe_allow_html=True)
st.markdown("<p class='custom-subtitle'>SNS POSTING ASSISTANT</p>", unsafe_allow_html=True)

if not df_teams.empty:
    tab1, tab2, tab3 = st.tabs(["🔍 1件ずつ", "🗓 一括生成", "📸 合同ピックアップ"])

    # --- タブ1: 1件ずつ（自動生成＆文字数チェッカー復活！） ---
    with tab1:
        col_search, col_part = st.columns([3, 1])
        with col_search:
            query = st.text_input("チーム名検索", placeholder="ひらぎし、科学大など")
        with col_part:
            part_num = st.text_input("part", value="1", key="single_part")
            
        if query:
            norm_q = normalize_text(query)
            results = df_teams[df_teams["検索用"].str.contains(norm_q, na=False, regex=False)]
            if not results.empty:
                selected = st.selectbox("チーム確定", results["名前"].tolist())
                row = df_teams[df_teams["名前"] == selected].iloc[0]
                
                # 自動生成
                res_x = st.session_state.editing_x.format(名前=row['名前'], X=row['X'], インスタ=row['インスタ'], タグ=row['タグ'], part=part_num)
                res_i = st.session_state.editing_i.format(名前=row['名前'], X=row['X'], インスタ=row['インスタ'], タグ=row['タグ'], part=part_num)
                
                t_x, t_i = st.tabs(["🐦 X (Twitter)", "📸 Instagram"])
                
                with t_x:
                    char_count = len(res_x)
                    if char_count <= 140:
                        st.caption(f"🟢 文字数: {char_count}/140")
                    else:
                        st.error(f"🔴 文字数オーバー！: {char_count}/140")
                    st.code(res_x, language="text")
                    st.link_button("🐦 Xで開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(res_x)}", type="primary", use_container_width=True)
                    
                with t_i:
                    st.code(res_i, language="text")
                    st.link_button("📸 インスタを開く（※上の文章をコピーしてから押してね）", "https://www.instagram.com/", use_container_width=True)

    # --- タブ2: 一括生成（文字数チェッカー復活！） ---
    with tab2:
        bulk_input = st.text_area("テキストを貼り付け", height=150)
        bulk_part = st.text_input("一括用part", value="1", key="bulk_part")
        if st.button("一括生成", type="primary", use_container_width=True):
            matched = extract_teams_from_blob(bulk_input, df_teams)
            for t_name in matched:
                row = df_teams[df_teams["名前"] == t_name].iloc[0]
                f_x = st.session_state.editing_x.format(名前=row['名前'], X=row['X'], インスタ=row['インスタ'], タグ=row['タグ'], part=bulk_part)
                f_i = st.session_state.editing_i.format(名前=row['名前'], X=row['X'], インスタ=row['インスタ'], タグ=row['タグ'], part=bulk_part)
                
                with st.expander(f"✅ {row['名前']}"):
                    st.write("**🐦 X用**")
                    char_count = len(f_x)
                    st.caption(f"{'🟢' if char_count <= 140 else '🔴'} 文字数: {char_count}/140")
                    st.code(f_x, language="text")
                    st.link_button("🐦 X投稿", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(f_x)}", type="primary")
                    st.write("---")
                    st.write("**📸 インスタ用**")
                    st.code(f_i, language="text")

    # --- タブ3: 合同ピックアップ（文字数チェッカー復活！） ---
    with tab3:
        joint_input = st.text_area("タイムテーブルを貼り付け", height=120)
        if st.button("🔍 チームを抽出する", type="primary", use_container_width=True):
            st.session_state.joint_extracted_teams = extract_teams_from_blob(joint_input, df_teams)
            
        if "joint_extracted_teams" in st.session_state and st.session_state.joint_extracted_teams:
            matched_teams = st.session_state.joint_extracted_teams
            if "selected_joint_teams" not in st.session_state: st.session_state.selected_joint_teams = []
            
            cols = st.columns(2)
            for i, t_name in enumerate(matched_teams):
                with cols[i % 2]:
                    is_sel = t_name in st.session_state.selected_joint_teams
                    if st.button(f"{'✅' if is_sel else '⬜'} {t_name}", key=f"btn_joint_{t_name}", use_container_width=True):
                        if is_sel: st.session_state.selected_joint_teams.remove(t_name)
                        elif len(st.session_state.selected_joint_teams) < 4: st.session_state.selected_joint_teams.append(t_name)
                        st.rerun()
            
            if st.session_state.selected_joint_teams:
                teams_text = "\n".join([f"🎤 {t}" for t in st.session_state.selected_joint_teams])
                final_text = st.session_state.joint_base_text.replace("{teams}", teams_text)
                final_text = st.text_area("✍️ 最終確認", value=final_text, height=200)
                
                char_count = len(final_text)
                if char_count <= 140:
                    st.caption(f"🟢 文字数: {char_count}/140")
                else:
                    st.error(f"🔴 文字数オーバー！: {char_count}/140")
                    
                st.link_button("🐦 Xを開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(final_text)}", type="primary", use_container_width=True)

else:
    st.info("データを読み込み中です...")
