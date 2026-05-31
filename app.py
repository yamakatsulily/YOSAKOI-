import streamlit as st
import pandas as pd
import urllib.parse
import re
import unicodedata # ★全角半角の統一用

st.set_page_config(page_title="YOSAKOI現地投稿くん", layout="centered", initial_sidebar_state="expanded")

# ==========================================
# 🎨 スマホアプリ風デザイン（CSS）
# ==========================================
st.markdown("""
<style>
    .block-container {
        padding-top: 4.5rem;
        padding-bottom: 2rem;
    }
    div.stButton > button {
        border-radius: 8px;
        font-weight: bold;
    }
    .custom-title {
        text-align: center;
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 0px;
        color: #333;
        line-height: 1.2;
    }
    .custom-subtitle {
        text-align: center;
        font-size: 0.8rem;
        color: #666;
        margin-top: 0px;
        margin-bottom: 20px;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 0. 文字のお掃除＆超強力スキャナー関数
# ==========================================
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = text.lower()
    text = text.replace("櫻", "桜").replace("樂", "楽").replace("眞", "真").replace("邊", "辺").replace("澤", "沢").replace("濱", "浜")
    text = re.sub(r"[\s　\"”'’「」『』【】＆&()（）\-ー・!！〜~～_＿=＝—]", "", text)
    return text

def extract_teams_from_blob(blob, df_teams):
    if not blob: return []
    norm_blob = normalize_text(blob)
    found_teams = []
    
    for index, row in df_teams.iterrows():
        t_name = row["名前"]
        norm_team = normalize_text(t_name)
        
        if not norm_team: continue
            
        start = 0
        found_any = False
        while True:
            pos = norm_blob.find(norm_team, start)
            if pos == -1: break
            found_teams.append((pos, t_name))
            start = pos + len(norm_team)
            found_any = True
            
        if not found_any:
            core_team = re.sub(r"[a-z0-9]", "", norm_team)
            if len(core_team) >= 2 and core_team != norm_team:
                start = 0
                while True:
                    pos = norm_blob.find(core_team, start)
                    if pos == -1: break
                    found_teams.append((pos, t_name))
                    start = pos + len(core_team)
                    
    found_teams.sort(key=lambda x: x[0])
    
    result = []
    for item in found_teams:
        if item[1] not in result:
            result.append(item[1])
            
    return result

# ==========================================
# 1. URL設定
# ==========================================
TEAM_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=0&single=true&output=csv"
TEMPLATE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=2050053305&single=true&output=csv"

# ==========================================
# 2. データ読み込み
# ==========================================
@st.cache_data(ttl=60)
def load_data(url):
    try:
        return pd.read_csv(url).fillna("")
    except:
        return pd.DataFrame()

df_teams = load_data(TEAM_SHEET_URL).rename(columns={"チーム名": "名前", "ふりがな": "かな", "Xアカウント": "X", "インスタグラム": "インスタ", "ハッシュタグ": "タグ"})
df_templates = load_data(TEMPLATE_SHEET_URL).rename(columns={"行事名": "イベント名", "Twitter用": "X用", "Instagram用": "インスタ用", "合同用": "合同用"})

if not df_teams.empty:
    df_teams["検索用"] = df_teams["名前"].apply(normalize_text) + df_teams["かな"].apply(normalize_text)

# ==========================================
# 3. サイドバー（設定エリア）
# ==========================================
with st.sidebar:
    st.header("⚙️ 投稿設定")
    
    if not df_templates.empty:
        event_names = df_templates["イベント名"].tolist()
        if "selected_event" not in st.session_state:
            st.session_state.selected_event = event_names[0]
        
        target_event = st.selectbox("🎪 イベントを選択", event_names, index=event_names.index(st.session_state.selected_event))

        if "last_loaded_event" not in st.session_state or st.session_state.last_loaded_event != target_event:
            row = df_templates[df_templates["イベント名"] == target_event].iloc[0]
            st.session_state.editing_x = row["X用"]
            st.session_state.editing_i = row["インスタ用"]
            
            if "合同用" in row and row["合同用"]:
                st.session_state.joint_base_text = row["合同用"]
            else:
                st.session_state.joint_base_text = "現地から速報！🔥\n{teams}\n\n#YOSAKOIソーラン祭り"
                
            st.session_state.last_loaded_event = target_event
            st.session_state.selected_event = target_event

        st.write("📝 ベース文章の微調整")
        st.session_state.editing_x = st.text_area("🐦 X用ベース", st.session_state.editing_x, height=150)
        st.session_state.editing_i = st.text_area("📸 インスタ用ベース", st.session_state.editing_i, height=150)
        
        if st.button("🔄 シートの文章にリセット", use_container_width=True):
            del st.session_state.last_loaded_event
            st.rerun()
    else:
        st.error("テンプレートが読み込めません。")
        
    st.divider()
    if st.button("🔄 最新のチーム名簿を読み込む", use_container_width=True):
        st.cache_data.clear()
        st.success("最新情報を読み込みました！")
        st.rerun()

# ==========================================
# 4. メイン画面
# ==========================================
st.markdown("<p class='custom-title'>🎤 YOSAKOI現地投稿くん</p>", unsafe_allow_html=True)
st.markdown("<p class='custom-subtitle'>SNS POSTING ASSISTANT</p>", unsafe_allow_html=True)

if not df_teams.empty:
    tab1, tab2, tab3 = st.tabs(["🔍 1件ずつ", "🗓 一括生成", "📸 合同ピックアップ"])

    # -----------------------------
    # タブ1: 1件ずつ検索
    # -----------------------------
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
                x_id = row['X'] if row['X'] not in ["(確認できず)", "nan", ""] else ""
                insta_id = row['インスタ'] if row['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                try:
                    res_x = st.session_state.editing_x.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'], part=part_num)
                    res_i = st.session_state.editing_i.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'], part=part_num)
                    st.success(f"【{selected}】を生成しました")
                    t_x, t_i = st.tabs(["🐦 X", "📸 インスタ"])
                    with t_x:
                        st.code(res_x, language="text")
                        st.link_button("🐦 Xで開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(res_x)}", type="primary", use_container_width=True)
                    with t_i:
                        st.code(res_i, language="text")
                except: st.error("テンプレートを確認してください")
            else: st.warning("見つかりません")

    # -----------------------------
    # タブ2: 一括生成（超強力スキャナー版）
    # -----------------------------
    with tab2:
        st.info("💡 タイムテーブルをそのまま貼り付けても、チーム名だけを自動で抜き出します！")
        bulk_input = st.text_area("テキストを貼り付け", height=150, key="bulk_input_tab2")
        bulk_part = st.text_input("一括用part", value="1", key="bulk_part")
        
        if st.button("一括生成", type="primary", use_container_width=True):
            matched_teams = extract_teams_from_blob(bulk_input, df_teams)
            
            if matched_teams:
                st.success(f"✅ {len(matched_teams)}チームを抽出しました！")
                for t_name in matched_teams:
                    row = df_teams[df_teams["名前"] == t_name].iloc[0]
                    x_r = row['X'] if row['X'] not in ["(確認できず)", "nan", ""] else ""
                    i_r = row['インスタ'] if row['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                    try:
                        f_x = st.session_state.editing_x.format(名前=row['名前'], X=x_r, インスタ=i_r, タグ=row['タグ'], part=bulk_part)
                        f_i = st.session_state.editing_i.format(名前=row['名前'], X=x_r, インスタ=i_r, タグ=row['タグ'], part=bulk_part)
                        with st.expander(f"✅ {row['名前']}"):
                            st.code(f_x, language="text")
                            st.link_button("🐦 X投稿", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(f_x)}", type="primary")
                    except Exception as e:
                        st.error(f"⚠️ {row['名前']}の生成エラー")
            else:
                if bulk_input:
                    st.error("❌ テキストの中に、名簿に登録されているチーム名が見つかりませんでした。")

    # -----------------------------
    # タブ3: 合同ピックアップ（ボタン完備＆超強力スキャナー版）
    # -----------------------------
    with tab3:
        st.info("💡 スケジュールから4チームを選んで合同投稿を作成！")
        
        with st.expander("⚙️ 合同投稿のベース文章を一時編集"):
            st.session_state.joint_base_text = st.text_area("合同用ベース文章", st.session_state.joint_base_text, height=130)
            st.caption("※スプレッドシートから読み込んだ文章が初期値になっています")
        
        joint_input = st.text_area("タイムテーブルを貼り付け", height=120, key="joint_input_tab3")
        
        # 🌟 ここに「抽出する」ボタンを新設し、スマホの入力問題を完全解決！
        if st.button("🔍 チームを抽出する", type="primary", use_container_width=True, key="btn_extract_tab3"):
            if joint_input:
                extracted = extract_teams_from_blob(joint_input, df_teams)
                if extracted:
                    st.session_state.joint_extracted_teams = extracted
                    st.session_state.selected_joint_teams = [] # 新しく抽出した時は選択をリセット
                else:
                    st.error("❌ テキストの中にチーム名が見つかりませんでした。")
                    st.session_state.joint_extracted_teams = []
            else:
                st.warning("⚠️ タイムテーブルを貼り付けてからボタンを押してください。")
        
        # 抽出成功したチームが記憶されていれば、ボタンを表示
        if "joint_extracted_teams" in st.session_state and st.session_state.joint_extracted_teams:
            matched_teams = st.session_state.joint_extracted_teams
            st.write("👇 写真を載せるチームを選択（最大4つ）")
            
            if "selected_joint_teams" not in st.session_state:
                st.session_state.selected_joint_teams = []
            
            cols = st.columns(2)
            for i, t_name in enumerate(matched_teams):
                with cols[i % 2]:
                    is_selected = t_name in st.session_state.selected_joint_teams
                    btn_label = f"✅ {t_name}" if is_selected else f"⬜ {t_name}"
                    
                    if st.button(btn_label, key=f"btn_joint_{t_name}", use_container_width=True):
                        if is_selected:
                            st.session_state.selected_joint_teams.remove(t_name)
                            st.rerun()
                        elif len(st.session_state.selected_joint_teams) < 4:
                            st.session_state.selected_joint_teams.append(t_name)
                            st.rerun()
            
            if st.session_state.selected_joint_teams:
                team_texts = []
                for t_name in st.session_state.selected_joint_teams:
                    row = df_teams[df_teams["名前"] == t_name].iloc[0]
                    x_id = row['X'] if row['X'] not in ["(確認できず)", "nan", ""] else ""
                    team_texts.append(f"🎤 {t_name} {x_id}".strip())
                
                teams_joined = "\n".join(team_texts)
                final_joint_text = st.session_state.joint_base_text.replace("{teams}", teams_joined)
                
                st.success(f"✅ {len(st.session_state.selected_joint_teams)}チーム選択中！")
                final_joint_text_edited = st.text_area("✍️ 最終確認", value=final_joint_text, height=200, key="final_joint_edited")
                
                char_count = len(final_joint_text_edited)
                st.caption(f"{'🟢' if char_count <= 140 else '🔴'} 文字数: {char_count}/140")
                
                st.link_button("🐦 この内容でXを開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(final_joint_text_edited)}", type="primary", use_container_width=True)

else:
    st.info("データを読み込み中です...")
