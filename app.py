import streamlit as st
import datetime
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

FILE_PATH = "memories_list"

# ---------- データ処理 ----------
def load_memories():
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        return []

def save_memories(memories):
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        for m in memories:
            f.write(m)

def add_memory(word, description):
    memories = load_memories()
    dt = datetime.now(JST)
    memories.append(
        dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + word + "|" + description + "\n")
    save_memories(memories)

# ---------- UI ----------
st.title("Memory App")

menu = st.sidebar.selectbox(
    "メニュー",
    ["追加", "一覧", "検索", "復習", "編集", "削除"]
)

# ---------- 追加 ----------
if menu == "追加":
    st.subheader("メモ追加")

    word = st.text_input("単語")
    description = st.text_area("説明")

    if st.button("保存"):
        if word.strip() == "" or description.strip() == "":
            st.warning("単語と説明の両方を入力してください")
        else:
            add_memory(word, description)
            st.success("保存しました")

# ---------- 一覧 ----------
elif menu == "一覧":
    st.subheader("メモ一覧")

    memories = load_memories()

    if not memories:
        st.info("メモがありません")
    else:
        for i, m in enumerate(memories):
            st.write(f"{i}: {m}")

# ---------- 検索 ----------
elif menu == "検索":
    st.subheader("メモ検索")

    keyword = st.text_input("キーワード")

    if keyword:
        memories = load_memories()
        results = [m for m in memories if keyword in m]

        if results:
            for i, m in enumerate(results):
                st.write(m)
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
            st.write(f"{i}: {m}")

        index = st.number_input("編集番号", step=1, min_value=0)

        new_word = st.text_input("編集後の単語")
        new_description = st.text_area("編集後の説明")

        if st.button("編集"):
            if 0 <= index < len(memories):
                old_date = memories[int(index)].split("|", 1)[0]

                if new_word.strip() == "" or new_description.strip() == "":
                    st.warning("単語と説明の両方を入力してください")
                else:
                    memories[int(index)] = (
                        old_date + "|" + new_word + "|" + new_description + "\n"
                    )
                    save_memories(memories)
                    st.success("編集しました")
            else:
                st.error("存在しない番号です")

# ---------- 復習 ----------
elif menu == "復習":
    st.subheader("復習")

    memories = load_memories()

    if not memories:
        st.info("復習するメモがありません")
    else:
        for i, memory in enumerate(memories):

            parts = memory.strip().split("|")

            if len(parts) >= 3:
                date = parts[0]
                word = parts[1]
                description = parts[2]

                st.write(f"問題 {i+1}")
                st.write(f"単語：{word}")

                if st.button("答えを見る", key=f"answer_{i}"):
                    st.write(f"説明：{description}")

                st.divider()

# ---------- 削除 ----------
elif menu == "削除":
    st.subheader("メモ削除")

    memories = load_memories()

    if not memories:
        st.info("削除できるメモがありません")
    else:
        for i, m in enumerate(memories):
            st.write(f"{i}: {m}")

        index = st.number_input("削除番号", step=1, min_value=0)

        if st.button("削除"):
            if 0 <= index < len(memories):
                removed = memories.pop(int(index))
                save_memories(memories)
                st.success(f"削除しました: {removed}")
            else:
                st.error("存在しない番号です")