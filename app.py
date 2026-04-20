import streamlit as st
import pandas as pd

st.set_page_config(page_title="YOSAKOI現地投稿くん", layout="centered")

st.title("🎤 YOSAKOI現地投稿くん")
st.caption("イベント管理・ワンタップコピー対応 究極版")

# ==========================================
# 1. スプレッドシートのURL設定（★ここを書き換えてください★）
# ==========================================
# ① チーム一覧のCSV URL（前回と同じもの）
TEAM_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=0&single=true&output=csv"

# ② テンプレート一覧のCSV URL（今回新しく作ったシートのもの）
TEMPLATE_SHEET_URL = "ここに新しいURLを貼り付けてください"

# ==========================================
# 2. データの読み込み
# ==========================================
@st.cache_data(ttl=60)
def load_teams():
    try:
        df = pd.read_csv(TEAM_SHEET_URL).fillna("")
        df = df.rename(columns={"チーム名": "名前", "ふりがな": "かな", "Xアカウント": "X", "インスタグラム": "インスタ", "ハッシュタグ": "タグ"})
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_templates():
    try:
        if TEMPLATE_SHEET_URL and TEMPLATE_SHEET_URL != "ここに新しいURLを貼り付けてください":
            df = pd.read_csv(TEMPLATE_SHEET_URL).fillna("")
            return df
        else:
            # URLが設定されていない場合のデフォルト設定
            return pd.DataFrame([{
                "イベント名": "標準テンプレート",
                "X用": "🎤{名前}さん\n{X}\n\n演舞最高でした！✨\n\n{タグ}",
                "インスタ用": "🎤{名前}さん\n(Instagram: {インスタ})\n\n素敵な演舞をありがとうございます！✨\n.\n.\n{タグ}"
            }])
    except:
        return pd.DataFrame()

df_teams = load_teams()
df_templates = load_templates()

# ==========================================
# 3. イベント（テンプレート）の選択
# ==========================================
if not df_templates.empty:
    st.write("### 🎪 イベントの選択")
    selected_event = st.selectbox("現在のイベントを選択してください", df_templates["イベント名"].tolist())
    
    # 選んだイベントの定型文を取得
    template_row = df_templates[df_templates["イベント名"] == selected_event].iloc[0]
    current_x_template = template_row["X用"]
    current_insta_template = template_row["インスタ用"]
else:
    st.error("テンプレートデータが読み込めません。")
    current_x_template = ""
    current_insta_template = ""

st.divider()

# ==========================================
# 4. メイン機能
# ==========================================
if not df_teams.empty:
    tab1, tab2 = st.tabs(["🔍 1件ずつ検索", "🗓 スケジュール一括生成＆出力"])

    with tab1:
        st.write("### チーム名・ふりがなで検索")
        query = st.text_input("例：ひらぎし、科学大、そうせい など")
        
        if query:
            results = df_teams[df_teams["名前"].str.contains(query, na=False, case=False) | df_teams["かな"].str.contains(query, na=False, case=False)]
            
            if not results.empty:
                selected = st.selectbox("該当チームを選択してください", results["名前"].tolist())
                row = df_teams[df_teams["名前"] == selected].iloc[0]
                
                x_id = row['X'] if row['X'] not in ["(確認できず)", "nan", ""] else ""
                insta_id = row['インスタ'] if row['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                
                # テンプレートにデータを流し込む
                text_x = current_x_template.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'])
                text_insta = current_insta_template.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'])
                
                st.success(f"【{selected}】の情報を表示中")
                
                tab_x, tab_insta = st.tabs(["🐦 X (Twitter)", "📸 Instagram"])
                
                with tab_x:
                    # 編集エリア（ここで書き換える）
                    edited_x = st.text_area("✍️ 文章の微調整（ここで編集できます）", text_x, height=150, key=f"x_edit_{row['名前']}")
                    # コピー専用エリア（1タップコピーボタン付き）
                    st.caption("👇 右上のアイコンをタップで1発コピー！")
                    st.code(edited_x, language="text")
                    
                with tab_insta:
                    edited_insta = st.text_area("✍️ 文章の微調整（ここで編集できます）", text_insta, height=150, key=f"i_edit_{row['名前']}")
                    st.caption("👇 右上のアイコンをタップで1発コピー！")
                    st.code(edited_insta, language="text")
            else:
                st.warning("該当するチームが見つかりません。")

    with tab2:
        st.write("### スケジュールから一括生成")
        bulk_input = st.text_area("チーム名リスト（一行ずつ）", height=150)
        
        if st.button("投稿文をまとめて作る"):
            lines = bulk_input.split("\n")
            output_data = []
            unmatched_teams = [] # 失敗したチームを入れる箱
            count = 0
            
            for line in lines:
                name_part = line.strip()
                if name_part:
                    matched = df_teams[df_teams["名前"].str.contains(name_part, na=False, case=False)]
                    if not matched.empty:
                        count += 1
                        r = matched.iloc[0]
                        x_id_r = r['X'] if r['X'] not in ["(確認できず)", "nan", ""] else ""
                        insta_id_r = r['インスタ'] if r['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                        
                        res_x = current_x_template.format(名前=r['名前'], X=x_id_r, インスタ=insta_id_r, タグ=r['タグ'])
                        res_insta = current_insta_template.format(名前=r['名前'], X=x_id_r, インスタ=insta_id_r, タグ=r['タグ'])
                        
                        output_data.append({
                            "スケジュール名": name_part,
                            "正式チーム名": r['名前'],
                            "X用テキスト": res_x,
                            "Instagram用テキスト": res_insta
                        })
                        
                        with st.expander(f"✅ {r['名前']}"):
                            st.caption("👇 右上のアイコンでコピー")
                            st.code(res_x, language="text")
                    else:
                        # ヒットしなかったチームを記録
                        unmatched_teams.append(name_part)
                            
            st.write(f"合計 {count} チームの文章を作成しました。")
            
            # ❌ 生成に失敗したチームの一覧表示
            if unmatched_teams:
                st.error("❌ 以下のチームは名簿に登録されていません（手動で確認してください）")
                for un_team in unmatched_teams:
                    st.write(f"- {un_team}")
            
            # CSV一括ダウンロード
            if output_data:
                df_out = pd.DataFrame(output_data)
                csv_data = df_out.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 作成した文言をCSV(Excel)で一括ダウンロード",
                    data=csv_data,
                    file_name="yosakoi_posts.csv",
                    mime="text/csv",
                    type="primary"
                )
else:
    st.info("スプレッドシートのデータを読み込んでいます...")
