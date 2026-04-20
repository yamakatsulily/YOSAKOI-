import streamlit as st
import pandas as pd
import urllib.parse
import re  # ★文字のお掃除用に新しく追加

st.set_page_config(page_title="YOSAKOI現地投稿くん", layout="centered", initial_sidebar_state="expanded")

# ==========================================
# 0. 検索を最強にする「文字のお掃除」関数
# ==========================================
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    # 大文字小文字を揃える
    text = text.lower()
    # 空白(全角半角)、引用符、カッコ類、記号を裏側ですべて消し去る
    text = re.sub(r'[\s　"”\''’「」『』【】＆&()（）\-ー・!！〜~]', '', text)
    return text

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
df_templates = load_data(TEMPLATE_SHEET_URL).rename(columns={"行事名": "イベント名", "Twitter用": "X用", "Instagram用": "インスタ用"})

# ★ 検索用の「お掃除済みテキスト」列を作っておく
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
            st.session_state.last_loaded_event = target_event
            st.session_state.selected_event = target_event

        st.write("📝 ベース文章の微調整")
        st.session_state.editing_x = st.text_area("🐦 X用ベース", st.session_state.editing_x, height=150)
        st.session_state.editing_i = st.text_area("📸 インスタ用ベース", st.session_state.editing_i, height=150)
        st.caption("※ {名前} {X} {インスタ} {タグ} {part} が自動置換されます")
        
        if st.button("🔄 シートの文章にリセット"):
            del st.session_state.last_loaded_event
            st.rerun()
    else:
        st.error("テンプレートが読み込めません。")
        
    st.divider()
    if st.button("🔄 最新のチーム名簿を読み込む"):
        st.cache_data.clear()
        st.success("最新情報を読み込みました！")
        st.rerun()

# ==========================================
# 4. メイン画面
# ==========================================
st.title("🎤 YOSAKOI現地投稿くん")

if not df_teams.empty:
    tab1, tab2 = st.tabs(["🔍 1件ずつ検索", "🗓 スケジュール一括生成"])

    with tab1:
        col_search, col_part = st.columns([3, 1])
        with col_search:
            query = st.text_input("チーム名検索", placeholder="ひらぎし、科学大など")
        with col_part:
            part_num = st.text_input("part", value="1", key="single_part")

        if query:
            # 入力された文字もお掃除してから検索する
            norm_q = normalize_text(query)
            # regex=False で安全に完全一致・部分一致を探す
            results = df_teams[df_teams["検索用"].str.contains(norm_q, na=False, regex=False)]
            
            if not results.empty:
                selected = st.selectbox("チーム確定", results["名前"].tolist())
                row = df_teams[df_teams["名前"] == selected].iloc[0]
                
                x_id = row['X'] if row['X'] not in ["(確認できず)", "nan", ""] else ""
                insta_id = row['インスタ'] if row['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                
                res_x = st.session_state.editing_x.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'], part=part_num)
                res_i = st.session_state.editing_i.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'], part=part_num)

                st.success(f"【{selected}】の文章を生成しました！")
                t_x, t_i = st.tabs(["🐦 X (Twitter)", "📸 Instagram"])
                
                with t_x:
                    char_count = len(res_x)
                    if char_count <= 140:
                        st.caption(f"🟢 文字数: {char_count}/140")
                    else:
                        st.error(f"🔴 文字数オーバー！: {char_count}/140")
                    st.code(res_x, language="text")
                    st.link_button("🐦 この内容でXを開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(res_x)}", type="primary", use_container_width=True)
                    
                with t_i:
                    st.code(res_i, language="text")
            else:
                st.warning("見つかりません。")

    with tab2:
        bulk_input = st.text_area("チーム名リスト（一行ずつ）", height=200)
        bulk_part = st.text_input("一括用part", value="1", key="bulk_part")
        
        if st.button("投稿文をまとめて作る"):
            lines = bulk_input.split("\n")
            output_data = []
            unmatched = []
            count = 0
            for line in lines:
                name = line.strip()
                if not name: continue
                
                # スケジュールの文字もお掃除して照らし合わせる
                norm_name = normalize_text(name)
                match = df_teams[df_teams["検索用"].str.contains(norm_name, na=False, regex=False)]
                
                if not match.empty:
                    count += 1
                    r = match.iloc[0]
                    x_r = r['X'] if r['X'] not in ["(確認できず)", "nan", ""] else ""
                    i_r = r['インスタ'] if r['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                    
                    final_x = st.session_state.editing_x.format(名前=r['名前'], X=x_r, インスタ=i_r, タグ=r['タグ'], part=bulk_part)
                    final_i = st.session_state.editing_i.format(名前=r['名前'], X=x_r, インスタ=i_r, タグ=r['タグ'], part=bulk_part)
                    
                    output_data.append({"チーム": r['名前'], "X文章": final_x, "インスタ文章": final_i})
                    
                    with st.expander(f"✅ {r['名前']}"):
                        st.write("**🐦 X用**")
                        char_count = len(final_x)
                        if char_count <= 140:
                            st.caption(f"🟢 {char_count}/140文字")
                        else:
                            st.error(f"🔴 {char_count}/140文字（オーバー）")
                        st.code(final_x, language="text")
                        st.link_button("🐦 この内容でXを開く", f"https://twitter.com/intent/tweet?text={urllib.parse.quote(final_x)}", type="primary")
                        st.write("---")
                        st.write("**📸 インスタ用**")
                        st.code(final_i, language="text")
                else:
                    unmatched.append(name)
            
            if unmatched:
                st.error(f"❌ 未登録：{', '.join(unmatched)}")
            
            if output_data:
                st.success(f"合計 {count} チームの文章を作成しました！")
                csv = pd.DataFrame(output_data).to_csv(index=False, encoding='utf-8-sig')
                st.download_button("📥 全チーム分の文言をCSVでダウンロード", csv, "yosakoi_posts.csv", "text/csv", use_container_width=True)

else:
    st.info("データを読み込み中です...")
