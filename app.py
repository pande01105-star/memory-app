import streamlit as st
from datetime import datetime, timezone, timedelta
from supabase import create_client
import json
from openai import OpenAI

openai_client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

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

def update_memory_ai(memory_id, ai_data):
    supabase.table("memories").update({
        "ai_understanding": ai_data.get("understanding", ""),
        "ai_example": ai_data.get("example", ""),
        "ai_extra": ai_data.get("extra", ""),
        "ai_one_line": ai_data.get("one_line", ""),
        "ai_question": ai_data.get("question", "")
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

def load_review_logs():
    user_id = st.session_state.user.id

    response = (
        supabase.table("review_logs")
        .select("*")
        .eq("user_id", user_id)
        .order("id")
        .execute()
    )
    return response.data

def summarize_memory(word, description):
    prompt = f"""
あなたは記憶術に詳しい学習アシスタントです。
ユーザーは「理解 → 1行化 → 思い出す」の流れで記憶したいです。

次のメモを、丸暗記ではなく理解して思い出せる形に変換してください。

必ずJSONだけで返してください。
説明文やコードブロックは不要です。

JSON形式:
{{
  "understanding": "意味がわかる説明",
  "example": "身近な例え話",
  "extra": "理解を助ける補足知識",
  "one_line": "自分の言葉で覚える1行",
  "question": "復習時に思い出すための問い"
}}

条件:
- 日本語
- 単なる短い要約にしない
- 例え話を必ず入れる
- 周辺知識も少し補足する
- 難しすぎる専門語は避ける
- ただし内容を雑にしない

単語:
{word}

元の説明:
{description}
"""

    response = openai_client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    text = response.output_text.strip()
    return json.loads(text)

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
    ["追加", "一覧", "検索", "復習", "統計", "AI要約", "編集", "削除"]
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
    if st.button("理解カードを作る"):
        if word.strip() == "" or description.strip() == "":
            st.warning("単語と説明を入力してから使ってください")
        else:
            with st.spinner("AIが説明を整えています..."):
                ai_data = summarize_memory(word, description)

                st.session_state.ai_data = ai_data
    
    if "ai_data" in st.session_state:
        st.markdown("### AI理解カード")

        ai_data = st.session_state.ai_data

        st.write("#### 【理解】")
        st.write(ai_data.get("understanding", ""))

        st.write("#### 【例え話】")
        st.write(ai_data.get("example", ""))

        st.write("#### 【補足】")
        st.write(ai_data.get("extra", ""))

        st.write("#### 【自分の言葉で1行】")
        st.write(ai_data.get("one_line", ""))

        st.write("#### 【思い出す問い】")
        st.write(ai_data.get("question", ""))

        col1, col2 = st.columns(2)

        with col1:
            if st.button("理解カードを採用"):
                st.session_state.use_ai_data = True
                st.rerun()

        with col2:
            if st.button("理解カードを破棄"):
                del st.session_state.ai_data
                st.rerun()

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

    final_description = description

    if st.session_state.get("use_ai_description"):
        final_description = st.session_state.ai_description

    if st.button("保存"):
        if word.strip() == "" or description.strip() == "":
            st.warning("単語と説明の両方を入力してください")
        else:
            add_memory(word, final_description, tags, importance)

            if st.session_state.get("use_ai_data"):
                memories = load_memories()
                latest_memory = memories[-1]
                update_memory_ai(latest_memory["id"], st.session_state.ai_data)

            st.success("保存しました")
            st.session_state.pop("ai_data", None)
            st.session_state.pop("use_ai_data", None)

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
                if m.get("ai_question"):
                    st.info(f"思い出す問い：{m['ai_question']}")

                st.markdown(f"## {m['word']}")

                if st.button("答えを見る", key=f"answer_{m['id']}"):
                    st.session_state[show_key] = True

                if st.session_state[show_key]:
                    if m.get("ai_understanding"):
                        st.write("#### 【理解】")
                        st.write(m.get("ai_understanding"))

                        st.write("#### 【例え話】")
                        st.write(m.get("ai_example"))

                        st.write("#### 【補足】")
                        st.write(m.get("ai_extra"))

                        st.write("#### 【自分の言葉で1行】")
                        st.write(m.get("ai_one_line"))
                    else:
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

# ---------- 統計 ----------
elif menu == "統計":
    st.subheader("学習統計")

    memories = load_memories()
    logs = load_review_logs()

    total_memories = len(memories)
    total_reviews = len(logs)

    remembered_count = len([log for log in logs if log["result"] == "remembered"])
    forgot_count = len([log for log in logs if log["result"] == "forgot"])

    if total_reviews > 0:
        remember_rate = remembered_count / total_reviews * 100
    else:
        remember_rate = 0

    col1, col2, col3 = st.columns(3)

    col1.metric("総メモ数", total_memories)
    col2.metric("総復習回数", total_reviews)
    col3.metric("正答率", f"{remember_rate:.1f}%")

    st.divider()

    st.write("### 復習結果")

    col1, col2 = st.columns(2)
    col1.metric("覚えてた", remembered_count)
    col2.metric("忘れてた", forgot_count)

    st.divider()

    st.write("### 重要度別メモ数")

    for level in range(1, 6):
        count = len([
            m for m in memories
            if (m.get("importance") or 3) == level
        ])
        st.write(f"⭐{level}: {count}件")


# ---------- AI要約 ----------
elif menu == "AI要約":
    st.subheader("AI要約")

    memories = load_memories()

    if not memories:
        st.info("要約できるメモがありません")
    else:
        for i, m in enumerate(memories):
            st.write(
                f"{i}: ⭐{m.get('importance') or 3} | {m['word']} | タグ: {m.get('tags') or 'なし'}"
            )

        index = st.number_input(
            "要約する番号",
            step=1,
            min_value=0,
            max_value=len(memories) - 1
        )

        target = memories[int(index)]

        st.markdown("### 元の説明")
        st.write(target["description"])

        if st.button("AIで要約する"):
            with st.spinner("AIが要約中..."):
                summary = summarize_memory(
                    target["word"],
                    target["description"]
                )

            st.session_state.ai_summary = summary

        if "ai_summary" in st.session_state:
            st.markdown("### AI要約結果")
            st.write(st.session_state.ai_summary)

            if st.button("この要約で説明を更新する"):
                update_memory(
                    target["id"],
                    target["word"],
                    st.session_state.ai_summary,
                    target.get("tags") or "",
                    target.get("importance") or 3
                )
                del st.session_state.ai_summary
                st.success("説明をAI要約に更新しました")
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