import streamlit as st
import datetime

def load_memories():
    try:
        with open("memories_list", "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        return []

def save_memories(memories):
    with open("memories_list", "w", encoding="utf-8") as f:
        for m in memories:
            f.write(m)

def add_memory(text):
    memories = load_memories()
    dt = datetime.datetime.now()
    memories.append(dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + text + "\n")
    save_memories(memories)

# UI
st.title("Memory App")

menu = st.selectbox("メニュー", ["追加", "一覧", "削除"])

if menu == "追加":
    text = st.text_input("メモ")
    if st.button("保存"):
        if text != "":
            add_memory(text)
            st.success("保存した")

elif menu == "一覧":
    memories = load_memories()
    for i, m in enumerate(memories):
        st.text(f"{i}: {m}")

elif menu == "削除":
    memories = load_memories()
    for i, m in enumerate(memories):
        st.text(f"{i}: {m}")

    index = st.number_input("削除番号", step=1)

    if st.button("削除"):
        if 0 <= index < len(memories):
            memories.pop(int(index))
            save_memories(memories)
            st.success("削除した")