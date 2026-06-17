import streamlit as st
from datetime import datetime, timezone, timedelta
from supabase import create_client

JST = timezone(timedelta(hours=9))

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ---------- データ処理 ----------
def load_memories():
    response = (
        supabase.table("memories")
        .select("*")
        .order("id")
        .execute()
    )
    return response.data

def add_memory(word, description):
    dt = datetime.now(JST)

    supabase.table("memories").insert({
        "created_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "word": word,
        "description": description,
        "base_date": dt.strftime("%Y-%m-%d")
    }).execute()

def update_memory(memory_id, word, description):
    supabase.table("memories").update({
        "word": word,
        "description": description
    }).eq("id", memory_id).execute()

def delete_memory(memory_id):
    supabase.table("memories").delete().eq("id", memory_id).execute()

def reset_review_cycle(memory_id):
    today_text = datetime.now(JST).strftime("%Y-%m-%d")

    supabase.table("memories").update({
        "base_date": today_text
    }).eq("id", memory_id).execute()

# ---------- UI ----------
st.title("Memory App")

menu = st.sidebar.selectbox(
    "メニュー",
    ["追加", "一覧", "検索", "復習", "編集", "削除"]
)

# ---------- 追加 ----------
# ---------- 追加 ----------
if menu == "追加":
    st.subheader("メモ追加")

    if "word_input" not in st.session_state:
        st.session_state.word_input = ""

    if "description_input" not in st.session_state:
        st.session_state.description_input = ""

    word = st.text_input("単語", key="word_input")
    description = st.text_area("説明", key="description_input")

    if st.button("保存"):
        if word.strip() == "" or description.strip() == "":
            st.warning("単語と説明の両方を入力してください")
        else:
            add_memory(word, description)
            st.success("保存しました")

            st.session_state.word_input = ""
            st.session_state.description_input = ""

            st.rerun()

# ---------- 一覧 ----------
elif menu == "一覧":
    st.subheader("メモ一覧")

    memories = load_memories()

    if not memories:
        st.info("メモがありません")
    else:
        for i, m in enumerate(memories):
            st.write(
                f"{i}: {m['created_at']} | {m['word']} | {m['description']}"
            )
# ---------- 検索 ----------
elif menu == "検索":
    st.subheader("メモ検索")

    keyword = st.text_input("キーワード")

    if keyword:
        memories = load_memories()
        results = [
            m for m in memories
            if keyword in m["word"] or keyword in m["description"]
        ]

        if results:
            for i, m in enumerate(results):
                st.write(
                    f"{i}: {m['created_at']} | {m['word']} | {m['description']}"
                )
        else:
            st.info("該当なし")

# ---------- 編集 ----------
elif menu == "編集":
    st.subheader("メモ編集")

    memories = load_memories()

    if not memories:
        st.info("編集できるメモがありません")
    else:
        for i, m in enumerate(memories):
            st.write(
                f"{i}: {m['created_at']} | {m['word']} | {m['description']}"
            )

        index = st.number_input("編集番号", step=1, min_value=0)

        new_word = st.text_input("編集後の単語")
        new_description = st.text_area("編集後の説明")

        if st.button("編集"):
            if 0 <= index < len(memories):
                if new_word.strip() == "" or new_description.strip() == "":
                    st.warning("単語と説明の両方を入力してください")
                else:
                    memory_id = memories[int(index)]["id"]
                    update_memory(memory_id, new_word, new_description)
                    st.success("編集しました")
            else:
                st.error("存在しない番号です")
# ---------- 復習 ----------
elif menu == "復習":
    st.subheader("今日の復習")

    memories = load_memories()
    today = datetime.now(JST).date()

    review_days = [1, 3, 7, 30]
    review_cards = []

    for m in memories:
        base_date = datetime.strptime(m["base_date"], "%Y-%m-%d").date()
        days_passed = (today - base_date).days

        if days_passed in review_days:
            review_cards.append(m | {"days_passed": days_passed})

    if not review_cards:
        st.info("今日復習するカードはありません")
    else:
        for i, m in enumerate(review_cards):
            st.write(f"問題 {i+1}")
            st.write(f"復習サイクル開始から {m['days_passed']} 日後")
            st.write(f"単語：{m['word']}")

            if st.button("答えを見る", key=f"answer_{m['id']}"):
                st.write(f"説明：{m['description']}")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("覚えてた", key=f"remember_{m['id']}"):
                        st.success("OK。次の復習タイミングまで保存します")

                with col2:
                    if st.button("忘れてた", key=f"forgot_{m['id']}"):
                        reset_review_cycle(m["id"])
                        st.warning("復習サイクルを今日からやり直します")

            st.divider()

# ---------- 削除 ----------
elif menu == "削除":
    st.subheader("メモ削除")

    memories = load_memories()

    if not memories:
        st.info("削除できるメモがありません")
    else:
        for i, m in enumerate(memories):
            st.write(
                f"{i}: {m['created_at']} | {m['word']} | {m['description']}"
            )

        index = st.number_input("削除番号", step=1, min_value=0)

        if st.button("削除"):
            if 0 <= index < len(memories):
                memory_id = memories[int(index)]["id"]
                delete_memory(memory_id)
                st.success("削除しました")
            else:
                st.error("存在しない番号です")