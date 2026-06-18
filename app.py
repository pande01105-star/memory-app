import streamlit as st
from datetime import datetime, timezone, timedelta
from supabase import create_client

JST = timezone(timedelta(hours=9))

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

if st.session_state.access_token and st.session_state.refresh_token:
    try:
        supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )
        supabase.postgrest.auth(st.session_state.access_token)
    except Exception:
        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None

# ---------- データ処理 ----------
def sign_up(email, password):
    return supabase.auth.sign_up({
        "email": email,
        "password": password
    })

def sign_in(email, password):
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

def sign_out():
    supabase.auth.sign_out()

def load_memories():
    user_id = st.session_state.user.id

    response = (
        supabase.table("memories")
        .select("*")
        .eq("user_id", user_id)
        .order("id")
        .execute()
    )
    return response.data

def add_memory(word, description, tags, importance):
    dt = datetime.now(JST)
    user_id = st.session_state.user.id

    supabase.table("memories").insert({
        "created_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "word": word,
        "description": description,
        "base_date": dt.strftime("%Y-%m-%d"),
        "user_id": user_id,
        "tags": tags,
        "importance": importance
    }).execute()

def update_memory(memory_id, word, description, tags, importance):
    supabase.table("memories").update({
        "word": word,
        "description": description,
        "tags": tags,
        "importance": importance
    }).eq("id", memory_id).execute()

def delete_memory(memory_id):
    supabase.table("memories").delete().eq("id", memory_id).execute()

def reset_review_cycle(memory_id):
    today_text = datetime.now(JST).strftime("%Y-%m-%d")

    supabase.table("memories").update({
        "base_date": today_text
    }).eq("id", memory_id).execute()

def add_review_log(memory_id, result):
    user_id = st.session_state.user.id

    supabase.table("review_logs").insert({
        "memory_id": memory_id,
        "user_id": user_id,
        "reviewed_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }).execute()

# ---------- UI ----------
st.title("Memory App")
if st.session_state.user is None:
    st.subheader("ログイン / 新規登録")

    auth_menu = st.radio("選択", ["ログイン", "新規登録"])

    email = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")

    if auth_menu == "新規登録":
        if st.button("新規登録"):
            if email.strip() == "" or password.strip() == "":
                st.warning("メールアドレスとパスワードを入力してください")
            else:
                try:
                    response = sign_up(email, password)

                    st.session_state.user = response.user
                    st.session_state.access_token = response.session.access_token
                    st.session_state.refresh_token = response.session.refresh_token

                    supabase.auth.set_session(
                        st.session_state.access_token,
                        st.session_state.refresh_token
                    )

                    supabase.postgrest.auth(st.session_state.access_token)

                    st.success("ログインしました")
                    st.rerun()
                except Exception as e:
                    st.error("登録に失敗しました")
                    st.write(e)

    else:
        if st.button("ログイン"):
            if email.strip() == "" or password.strip() == "":
                st.warning("メールアドレスとパスワードを入力してください")
            else:
                try:
                    response = sign_in(email, password)

                    st.session_state.user = response.user
                    st.session_state.access_token = response.session.access_token
                    st.session_state.refresh_token = response.session.refresh_token

                    supabase.auth.set_session(
                        st.session_state.access_token,
                        st.session_state.refresh_token
                    )

                    supabase.postgrest.auth(st.session_state.access_token)

                    st.success("ログインしました")
                    st.rerun()
                except Exception as e:
                    st.error("ログインに失敗しました")
                    st.write(e)

    st.stop()

st.sidebar.write(f"ログイン中: {st.session_state.user.email}")

if st.sidebar.button("ログアウト"):
    sign_out()
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.rerun()

menu = st.sidebar.selectbox(
    "メニュー",
    ["追加", "一覧", "検索", "復習", "編集", "削除"]
)

# ---------- 追加 ----------
if menu == "追加":
    st.subheader("メモ追加")

    if "clear_count" not in st.session_state:
        st.session_state.clear_count = 0

    word = st.text_input(
        "単語",
        key=f"word_input_{st.session_state.clear_count}"
    )

    description = st.text_area(
        "説明",
        key=f"description_input_{st.session_state.clear_count}"
    )

    tags = st.text_input(
        "タグ（カンマ区切りで入力）",
        placeholder="例：Python, Git, AI",
        key=f"tags_input_{st.session_state.clear_count}"
    )

    importance = st.slider(
        "重要度",
        min_value=1,
        max_value=5,
        value=3,
        key=f"importance_input_{st.session_state.clear_count}"
    )

    if st.button("保存"):
        if word.strip() == "" or description.strip() == "":
            st.warning("単語と説明の両方を入力してください")
        else:
            add_memory(word, description, tags, importance)
            st.success("保存しました")

            st.session_state.clear_count += 1
            st.rerun()

# ---------- 一覧 ----------
elif menu == "一覧":
    st.subheader("メモ一覧")

    memories = load_memories()
    selected_tag = st.text_input("タグで絞り込み")
    if selected_tag:
        memories = [
            m for m in memories
            if selected_tag.lower()
            in (m.get("tags") or "").lower()
        ]
    min_importance = st.slider("重要度で絞り込み",min_value=1,max_value=5,value=1)

    memories = [
        m for m in memories
        if (m.get("importance") or 3) >= min_importance
    ]

    if not memories:
        st.info("メモがありません")
    else:
        for i, m in enumerate(memories):
            with st.container(border=True):
                st.markdown(f"### {m['word']}")

                st.write(m["description"])

                st.caption(
                    f"⭐{m.get('importance') or 3} | "
                    f"タグ: {m.get('tags') or 'なし'} | "
                    f"作成日: {m['created_at']}"
                )  

# ---------- 検索 ----------
elif menu == "検索":
    st.subheader("メモ検索")

    keyword = st.text_input("キーワード")

    if keyword:
        memories = load_memories()
        results = [
            m for m in memories
            if keyword.lower() in m["word"].lower()
            or keyword.lower() in m["description"].lower()
            or keyword.lower() in (m.get("tags") or "").lower()
        ]

        if results:
            for m in results:
                with st.container(border=True):
                    st.markdown(f"### {m['word']}")
                    st.write(m["description"])
                    st.caption(
                        f"⭐{m.get('importance') or 3} | "
                        f"タグ: {m.get('tags') or 'なし'} | "
                        f"作成日: {m['created_at']}"
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
                f"{i}: ⭐{m.get('importance') or 3} | {m['word']} | {m['description']} | タグ: {m.get('tags') or 'なし'}"
            )

        index = st.number_input("編集番号", step=1, min_value=0)

        if 0 <= index < len(memories):
            target = memories[int(index)]

            new_word = st.text_input("編集後の単語", value=target["word"])
            new_description = st.text_area("編集後の説明", value=target["description"])
            new_tags = st.text_input("編集後のタグ", value=target.get("tags") or "")
            new_importance = st.slider(
                "編集後の重要度",
                min_value=1,
                max_value=5,
                value=target.get("importance") or 3
            )

            if st.button("編集"):
                if new_word.strip() == "" or new_description.strip() == "":
                    st.warning("単語と説明の両方を入力してください")
                else:
                    memory_id = target["id"]
                    update_memory(memory_id, new_word, new_description, new_tags, new_importance)
                    st.success("編集しました")
                    st.rerun()
        else:
            st.error("存在しない番号です")

# ---------- 復習 ----------
elif menu == "復習":
    st.subheader("今日の復習")

    memories = load_memories()
    today = datetime.now(JST).date()

    review_days = [0, 1, 3, 7, 30]
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
            show_key = f"show_answer_{m['id']}"

            if show_key not in st.session_state:
                st.session_state[show_key] = False

            with st.container(border=True):
                st.markdown(f"### 問題 {i+1}")
                st.caption(
                    f"復習サイクル開始から {m['days_passed']} 日後 | "
                    f"⭐{m.get('importance') or 3} | "
                    f"タグ: {m.get('tags') or 'なし'}"
                )

                st.markdown(f"## {m['word']}")

                if st.button("答えを見る", key=f"answer_{m['id']}"):
                    st.session_state[show_key] = True

                if st.session_state[show_key]:
                    st.write(m["description"])

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("覚えてた", key=f"remember_{m['id']}"):
                            add_review_log(m["id"], "remembered")
                            st.session_state[show_key] = False
                            st.success("OK。復習履歴に記録しました")
                            st.rerun()

                    with col2:
                        if st.button("忘れてた", key=f"forgot_{m['id']}"):
                            add_review_log(m["id"], "forgot")
                            reset_review_cycle(m["id"])
                            st.session_state[show_key] = False
                            st.warning("復習サイクルを今日からやり直します")
                            st.rerun()

# ---------- 削除 ----------
elif menu == "削除":
    st.subheader("メモ削除")

    memories = load_memories()

    if not memories:
        st.info("削除できるメモがありません")
    else:
        for i, m in enumerate(memories):
            with st.container(border=True):
                st.markdown(f"### {i}: {m['word']}")
                st.write(m["description"])
                st.caption(
                    f"⭐{m.get('importance') or 3} | "
                    f"タグ: {m.get('tags') or 'なし'} | "
                    f"作成日: {m['created_at']}"
                )

        index = st.number_input(
            "削除番号",
            step=1,
            min_value=0,
            max_value=len(memories) - 1
        )

        if st.button("削除"):
            memory_id = memories[int(index)]["id"]
            delete_memory(memory_id)
            st.success("削除しました")
            st.rerun()