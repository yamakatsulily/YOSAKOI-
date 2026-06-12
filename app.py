import streamlit as st
import pandas as pd
import urllib.parse
import re
import unicodedata
import math

st.set_page_config(page_title="YOSAKOI現地投稿くん", layout="centered", initial_sidebar_state="expanded")

# ==========================================
# 共通関数：ゆるいマッチング（とりあえず拾う！）
# ==========================================
def normalize_text(text):
    if not isinstance(text, str): return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return unicodedata.normalize('NFKC', text).lower()

def extract_teams_loose(blob, df_teams):
    if not blob: return []
    found_teams = set()
    norm_blob = normalize_text(blob)
    
    for index, row in df_teams.iterrows():
        t_name = row["名前"]
        # チーム名の最初の2文字以上がタイムテーブルにあれば拾う（ゆるい）
        target = normalize_text(t_name)[:4] # 4文字くらいで判定
        if len(target) >= 2 and target in norm_blob:
            found_teams.add(t_name)
    return list(found_teams)

def get_x_char_count(text):
    count = 0
    for char in text:
        count += 2 if unicodedata.east_asian_width(char) in ('F', 'W', 'A') else 1
    return math.ceil(count / 2)

def clean_social_id(text):
    text = str(text).strip()
    if not text or text.lower() == "nan" or "確認" in text or "不明" in text: return ""
    return text

def format_hashtags(tag_text):
    text = str(tag_text).strip()
    if not text or text.lower() == "nan": return ""
    return "\n".join([t for t in re.split(r'[\s ]+', text) if t])

def update_url():
    st.query_params["date"] = st.session_state.input_date
    st.query_params["venue"] = st.session_state.input_venue

# ==========================================
# データ読み込み・UI構築
# ==========================================
TEAM_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=0&single=true&output=csv"
TEMPLATE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=2050053305&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data(url):
    try: return pd.read_csv(url).fillna("")
    except: return pd.DataFrame()

df_teams = load_data(TEAM_SHEET_URL).rename(columns={"チーム名": "名前", "ふりがな": "かな", "Xアカウント": "X", "インスタグラム": "インスタ", "ハッシュタグ": "タグ"})
df_templates = load_data(TEMPLATE_SHEET_URL).rename(columns={"行事名": "イベント名", "Twitter用": "X用", "Instagram用": "インスタ用", "合同用": "合同用"})

# サイドバー設定は省略（これまでと同じです）
with st.sidebar:
    st.header("⚙️ 投稿設定")
    if not df_templates.empty:
        event_names = df_templates["イベント名"].tolist()
        if "selected_event" not in st.session_state: st.session_state.selected_event = event_names[0]
        target_event = st.selectbox("🎪 イベントを選択", event_names, index=event_names.index(st.session_state.selected_event))
        row = df_templates[df_templates["イベント名"] == target_event].iloc[0]
        st.session_state.editing_x = row["X用"]
        st.session_state.joint_base_text = row["合同用"] if "合同用" in row.index and row["合同用"] else "🗓️{日付}\n🎪{会場} 速報！\n\n{teams}\n\n#{イベント名}"
        st.text_input("🗓 演舞日", key="input_date", on_change=update_url)
        st.text_input("🎪 会場", key="input_venue", on_change=update_url)
        st.session_state.editing_x = st.text_area("🐦 X用ベース", st.session_state.editing_x, height=100)
        st.session_state.joint_base_text = st.text_area("🔥 速報用ベース", st.session_state.joint_base_text, height=100)

st.title("🎤 YOSAKOI現地投稿くん")

tab1, tab2, tab3 = st.tabs(["🔍 1件ずつ", "🗓 一括生成", "📸 合同ピックアップ"])

with tab3:
    joint_input = st.text_area("タイムテーブルを貼り付け", height=150)
    if st.button("全件候補をリストアップ"):
        st.session_state.all_candidates = extract_teams_loose(joint_input, df_teams)
        st.session_state.selected_teams = st.session_state.all_candidates.copy()

    if "all_candidates" in st.session_state:
        st.write("### ✅ 投稿するチームを選んでください")
        selected = []
        for t_name in st.session_state.all_candidates:
            if st.checkbox(t_name, value=(t_name in st.session_state.selected_teams)):
                selected.append(t_name)
        
        if selected:
            team_texts = [f"🎤 {t} さん {clean_social_id(df_teams[df_teams['名前']==t].iloc[0]['X'])}" for t in selected]
            final_text = st.session_state.joint_base_text.replace("{teams}", "\n".join(team_texts)).replace("{日付}", st.session_state.input_date).replace("{会場}", st.session_state.input_venue).replace("{イベント名}", target_event)
            st.text_area("✍️ 最終確認", value=final_text, height=200)
            st.link_button("🐦 Xで開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(final_text)}", type="primary")
