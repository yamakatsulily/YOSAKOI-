import streamlit as st
import pandas as pd

st.set_page_config(page_title="YOSAKOI現地投稿くん", layout="centered")

# ==========================================
# 1. URL設定
# ==========================================
# チーム一覧
TEAM_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=0&single=true&output=csv"
# テンプレート一覧（今回いただいたURL！）
TEMPLATE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=2050053305&single=true&output=csv"

# ==========================================
# 2. データ読み込み（キャッシュクリア機能付き）
# ==========================================
def clear_cache():
    st.cache_data.clear()
    st.success("最新情報をスプレッドシートから読み込みました！")

@st.cache_data(ttl=60)
def load_data(url, default_cols):
    try:
        df = pd.read_csv(url).fillna("")
        return df
    except:
        return pd.DataFrame(columns=default_cols)

st.title("🎤 YOSAKOI現地投稿くん")

if st.button("🔄 スプレッドシートから最新情報を読み込む"):
    clear_cache()

df_teams = load_data(TEAM_SHEET_URL, ["名前", "かな", "X", "インスタ", "タグ"])
df_templates = load_data(TEMPLATE_SHEET_URL, ["イベント名", "X用", "インスタ用"])

# 列名の正規化（多少名前が違っても動くように）
df_teams = df_teams.rename(columns={"チーム名": "名前", "ふりがな": "かな", "Xアカウント": "X", "インスタグラム": "インスタ", "ハッシュタグ": "タグ"})
df_templates = df_templates.rename(columns={"行事名": "イベント名", "Twitter用": "X用", "Instagram用": "インスタ用"})

# ==========================================
# 3. テンプレート選択・編集エリア
# ==========================================
with st.expander("⚙️ 投稿テンプレートの選択と編集", expanded=True):
    if not df_templates.empty and "イベント名" in df_templates.columns:
        event_list = df_templates["イベント名"].tolist()
        selected_event = st.selectbox("使うテンプレートを選んでください", event_list)
        
        # 選択されたテンプレートをsession_stateに保持（手動編集できるように）
        target_row = df_templates[df_templates["イベント名"] == selected_event].iloc[0]
        
        # 初回またはイベント切り替え時に反映
        if "editing_x" not in st.session_state or st.session_state.get("prev_event") != selected_event:
            st.session_state.editing_x = target_row["X用"]
            st.session_state.editing_i = target_row["インスタ用"]
            st.session_state.prev_event = selected_event

        st.session_state.editing_x = st.text_area("X用ベース文章（ここで微調整OK）", st.session_state.editing_x, height=150)
        st.session_state.editing_i = st.text_area("インスタ用ベース文章（ここで微調整OK）", st.session_state.editing_i, height=150)
        st.caption("※ {名前} {X} {インスタ} {タグ} {part} が自動置換されます")
    else:
        st.warning("テンプレートデータがまだ読み込めていません。更新ボタンを押すか、スプレッドシートを確認してください。")

st.divider()

# ==========================================
# 4. メイン機能
# ==========================================
if not df_teams.empty:
    tab1, tab2 = st.tabs(["🔍 1件ずつ検索", "🗓 スケジュール一括生成"])

    with tab1:
        col_search, col_part = st.columns([3, 1])
        with col_search:
            query = st.text_input("チーム名検索", placeholder="ひらぎし、科学大など")
        with col_part:
            part_num = st.text_input("part", value="1")

        if query:
            results = df_teams[df_teams["名前"].str.contains(query, na=False, case=False) | df_teams["かな"].str.contains(query, na=False, case=False)]
            
            if not results.empty:
                selected = st.selectbox("チーム確定", results["名前"].tolist())
                row = df_teams[df_teams["名前"] == selected].iloc[0]
                
                x_id = row['X'] if row['X'] not in ["(確認できず)", "nan", ""] else ""
                insta_id = row['インスタ'] if row['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                
                # 置換処理
                def format_text(template):
                    try:
                        return template.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'], part=part_num)
                    except KeyError as e:
                        return f"⚠️ テンプレートの波カッコ設定に誤りがあります: {e}"

                res_x = format_text(st.session_state.editing_x)
                res_i = format_text(st.session_state.editing_i)

                st.success(f"【{selected}】を生成しました")
                t_x, t_i = st.tabs(["🐦 X (Twitter)", "📸 Instagram"])
                with t_x:
                    st.caption("👇 右上のアイコンでコピー")
                    st.code(res_x, language="text")
                with t_i:
                    st.caption("👇 右上のアイコンでコピー")
                    st.code(res_i, language="text")
            else:
                st.warning("見つかりません。")

    with tab2:
        bulk_input = st.text_area("チーム名リスト（一行ずつ）")
        bulk_part = st.text_input("一括用part", value="1")
        if st.button("一括生成"):
            lines = bulk_input.split("\n")
            output_data = []
            unmatched = []
            for line in lines:
                name = line.strip()
                if not name: continue
                match = df_teams[df_teams["名前"].str.contains(name, na=False, case=False)]
                if not match.empty:
                    r = match.iloc[0]
                    x_r = r['X'] if r['X'] not in ["(確認できず)", "nan", ""] else ""
                    i_r = r['インスタ'] if r['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                    
                    try:
                        final_x = st.session_state.editing_x.format(名前=r['名前'], X=x_r, インスタ=i_r, タグ=r['タグ'], part=bulk_part)
                        final_i = st.session_state.editing_i.format(名前=r['名前'], X=x_r, インスタ=i_r, タグ=r['タグ'], part=bulk_part)
                        
                        output_data.append({"チーム": r['名前'], "X文章": final_x, "インスタ文章": final_i})
                        with st.expander(f"✅ {r['名前']}"):
                            st.caption("👇 右上のアイコンでコピー")
                            st.code(final_x, language="text")
                    except KeyError as e:
                        st.error(f"⚠️ テンプレート設定エラー: {e}")
                else:
                    unmatched.append(name)
            
            if unmatched:
                st.error(f"❌ 未登録：{', '.join(unmatched)}")
            if output_data:
                csv = pd.DataFrame(output_data).to_csv(index=False, encoding='utf-8-sig')
                st.download_button("📥 CSVダウンロード", csv, "yosakoi_posts.csv", "text/csv")
