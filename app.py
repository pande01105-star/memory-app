import streamlit as st
import datetime
from datetime import datetime, timezone, timedelta

st.title("UPDATED VERSION 1654d98")

JST = timezone(timedelta(hours=9))

st.write("JST:", datetime.now(JST))
st.write("NOW:", datetime.datetime.now())
st.write("UTC:", datetime.datetime.utcnow())

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

def add_memory(text):
    memories = load_memories()
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    dt = datetime.now(JST)
    memories.append(dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + text + "\n")
    save_memories(memories)

# ---------- UI ----------
st.title("Memory App")

menu = st.sidebar.selectbox(
    "メニュー",
    ["追加", "一覧", "検索", "削除"]
)

# ---------- 追加 ----------
if menu == "追加":
    st.subheader("メモ追加")

    text = st.text_input("メモ内容")

    if st.button("保存"):
        if text.strip() == "":
            st.warning("空のメモは保存できません")
        else:
            add_memory(text)
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