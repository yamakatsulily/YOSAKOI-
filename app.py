import streamlit as st
import pandas as pd

st.set_page_config(page_title="YOSAKOI現地投稿くん", layout="centered")

st.title("🎤 YOSAKOI現地投稿くん")
st.caption("スプレッドシート連動・全自動更新版")

# ==========================================
# 1. スプレッドシートのURL設定
# ==========================================
# 先ほど取得いただいたURLです！
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4oPDAGy6lDROLhiBEhDKLNEI-b82ghaBNr3yli5uVZbizgZmSo2Gidv0HjuZbWXnX5-yo0TJMmM99/pub?gid=0&single=true&output=csv"

# ==========================================
# 2. データの読み込み（60秒ごとに最新情報をチェック）
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    try:
        # スプレッドシートから直接読み込み
        df = pd.read_csv(SHEET_URL)
        df = df.fillna("") # 空欄をエラーにならないよう処理
        
        # エクセルそのままの列名（チーム名など）で貼られていても動くように自動変換
        rename_dict = {
            "チーム名": "名前",
            "ふりがな": "かな",
            "Xアカウント": "X",
            "インスタグラム": "インスタ",
            "ハッシュタグ": "タグ"
        }
        df = df.rename(columns=rename_dict)
        return df
    except Exception as e:
        st.error("データの読み込みに失敗しました。URLが間違っていないか確認してください。")
        return pd.DataFrame()

# データの取得
df = load_data()

# テンプレートの初期設定
if "template_x" not in st.session_state:
    st.session_state.template_x = "🎤{名前}さん\n{X}\n\n演舞最高でした！✨\n\n{タグ}"

if "template_insta" not in st.session_state:
    st.session_state.template_insta = "🎤{名前}さん\n(Instagram: {インスタ})\n\n素敵な演舞をありがとうございます！✨\n.\n.\n{タグ}"

# ==========================================
# 3. テンプレート設定エリア
# ==========================================
with st.expander("⚙️ 投稿テンプレートの設定（イベントごとに変更可能）"):
    st.write("以下の文章を書き換えると、すべての生成結果に反映されます。")
    st.session_state.template_x = st.text_area("X (Twitter) 用テンプレート", st.session_state.template_x, height=130)
    st.session_state.template_insta = st.text_area("Instagram 用テンプレート", st.session_state.template_insta, height=150)

# ==========================================
# 4. メイン機能（データが読み込めた場合のみ表示）
# ==========================================
if not df.empty:
    tab1, tab2 = st.tabs(["🔍 1件ずつ検索", "🗓 スケジュール一括生成＆出力"])

    with tab1:
        st.write("### チーム名・ふりがなで検索")
        query = st.text_input("例：ひらぎし、科学大、そうせい など")
        
        if query:
            # 検索処理
            results = df[df["名前"].str.contains(query, na=False, case=False) | df["かな"].str.contains(query, na=False, case=False)]
            
            if not results.empty:
                selected = st.selectbox("該当チームを選択してください", results["名前"].tolist())
                row = df[df["名前"] == selected].iloc[0]
                
                # テンプレートに流し込むデータの準備
                x_id = row['X'] if row['X'] not in ["(確認できず)", "nan", ""] else ""
                insta_id = row['インスタ'] if row['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                
                text_x = st.session_state.template_x.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'])
                text_insta = st.session_state.template_insta.format(名前=row['名前'], X=x_id, インスタ=insta_id, タグ=row['タグ'])
                
                st.divider()
                st.success(f"【{selected}】の情報を表示中")
                
                tab_x, tab_insta = st.tabs(["🐦 X (Twitter)", "📸 Instagram"])
                with tab_x:
                    st.text_area("X用文章（微調整できます）", text_x, height=200, key=f"x_edit_{row['名前']}")
                with tab_insta:
                    st.text_area("Instagram用文章（微調整できます）", text_insta, height=200, key=f"insta_edit_{row['名前']}")
            else:
                st.warning("該当するチームが見つかりません。スプレッドシートに追加してください。")

    with tab2:
        st.write("### スケジュールから一括生成")
        bulk_input = st.text_area("チーム名リスト（一行ずつ）", height=150)
        
        if st.button("投稿文をまとめて作る"):
            lines = bulk_input.split("\n")
            output_data = []
            count = 0
            
            for line in lines:
                name_part = line.strip()
                if name_part:
                    matched = df[df["名前"].str.contains(name_part, na=False, case=False)]
                    if not matched.empty:
                        count += 1
                        r = matched.iloc[0]
                        x_id_r = r['X'] if r['X'] not in ["(確認できず)", "nan", ""] else ""
                        insta_id_r = r['インスタ'] if r['インスタ'] not in ["(確認できず)", "nan", ""] else ""
                        
                        res_x = st.session_state.template_x.format(名前=r['名前'], X=x_id_r, インスタ=insta_id_r, タグ=r['タグ'])
                        res_insta = st.session_state.template_insta.format(名前=r['名前'], X=x_id_r, インスタ=insta_id_r, タグ=r['タグ'])
                        
                        output_data.append({
                            "スケジュール名": name_part,
                            "正式チーム名": r['名前'],
                            "X用テキスト": res_x,
                            "Instagram用テキスト": res_insta
                        })
                        
                        with st.expander(f"✅ {r['名前']}"):
                            st.text(res_x)
                            
            st.write(f"合計 {count} チームの文章を作成しました。")
            
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
