import streamlit as st
import pandas as pd
import urllib.parse
import re
import unicodedata
import math

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
# 共通関数：強力な検索ロジック
# ==========================================
def normalize_text(text):
    if not isinstance(text, str): return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return unicodedata.normalize('NFKC', text).lower()

def extract_teams_from_blob(blob, df_teams):
    if not blob: return []
    # タイムテーブルの各行から、チーム名を強引にでも見つける
    found_teams = []
    lines = blob.split('\n')
    for line in lines:
        norm_line = normalize_text(line)
        norm_line = re.sub(r'[^a-z0-9\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]', '', norm_line)
        for _, row in df_teams.iterrows():
            t_name = row["名前"]
            target = normalize_text(t_name)
            target_clean = re.sub(r'[^a-z0-9\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]', '', target)
            
            # 2文字以上で前方一致すれば拾う
            if len(target_clean) >= 2 and target_clean in norm_line:
                if t_name not in found_teams:
                    found_teams.append(t_name)
    return found_teams

def get_x_char_count(text):
    count = 0
    for char in text:
        count += 2 if unicodedata.east_asian_width(char) in ('F', 'W', 'A') else 1
    return math.ceil(count / 2)

def clean_social_id(text):
    text = str(text).strip()
    if not text or text.lower() == "nan" or "確認" in text or "不明" in text: return ""
    return text

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

# ==========================================
# 2. UI
# ==========================================
st.markdown("<p class='custom-title'>🎤 YOSAKOI現地投稿くん</p>", unsafe_allow_html=True)
st.markdown("<p class='custom-subtitle'>SNS POSTING ASSISTANT</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 投稿設定")
    if not df_templates.empty:
        event_names = df_templates["イベント名"].tolist()
        target_event = st.selectbox("🎪 イベントを選択", event_names)
        row = df_templates[df_templates["イベント名"] == target_event].iloc[0]
        
        st.session_state.editing_x = row["X用"]
        st.session_state.joint_base_text = row["合同用"] if "合同用" in row.index and row["合同用"] else "🗓️{日付}\n🎪{会場} 速報！\n\n{teams}\n\n#{イベント名}"
        
        target_date = st.text_input("🗓 演舞日", value=row.get("日付", ""))
        target_venue = st.text_input("🎪 会場", value=row.get("会場", ""))

tab1, tab2, tab3 = st.tabs(["🔍 1件ずつ", "🗓 一括生成", "📸 合同ピックアップ"])

with tab3:
    joint_input = st.text_area("タイムテーブルを貼り付け", height=120)
    if st.button("🔍 チームを抽出"):
        st.session_state.joint_extracted_teams = extract_teams_from_blob(joint_input, df_teams)
        st.session_state.selected_joint_teams = []

    if "joint_extracted_teams" in st.session_state:
        matched = st.session_state.joint_extracted_teams
        cols = st.columns(2)
        for i, t in enumerate(matched):
            with cols[i % 2]:
                if st.button(t, key=f"btn_{t}"):
                    if t not in st.session_state.selected_joint_teams:
                        st.session_state.selected_joint_teams.append(t)
        
        st.write("---")
        st.write("### 選んだチーム")
        for t in st.session_state.selected_joint_teams:
            if st.button(f"❌ {t}"):
                st.session_state.selected_joint_teams.remove(t)
                st.rerun()
        
        if st.session_state.selected_joint_teams:
            team_texts = [f"🎤 {t} さん {clean_social_id(df_teams[df_teams['名前']==t].iloc[0]['X'])}" for t in st.session_state.selected_joint_teams]
            final_text = st.session_state.joint_base_text.replace("{teams}", "\n".join(team_texts)).replace("{日付}", target_date).replace("{会場}", target_venue).replace("{イベント名}", target_event)
            final_text = st.text_area("✍️ 最終確認", value=final_text, height=200)
            st.link_button("🐦 Xで開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(final_text)}", type="primary", use_container_width=True)
