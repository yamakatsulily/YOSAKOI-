import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="YOSAKOI投稿メーカー", layout="centered")

st.title("🎤 YOSAKOI投稿メーカー")

# 1. データの読み込み
st.sidebar.header("設定")
uploaded_file = st.sidebar.file_uploader("チームリスト(CSV)をアップロード", type="csv")

if uploaded_file:
    # CSVを読み込み（列名は元データに合わせる）
    df = pd.read_csv(uploaded_file).fillna("")
    
    tab1, tab2 = st.tabs(["🔍 チーム検索", "🗓 スケジュール一括生成"])

    with tab1:
        st.write("写真のスケジュールを見ながらチームを探せます。")
        search_query = st.text_input("チーム名の一部を入力（例：平岸）")
        
        if search_query:
            # 部分一致で検索
            results = df[df["チーム名"].str.contains(search_query, na=False)]
            if not results.empty:
                selected_team = st.selectbox("該当するチームを選択", results["チーム名"].tolist())
                row = results[results["チーム名"] == selected_team].iloc[0]
                
                # 文章生成（X用）
                st.subheader("🐦 X (Twitter)")
                x_acc = row['Xアカウント'] if row['Xアカウント'] != "(確認できず)" else ""
                x_text = f"🎤{row['チーム名']}さん\n{x_acc}\n\n演舞最高でした！✨\n\n{row['ハッシュタグ']}"
                st.text_area("X用コピー", x_text, height=150)

                # 文章生成（インスタ用）
                st.subheader("📸 Instagram")
                i_acc = row['インスタグラム'] if row['インスタグラム'] != "(確認できず)" else ""
                i_text = f"🎤{row['チーム名']}さん\n(Instagram: {i_acc})\n\n素敵な演舞をありがとうございます！\n\n{row['ハッシュタグ']}"
                st.text_area("インスタ用コピー", i_text, height=150)
            else:
                st.warning("チームが見つかりません。")

    with tab2:
        st.write("写真から書き出したチーム名を一行ずつ貼り付けてください。")
        schedule_input = st.text_area("スケジュール（チーム名を一行ずつ）", height=200)
        
        if st.button("まとめて生成"):
            lines = schedule_input.split("\n")
            for line in lines:
                team_name = line.strip()
                if team_name:
                    # チームリストから完全一致または部分一致を探す
                    matched = df[df["チーム名"].str.contains(team_name, na=False)]
                    if not matched.empty:
                        row = matched.iloc[0]
                        with st.expander(f"✅ {row['チーム名']} の投稿文"):
                            st.text_area(f"{row['チーム名']}用", f"🎤{row['チーム名']}さん\n{row['Xアカウント']}\n\n演舞お疲れ様でした！\n\n{row['ハッシュタグ']}", height=120)

else:
    st.info("左のメニューから「よさ.xlsx - Sheet1.csv」をアップロードしてください。")
