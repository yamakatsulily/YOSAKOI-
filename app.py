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
# 0. 共通関数（超・前方一致スキャナー）
# ==========================================
def normalize_text(text):
    if not isinstance(text, str): return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = unicodedata.normalize('NFKC', text).lower()
    return text.replace("櫻", "桜").replace("樂", "楽").replace("眞", "真").replace("邊", "辺").replace("澤", "沢").replace("濱", "浜")

def extract_teams_from_blob(blob, df_teams):
    if not blob: return []
    found_teams = []
    
    # --- 事前準備：全チームの検索候補（前方一致用）を作成 ---
    team_search_data = []
    
    # 汎用ワードを削る関数（例：「よさこいチーム倭奏」→「倭奏」）
    def strip_generic(text):
        prefixes = ['よさこい', 'ヨサコイ', 'yosakoi', 'そーらん', 'ソーラン', 'ちーむ', 'チーム', 'だんす', 'ダンス', 'ぷろじぇくと', 'プロジェクト', 'ごうどう', '合同', 'がくせい', '学生']
        res = text
        for _ in range(3):
            for p in prefixes:
                if res.startswith(p): res = res[len(p):]
                if res.endswith(p): res = res[:-len(p)]
        return res

    for index, row in df_teams.iterrows():
        t_name = row["名前"]
        name = normalize_text(t_name)
        
        # 記号で分割
        parts = re.split(r'[\s ・（）()\[\]〜～\-－&＆_＿]', name)
        clean_parts = [re.sub(r'[^a-z0-9\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]', '', p) for p in parts]
        clean_parts = [p for p in clean_parts if p]
        
        candidates = set()
        
        # 1. 全部繋げたもの
        full_clean = "".join(clean_parts)
        if len(full_clean) >= 2: candidates.add(full_clean)
        
        # 2. 英数字抜き（漢字・ひらがな等のみ）
        core = re.sub(r'[a-z0-9]', '', full_clean)
        if len(core) >= 2: candidates.add(core)
            
        # 3. 「よさこい」等の汎用ワードを削ったもの
        stripped_full = strip_generic(full_clean)
        if len(stripped_full) >= 2: candidates.add(stripped_full)
        
        stripped_core = strip_generic(core)
        if len(stripped_core) >= 2: candidates.add(stripped_core)
            
        # 4. 記号等で分割された各パーツ
        for p in clean_parts:
            sp = strip_generic(p)
            if len(sp) >= 2: candidates.add(sp)
            elif len(p) >= 2: candidates.add(p)
                
        # --- 🌟ここが本命！前方一致（Prefix）の生成 ---
        prefix_candidates = set()
        for cand in candidates:
            prefix_candidates.add(cand)
            # 長い名前なら、途中で切れていてもマッチするように前方一致候補を作る
            if len(cand) >= 5:
                for i in range(len(cand)-1, 3, -1): # 4文字まで許容
                    prefix_candidates.add(cand[:i])
            elif len(cand) == 4:
                prefix_candidates.add(cand[:3]) # 4文字のチームは3文字まで許容
                
        # 誤爆防止のため、短すぎる一般的な単語は除外
        ignore_words = {"だいがく", "大学", "学園", "がくえん", "北海道", "札幌", "さっぽろ", "高校", "中学", "ジュニア", "キッズ", "チーム", "ちーむ"}
        prefix_candidates = {c for c in prefix_candidates if c not in ignore_words}
        
        for cand in prefix_candidates:
            team_search_data.append((t_name, cand, len(cand)))

    # --- タイムテーブルの解析 ---
    lines = blob.split('\n')
    for line in lines:
        norm_line = normalize_text(line)
        norm_line = re.sub(r'[^a-z0-9\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]', '', norm_line)
        if not norm_line: continue
        
        line_teams = []
        # その行に対して全候補をぶつける
        for t_name, cand, cand_len in team_search_data:
            pos = norm_line.find(cand)
            if pos != -1:
                line_teams.append((pos, t_name, cand_len))
                
        # 同じ位置で見つかった場合、①文字数が長いマッチ ②元のチーム名が短い（完全一致） を優先
        line_teams.sort(key=lambda x: (x[0], -x[2], len(x[1])))
        
        filtered_line_teams = []
        for item in line_teams:
            overlap = False
            for existing in filtered_line_teams:
                # すでに抽出されたチーム名と完全に同じ場合はスキップ
                if item[1] == existing[1]:
                    overlap = True
                    break
                # 見つかった文字列の範囲が被っている場合は、より長くマッチしたものを優先
                e_start, e_end = existing[0], existing[0] + existing[2]
                i_start, i_end = item[0], item[0] + item[2]
                if max(e_start, i_start) < min(e_end, i_end):
                    overlap = True
                    break
            if not overlap:
                filtered_line_teams.append(item)
                
        # 見つかった順番でリストに追加
        for item in filtered_line_teams:
            if item[1] not in found_teams:
                found_teams.append(item[1])
                
    return found_teams

def get_x_char_count(text):
    count = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('F', 'W', 'A'):
            count += 2
        else:
            count += 1
    return math.ceil(count / 2)

def clean_social_id(text):
    text = str(text).strip()
    if not text or text.lower() == "nan" or "確認" in text or "不明" in text:
        return ""
    return text

def format_hashtags(tag_text):
    text = str(tag_text).strip()
    if not text or text.lower() == "nan": return ""
    tags = re.split(r'[\s ]+', text)
    return "\n".join([t for t in tags if t])

def update_url():
    st.query_params["date"] = st.session_state.input_date
    st.query_params["venue"] = st.session_state.input_venue

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
            st.session_state.joint_base_text = row["合同用"] if "合同用" in row.index and row["合同用"] else "🗓️{日付}\n🎪{会場} より速報！🔥\n\n{teams}\n\n#{イベント名}"
            
            def_date = str(row["日付"]) if "日付" in row.index else ""
            def_venue = str(row["会場"]) if "会場" in row.index else ""
            st.session_state.input_date = st.query_params.get("date", def_date)
            st.session_state.input_venue = st.query_params.get("venue", def_venue)
            
            st.session_state.last_loaded_event = target_event

        st.write("📅 撮影データ情報")
        st.text_input("🗓 演舞日", key="input_date", on_change=update_url)
        st.text_input("🎪 会場", key="input_venue", on_change=update_url)
        
        st.query_params["date"] = st.session_state.input_date
        st.query_params["venue"] = st.session_state.input_venue
        st.divider()

        st.write("📝 ベース文章の微調整")
        st.caption("※ここは再読み込みで消えるので、ベース文の大幅な変更はスプレッドシートで行ってください")
        st.session_state.editing_x = st.text_area("🐦 X用ベース", st.session_state.editing_x, height=120)
        st.session_state.editing_i = st.text_area("📸 インスタ用ベース", st.session_state.editing_i, height=120)
        st.session_state.joint_base_text = st.text_area("🔥 速報(合同)用ベース", st.session_state.joint_base_text, height=120)

# ==========================================
# 3. メイン画面
# ==========================================
st.markdown("<p class='custom-title'>🎤 YOSAKOI現地投稿くん</p>", unsafe_allow_html=True)
st.markdown("<p class='custom-subtitle'>SNS POSTING ASSISTANT</p>", unsafe_allow_html=True)

if not df_teams.empty:
    tab1, tab2, tab3 = st.tabs(["🔍 1件ずつ", "🗓 一括生成", "📸 合同ピックアップ"])

    # --- タブ1: 1件ずつ ---
    with tab1:
        col_search, col_part = st.columns([3, 1])
        with col_search:
            query = st.text_input("チーム名検索", placeholder="ひらぎし、科学大など")
        with col_part:
            def update_part():
                st.query_params["part"] = st.session_state.single_part
            part_num = st.text_input("part", value=st.query_params.get("part", "1"), key="single_part", on_change=update_part)
            
        if query:
            norm_q = normalize_text(query)
            results = df_teams[df_teams["検索用"].str.contains(norm_q, na=False, regex=False)]
            if not results.empty:
                selected = st.selectbox("チーム確定", results["名前"].tolist())
                row = df_teams[df_teams["名前"] == selected].iloc[0]
                
                try:
                    row_x = clean_social_id(row['X'])
                    row_i = clean_social_id(row['インスタ'])
                    row_tags = format_hashtags(row['タグ'])
                    
                    res_x = st.session_state.editing_x.format(名前=row['名前'], X=row_x, インスタ=row_i, タグ=row_tags, part=part_num, 日付=st.session_state.input_date, 会場=st.session_state.input_venue, イベント名=target_event)
                    res_i = st.session_state.editing_i.format(名前=row['名前'], X=row_x, インスタ=row_i, タグ=row_tags, part=part_num, 日付=st.session_state.input_date, 会場=st.session_state.input_venue, イベント名=target_event)
                    
                    t_x, t_i = st.tabs(["🐦 X (Twitter)", "📸 Instagram"])
                    
                    with t_x:
                        char_count = get_x_char_count(res_x)
                        st.caption(f"{'🟢' if char_count <= 140 else '🔴'} 文字数: {char_count}/140")
                        st.code(res_x, language="text")
                        st.link_button("🐦 Xで開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(res_x)}", type="primary", use_container_width=True)
                        
                    with t_i:
                        st.code(res_i, language="text")
                        st.link_button("📸 インスタを開く（※コピーしてから押してね）", "https://www.instagram.com/", use_container_width=True)
                except KeyError as e:
                    st.error(f"⚠️ テンプレートエラー: 登録されていない {e} が含まれています。")

    # --- タブ2: 一括生成 ---
    with tab2:
        bulk_input = st.text_area("テキストを貼り付け", height=150)
        bulk_part = st.text_input("一括用part", value="1", key="bulk_part")
        if st.button("一括生成", type="primary", use_container_width=True):
            matched = extract_teams_from_blob(bulk_input, df_teams)
            for t_name in matched:
                row = df_teams[df_teams["名前"] == t_name].iloc[0]
                try:
                    row_x = clean_social_id(row['X'])
                    row_i = clean_social_id(row['インスタ'])
                    row_tags = format_hashtags(row['タグ'])
                    
                    f_x = st.session_state.editing_x.format(名前=row['名前'], X=row_x, インスタ=row_i, タグ=row_tags, part=bulk_part, 日付=st.session_state.input_date, 会場=st.session_state.input_venue, イベント名=target_event)
                    f_i = st.session_state.editing_i.format(名前=row['名前'], X=row_x, インスタ=row_i, タグ=row_tags, part=bulk_part, 日付=st.session_state.input_date, 会場=st.session_state.input_venue, イベント名=target_event)
                    
                    with st.expander(f"✅ {row['名前']}"):
                        st.write("**🐦 X用**")
                        char_count = get_x_char_count(f_x)
                        st.caption(f"{'🟢' if char_count <= 140 else '🔴'} 文字数: {char_count}/140")
                        st.code(f_x, language="text")
                        st.link_button("🐦 X投稿", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(f_x)}", type="primary")
                        st.write("---")
                        st.write("**📸 インスタ用**")
                        st.code(f_i, language="text")
                except Exception as e:
                    st.error(f"⚠️ {row['名前']}の生成エラー")

    # --- タブ3: 合同ピックアップ ---
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
                team_texts = []
                for t_name in matched_teams:
                    if t_name in st.session_state.selected_joint_teams:
                        row = df_teams[df_teams["名前"] == t_name].iloc[0]
                        x_id = clean_social_id(row['X'])
                        team_texts.append(f"🎤 {t_name} さん {x_id}".strip())
                    
                teams_text = "\n".join(team_texts)
                final_text = st.session_state.joint_base_text.replace("{teams}", teams_text).replace("{日付}", st.session_state.input_date).replace("{会場}", st.session_state.input_venue).replace("{イベント名}", target_event)
                final_text = st.text_area("✍️ 最終確認", value=final_text, height=200)
                
                char_count = get_x_char_count(final_text)
                st.caption(f"{'🟢' if char_count <= 140 else '🔴'} 文字数: {char_count}/140")
                    
                st.link_button("🐦 Xを開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(final_text)}", type="primary", use_container_width=True)

else:
    st.info("データを読み込み中です...")
