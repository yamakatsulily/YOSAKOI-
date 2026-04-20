import streamlit as st
import pandas as pd

st.set_page_config(page_title="YOSAKOI現地投稿くん", layout="centered")

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

df_teams_raw = load_data(TEAM_SHEET_URL)
df_templates_raw = load_data(TEMPLATE_SHEET_URL)

# 列名の整理
df_teams = df_teams_raw.rename(columns={"チーム名": "名前", "ふりがな": "かな", "Xアカウント": "X", "インスタグラム": "インスタ", "ハッシュタグ": "タグ"})
df_templates = df_templates_raw.rename(columns={"行事名": "イベント名", "Twitter用": "X用", "Instagram用": "インスタ用"})

st.title("🎤 YOSAKOI現地投稿くん")

# ==========================================
# 3. テンプレート管理（ここを強化しました）
# ==========================================
with st.expander("⚙️ 投稿テンプレートの選択と編集", expanded=True):
    if not df_templates.empty:
        # イベント選択
        event_names = df_templates["イベント名"].tolist()
        # 選択状態を保持
        if "selected_event" not in st.session_state:
            st.session_state.selected_event = event_names[0]
        
        target_event = st.selectbox("イベントを選択", event_names, index=event_names.index(st.session_state.selected_event))

        # イベントが切り替わった場合、または初回のみスプレッドシートから読み込む
        if "last_loaded_event" not in st.session_state or st.session_state.last_loaded_event != target_event:
            row = df_templates[df_templates["イベント名"] == target_event].iloc[0]
            st.session_state.editing_x = row["X用"]
            st.session_state.editing_i = row["インスタ用"]
            st.session_state.last_loaded_event = target_event
            st.session_state.selected_event = target_event

        # 【重要】ここでの入力内容は session_state に直接保存されるため、チーム検索しても消えません
        st.session_state.editing_x = st.text_area("X用ベース文章", st.session_state.editing_x, height=150)
        st.session_state.editing_i = st.text_area("インスタ用ベース文章", st.session_state.editing_i, height=150)
        st.caption("※ {名前} {X} {インスタ} {タグ} {part} が自動置換されます")
        
        if st.button("🔄 スプレッドシートの値に戻す（編集をリセット）"):
            del st.session_state.last_loaded_event
            st.rerun()
    else:
        st.error("テンプレートが読み込めません。")

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
                    return template.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'], part=part_num)

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
        bulk_input = st.text_area("チーム名リスト（一行ずつ）", height=150)
        bulk_part = st.text_input("一括用part", value="1", key="bulk_part")
        
        if st.button("投稿文をまとめて作る"):
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
                    
                    final_x = st.session_state.editing_x.format(名前=r['名前'], X=x_r, インスタ=i_r, タグ=r['タグ'], part=bulk_part)
                    final_i = st.session_state.editing_i.format(名前=r['名前'], X=x_r, インスタ=i_r, タグ=r['タグ'], part=bulk_part)
                    
                    output_data.append({"チーム": r['名前'], "X文章": final_x, "インスタ文章": final_i})
                    
                    with st.expander(f"✅ {r['名前']}"):
                        st.write("**🐦 X用**")
                        st.code(final_x, language="text")
                        st.write("**📸 インスタ用**")
                        st.code(final_i, language="text")
                else:
                    unmatched.append(name)
            
            if unmatched:
                st.error(f"❌ 未登録：{', '.join(unmatched)}")
            
            if output_data:
                csv = pd.DataFrame(output_data).to_csv(index=False, encoding='utf-8-sig')
                st.download_button("📥 全チーム分の文言をCSVでダウンロード", csv, "yosakoi_posts.csv", "text/csv")

else:
    st.info("データを読み込み中です...")
