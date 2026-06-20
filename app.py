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
        response = supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )

        st.session_state.user = response.user
        st.session_state.access_token = response.session.access_token
        st.session_state.refresh_token = response.session.refresh_token

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

    try:
        response = (
            supabase.table("memories")
            .select("*")
            .eq("user_id", user_id)
            .order("id")
            .execute()
        )
        return response.data

    except Exception as e:
        st.error("メモの読み込みに失敗しました")
        st.write(e)
        return []

def count_today_reviews():
    memories = load_memories()
    today = datetime.now(JST).date()
    review_days = [1, 3, 7, 30]
    today_reviewed_ids = load_today_reviewed_memory_ids()

    count = 0

    for m in memories:
        try:
            base_date = datetime.strptime(m["base_date"], "%Y-%m-%d").date()
            days_passed = (today - base_date).days

            if days_passed in review_days and m["id"] not in today_reviewed_ids:
                count += 1
        except Exception:
            pass

    return count

def add_memory(word, description, tags, importance):
    dt = datetime.now(JST)
    user_id = st.session_state.user.id

    response = (
        supabase.table("memories")
        .insert({
            "created_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "word": word,
            "description": description,
            "base_date": dt.strftime("%Y-%m-%d"),
            "user_id": user_id,
            "tags": tags,
            "importance": importance
        })
        .execute()
    )

    return response.data[0]

def update_memory(memory_id, word, description, tags, importance):
    supabase.table("memories").update({
        "word": word,
        "description": description,
        "tags": tags,
        "importance": importance
    }).eq("id", memory_id).execute()

def update_memory_ai(memory_id, ai_data, user_one_line):
    supabase.table("memories").update({
        "ai_understanding": ai_data.get("understanding", ""),
        "ai_example": ai_data.get("example", ""),
        "ai_extra": ai_data.get("extra", ""),
        "ai_one_line": user_one_line,
        "ai_question": ai_data.get("question", "")
    }).eq("id", memory_id).execute()

def update_memory_quiz(memory_id, quiz_data):
    supabase.table("memories").update({
        "ai_quiz_question": quiz_data.get("question", ""),
        "ai_quiz_answer": quiz_data.get("answer", ""),
        "ai_quiz_hint": quiz_data.get("hint", "")
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

def load_today_reviewed_memory_ids():
    user_id = st.session_state.user.id
    today_text = datetime.now(JST).strftime("%Y-%m-%d")

    response = (
        supabase.table("review_logs")
        .select("memory_id")
        .eq("user_id", user_id)
        .gte("reviewed_at", today_text + " 00:00:00")
        .lte("reviewed_at", today_text + " 23:59:59")
        .execute()
    )

    return [log["memory_id"] for log in response.data]

def add_feedback(category, content):
    user_id = st.session_state.user.id
    email = st.session_state.user.email

    supabase.table("feedbacks").insert({
        "user_id": user_id,
        "email": email,
        "created_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "content": content
    }).execute()

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
  "question": "復習時に思い出すための問い"
}}

条件:
- 日本語
- 単なる短い要約にしない
- 例え話を必ず入れる
- 周辺知識も少し補足する
- 難しすぎる専門語は避ける
- ただし内容を雑にしない
- 思い出す問いには、単語そのものを含めない
- one_line は作らない。ユーザー自身が入力する

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

def generate_tags(word, description=""):
    description_text = description.strip() if description else "説明なし"

    prompt = f"""
あなたは学習メモアプリのタグ生成AIです。

次の単語から、検索や復習に役立つタグを3〜5個作ってください。
説明がある場合は説明も参考にしてください。
説明がない場合は、単語の一般的な意味や関連分野から推測してください。

必ずJSONだけで返してください。
説明文やコードブロックは不要です。

JSON形式:
{{
  "tags": ["タグ1", "タグ2", "タグ3"]
}}

単語:
{word}

説明:
{description_text}
"""

    response = openai_client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    text = response.output_text.strip()
    return json.loads(text)

def generate_quiz(word, description):
    description_text = description.strip() if description and description.strip() else "説明なし"

    prompt = f"""
あなたは学習メモアプリのクイズ生成AIです。

次の単語から、復習用のクイズを1問作ってください。
説明がある場合は説明も参考にしてください。
説明がない場合は、単語の一般的な意味から推測してください。

必ずJSONだけで返してください。
コードブロックは禁止です。
説明文は禁止です。

JSON形式:
{{
  "question": "問題文",
  "answer": "答え",
  "hint": "ヒント"
}}

条件:
- 日本語
- 問題文に単語そのものを含めない
- 答えは短め
- ヒントは答えを直接言いすぎない

単語:
{word}

説明:
{description_text}
"""

    response = openai_client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        text={
            "format": {
                "type": "json_object"
            }
        }
    )

    text = response.output_text.strip()
    return json.loads(text)

# ---------- UI ----------
st.title("Memory App")
st.caption("理解 → 1行化 → 思い出す、の流れで覚えたいことを定着させる学習アプリです。")
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
                    st.error("ログインに失敗しました。メールアドレスかパスワードを確認してください。")
                    st.write(e)

    st.stop()

st.sidebar.write(f"ログイン中: {st.session_state.user.email}")


if st.sidebar.button("ログアウト"):
    sign_out()
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.rerun()

today_review_count = count_today_reviews()

if today_review_count > 0:
    st.sidebar.warning(f"🔥 今日の復習: {today_review_count}件")
else:
    st.sidebar.success("今日の復習はありません")

review_menu_label = "復習"

menu = st.sidebar.selectbox(
    "メニュー",
    [
        "アプリ説明",
        "追加",
        "メモ管理",
        "検索",
        "復習",
        "AIクイズ",
        "統計",
        "フィードバック"
    ],
    key="main_menu"
)

# ---------- アプリ説明 ----------
st.write("### 今日の状況")

col1, col2 = st.columns(2)
col1.metric("今日の復習", f"{today_review_count}件")
col2.metric("総メモ数", len(load_memories()))

if today_review_count > 0:
    st.warning("今日の復習があります。復習ページを開いて確認してください。")
else:
    st.success("今日の復習はありません。")
if menu == "アプリ説明":
    st.subheader("Memory App β版")
    st.warning("ページ更新をするとログイン状態が切れる場合があります。その場合は再ログインしてください。")

    st.markdown("""
### このアプリについて

このアプリは

**理解 → 1行化 → 思い出す**

という流れで知識を定着させるための学習アプリです。

---

### 基本的な使い方

① 追加

覚えたい内容を登録します。

AI理解カードを利用すると、

- 理解
- 例え話
- 補足知識
- 思い出す問い

を自動生成できます。

自分の言葉で1行化することで記憶の定着を狙います。

---

② 復習

エビングハウスの忘却曲線を参考に、

- 1日後
- 3日後
- 7日後
- 30日後

に復習カードが表示されます。

毎日アプリを開き、
「今日復習するものがないか」
を確認する使い方を想定しています。

---

③ AIクイズ

保存した内容からAIが問題を作成します。

理解できているかを確認するために使います。

---

### タグと重要度

タグと重要度は、

- 分野ごとの振り返り
- AIクイズの絞り込み
- 一覧の絞り込み

に利用できます。

---

### テスト版について

現在はβ版です。

テスト期間は1週間程度を予定しています。

良い意見でも悪い意見でも、
質問でも不具合報告でも大歓迎です。

ぜひ率直な感想を教えてください。

---

### 今後追加したい機能

#### 通知機能

アプリを開かなくても、

「今日の復習があります」

と通知する機能。

#### メモリーツリー

単語同士の関連性を可視化し、
知識同士をつなげて記憶を強化する機能。

現在構想中です。
""")

# ---------- 追加 ----------
if menu == "追加":
    st.subheader("メモ追加")
    st.info("単語を見て説明を思い出せるようにするために、覚えたい単語を追加します。")

    with st.expander("追加機能の使い方"):
        st.markdown("""
    ### パターン1：シンプルに登録する

    **単語入力：** ニューラルネットワーク  
    **説明入力：** 脳の神経回路の模倣  
    → **保存**

    ---

    ### パターン2：AI理解カードを使って登録する

    **単語入力：** ニューラルネットワーク  

    AI補助欄の **「理解カードを作る」** を押す。

    表示された

    - 理解
    - 例え話
    - 補足

    の内容を確認する。

    その後、**自分の言葉で1行にまとめる**。

    → **「理解カードを採用」**  
    → **保存**

    ---

    保存前に **AIタグを作る** または **重要度を変更する** と、一覧・復習・AIクイズで見返す際に便利です。
    """)

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
    st.divider()
    st.markdown("### AI補助")
    st.caption("AI補助は入力した単語や説明をもとに、理解カード・タグ・クイズを作成します。")

    if st.button("理解カードを作る"):
        if word.strip() == "":
            st.warning("単語を入力してください")
        else:
            with st.spinner("AIが説明を整えています..."):
                ai_data = summarize_memory(word, description)

                st.session_state.ai_data = ai_data
    
    if st.session_state.get("ai_card_adopted"):
        st.success("理解カードを採用しました。保存するとメモに反映されます。")
    
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

        user_one_line = st.text_input(
            "自分の言葉で1行化",
            placeholder="例：重要な部分だけに注目して判断する仕組み",
            key="user_one_line_input"
        )

        st.session_state.user_one_line = user_one_line

        with col1:
            if st.button("理解カードを採用"):
                if st.session_state.user_one_line.strip() == "":
                    st.warning("自分の言葉で1行化を入力してください")
                else:
                    st.session_state.use_ai_data = True
                    st.session_state.ai_card_adopted = True
                    st.rerun()

        with col2:
            if st.button("理解カードを破棄"):
                del st.session_state.ai_data
                st.rerun()

    tag_key = f"tags_input_{st.session_state.clear_count}"

    if st.button("AIタグを作る"):
        if word.strip() == "":
            st.warning("単語を入力してください")
        else:
            with st.spinner("AIがタグを考えています..."):
                tag_data = generate_tags(word, description)
                st.session_state[tag_key] = ", ".join(tag_data.get("tags", []))
                st.rerun()

    tags = st.text_input(
        "タグ（カンマ区切りで入力）",
        placeholder="例：Python, Git, AI",
        key=tag_key
    )

    importance = st.slider(
        "重要度",
        min_value=1,
        max_value=5,
        value=3,
        key=f"importance_input_{st.session_state.clear_count}"
    )

    final_description = description

    if st.button("保存"):
        if word.strip() == "":
            st.warning("単語を入力してください")
        else:
            with st.spinner("保存中です。AIクイズも作成しています..."):
                saved_memory = add_memory(word, final_description, tags, importance)

                quiz_data = generate_quiz(word, final_description)
                update_memory_quiz(saved_memory["id"], quiz_data)

                if st.session_state.get("use_ai_data"):
                    update_memory_ai(
                        saved_memory["id"],
                        st.session_state.ai_data,
                        st.session_state.user_one_line
                    )

            st.success("保存しました")
            st.session_state.pop("ai_data", None)
            st.session_state.pop("use_ai_data", None)
            st.session_state.pop("ai_card_adopted", None)
            st.session_state.pop("user_one_line", None)

            st.session_state.clear_count += 1
            st.rerun()

# ---------- 一覧 ----------
elif menu == "メモ管理":
    st.subheader("メモ一覧")

    memories = load_memories()
    logs = load_review_logs()

    sort_type = st.selectbox(
        "並び順",
        [
            "新しい順",
            "古い順",
            "忘れやすい順",
            "復習回数順",
            "あいうえお順"
        ]
    )

    if sort_type == "新しい順":
        memories = sorted(
            memories,
            key=lambda x: x["created_at"],
            reverse=True
        )

    elif sort_type == "古い順":
        memories = sorted(
            memories,
            key=lambda x: x["created_at"]
        )

    elif sort_type == "あいうえお順":
        memories = sorted(
            memories,
            key=lambda x: x["word"]
        )

    elif sort_type == "復習回数順":

        review_count = {}

        for log in logs:
            memory_id = log["memory_id"]

            review_count[memory_id] = (
                review_count.get(memory_id, 0) + 1
            )

        memories = sorted(
            memories,
            key=lambda m: review_count.get(m["id"], 0),
            reverse=True
        )

    elif sort_type == "忘れやすい順":

        forgot_rate = {}

        for memory in memories:

            memory_logs = [
                log
                for log in logs
                if log["memory_id"] == memory["id"]
            ]

            total = len(memory_logs)

            forgot = len([
                log
                for log in memory_logs
                if log["result"] == "forgot"
            ])

            if total > 0:
                forgot_rate[memory["id"]] = forgot / total
            else:
                forgot_rate[memory["id"]] = 0

        memories = sorted(
            memories,
            key=lambda m: forgot_rate.get(m["id"], 0),
            reverse=True
        )

    selected_tag = st.text_input("タグで絞り込み")
    if selected_tag:
        memories = [
            m for m in memories
            if selected_tag.lower() in (m.get("tags") or "").lower()
        ]

    min_importance = st.slider(
        "重要度で絞り込み",
        min_value=1,
        max_value=5,
        value=1
    )

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

                if m.get("description"):
                    st.write(m["description"])

                if m.get("ai_one_line"):
                    st.info(f"1行化：{m.get('ai_one_line')}")

                with st.expander("理解カードを見る"):
                    if m.get("ai_understanding"):
                        st.write("#### 【理解】")
                        st.write(m.get("ai_understanding"))

                        st.write("#### 【例え話】")
                        st.write(m.get("ai_example"))

                        st.write("#### 【補足】")
                        st.write(m.get("ai_extra"))

                        st.write("#### 【思い出す問い】")
                        st.write(m.get("ai_question"))
                    else:
                        st.write("理解カードはありません")

                if m.get("ai_understanding"):
                    st.success("🧠 理解カードあり")

                if m.get("ai_quiz_question"):
                    st.info("❓ AIクイズあり")

                with st.expander("AIクイズを見る"):
                    if m.get("ai_quiz_question"):
                        st.write("#### 【問題】")
                        st.write(m.get("ai_quiz_question"))

                        st.write("#### 【ヒント】")
                        st.write(m.get("ai_quiz_hint"))

                        st.write("#### 【答え】")
                        st.write(m.get("ai_quiz_answer"))
                    else:
                        st.write("AIクイズはありません")

                with st.expander("関連メモを見る"):
                    current_tags = [
                        t.strip()
                        for t in (m.get("tags") or "").split(",")
                        if t.strip()
                    ]

                    related = []

                    for other in memories:
                        if other["id"] == m["id"]:
                            continue

                        other_tags = [
                            t.strip()
                            for t in (other.get("tags") or "").split(",")
                            if t.strip()
                        ]

                        if set(current_tags) & set(other_tags):
                            related.append(other)

                    if related:
                        for r in related[:5]:
                            st.write(
                                f"• {r['word']} "
                                f"({r.get('tags') or 'なし'})"
                            )
                    else:
                        st.write("関連メモなし")

                st.divider()

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button("編集", key=f"edit_card_{m['id']}"):
                        st.session_state.editing_memory_id = m["id"]
                        st.rerun()

                with col2:
                    if st.button("クイズ再生成", key=f"card_regen_quiz_{m['id']}"):
                        with st.spinner("AIクイズを作り直しています..."):
                            quiz_data = generate_quiz(
                                m["word"],
                                m.get("description") or m.get("ai_one_line") or ""
                            )
                            update_memory_quiz(m["id"], quiz_data)

                        st.success("AIクイズを再生成しました")
                        st.rerun()

                with col3:
                    if st.button("削除", key=f"delete_card_{m['id']}"):
                        st.session_state.deleting_memory_id = m["id"]
                        st.rerun()

                if st.session_state.get("editing_memory_id") == m["id"]:
                    st.warning("このメモを編集中です")

                    new_word = st.text_input(
                        "単語",
                        value=m["word"],
                        key=f"edit_word_{m['id']}"
                    )

                    new_description = st.text_area(
                        "説明",
                        value=m.get("description") or "",
                        key=f"edit_description_{m['id']}"
                    )

                    new_tags = st.text_input(
                        "タグ",
                        value=m.get("tags") or "",
                        key=f"edit_tags_{m['id']}"
                    )

                    new_importance = st.slider(
                        "重要度",
                        min_value=1,
                        max_value=5,
                        value=m.get("importance") or 3,
                        key=f"edit_importance_{m['id']}"
                    )

                    col_save, col_cancel = st.columns(2)

                    with col_save:
                        if st.button("保存", key=f"save_edit_{m['id']}"):
                            update_memory(
                                m["id"],
                                new_word,
                                new_description,
                                new_tags,
                                new_importance
                            )
                            st.session_state.editing_memory_id = None
                            st.success("編集しました")
                            st.rerun()

                    with col_cancel:
                        if st.button("キャンセル", key=f"cancel_edit_{m['id']}"):
                            st.session_state.editing_memory_id = None
                            st.rerun()

                if st.session_state.get("deleting_memory_id") == m["id"]:
                    st.error("本当に削除しますか？この操作は戻せません。")

                    col_delete, col_cancel_delete = st.columns(2)

                    with col_delete:
                        if st.button("完全に削除", key=f"confirm_delete_{m['id']}"):
                            delete_memory(m["id"])
                            st.session_state.deleting_memory_id = None
                            st.success("削除しました")
                            st.rerun()

                    with col_cancel_delete:
                        if st.button("削除をやめる", key=f"cancel_delete_{m['id']}"):
                            st.session_state.deleting_memory_id = None
                            st.rerun()

                review_num = len([
                    log
                    for log in logs
                    if log["memory_id"] == m["id"]
                ])

                if sort_type == "復習回数順":
                    st.info(f"📚 復習回数: {review_num}回")

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
            or keyword.lower() in (m.get("description") or "").lower()
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

# ---------- AIクイズ ----------
elif menu == "AIクイズ":
    st.subheader("AIクイズ")
    st.info("追加機能で保存した単語カードには、自動でAIクイズが作成されます。")

    with st.expander("AIクイズの使い方"):
        st.markdown("""
AIクイズでは、追加した単語カードから自動生成された問題が出題されます。

出題形式は、

- ランダム
- 苦手克服

から選べます。
""")

    memories = load_memories()
    logs = load_review_logs()

    st.write("### 出題設定")

    quiz_mode = st.radio(
        "出題形式",
        ["ランダム", "苦手克服"]
    )

    tag_filter = st.text_input(
        "タグで絞り込み",
        placeholder="例：Python, AI, Git"
    )

    min_importance = st.slider(
        "重要度で絞り込み",
        min_value=1,
        max_value=5,
        value=1,
        key="quiz_min_importance"
    )

    quiz_memories = [
        m for m in memories
        if m.get("ai_quiz_question")
        and (tag_filter.strip() == "" or tag_filter.lower() in (m.get("tags") or "").lower())
        and (m.get("importance") or 3) >= min_importance
    ]

    def quiz_score(memory):
        memory_logs = [
            log for log in logs
            if log["memory_id"] == memory["id"]
        ]

        total = len(memory_logs)

        forgot = len([
            log for log in memory_logs
            if log["result"] == "forgot"
        ])

        importance = memory.get("importance") or 3

        if total == 0:
            forgot_rate = 0.5
        else:
            forgot_rate = forgot / total

        return (
            forgot_rate * 10
            + importance
            - total * 0.1
        )

    if quiz_mode == "苦手克服":
        quiz_memories = sorted(
            quiz_memories,
            key=quiz_score,
            reverse=True
        )

    if not quiz_memories:
        st.info("条件に合うクイズがありません")
    else:
        import random

        if "quiz_index" not in st.session_state:
            if quiz_mode == "ランダム":
                st.session_state.quiz_index = random.randint(
                    0,
                    len(quiz_memories) - 1
                )
            else:
                st.session_state.quiz_index = 0

        if st.session_state.quiz_index >= len(quiz_memories):
            st.session_state.quiz_index = 0

        target = quiz_memories[st.session_state.quiz_index]

        st.write("### 問題")

        if quiz_mode == "苦手克服":
            st.caption("苦手克服モード：忘れやすさ・重要度・復習回数をもとに優先出題しています。")

        st.info(target.get("ai_quiz_question", ""))

        quiz_id = target["id"]

        hint_key = f"show_quiz_hint_{quiz_id}"
        answer_key = f"show_quiz_answer_{quiz_id}"

        if hint_key not in st.session_state:
            st.session_state[hint_key] = False

        if answer_key not in st.session_state:
            st.session_state[answer_key] = False

        if st.button("ヒントを見る", key=f"hint_button_{quiz_id}"):
            st.session_state[hint_key] = True

        if st.session_state[hint_key]:
            st.write("#### ヒント")
            st.write(target.get("ai_quiz_hint", ""))

        if st.button("答えを見る", key=f"answer_button_{quiz_id}"):
            st.session_state[answer_key] = True

        if st.session_state[answer_key]:
            st.write("#### 答え")
            st.success(target.get("ai_quiz_answer", ""))

            st.write("#### 元の単語")
            st.info(target.get("word", ""))

        col1, col2 = st.columns(2)

        with col1:
            if st.button("覚えてた", key=f"quiz_remember_{target['id']}"):
                add_review_log(target["id"], "remembered")
                st.success("記録しました")

                st.session_state[hint_key] = False
                st.session_state[answer_key] = False

                if quiz_mode == "ランダム":
                    st.session_state.quiz_index = random.randint(
                        0,
                        len(quiz_memories) - 1
                    )
                else:
                    st.session_state.quiz_index = 0

                st.rerun()

        with col2:
            if st.button("忘れてた", key=f"quiz_forgot_{target['id']}"):
                add_review_log(target["id"], "forgot")
                reset_review_cycle(target["id"])
                st.warning("復習サイクルを今日からやり直します")

                st.session_state[hint_key] = False
                st.session_state[answer_key] = False

                if quiz_mode == "ランダム":
                    st.session_state.quiz_index = random.randint(
                        0,
                        len(quiz_memories) - 1
                    )
                else:
                    st.session_state.quiz_index = 0

                st.rerun()

        if st.button("次の問題", key=f"next_quiz_{quiz_id}"):
            st.session_state[hint_key] = False
            st.session_state[answer_key] = False

            if quiz_mode == "ランダム":
                st.session_state.quiz_index = random.randint(
                    0,
                    len(quiz_memories) - 1
                )
            else:
                current_index = st.session_state.quiz_index
                next_index = current_index + 1

                if next_index >= len(quiz_memories):
                    next_index = 0

                st.session_state.quiz_index = next_index

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
    
    st.divider()
    st.write("### 最近忘れたメモ")

    forgot_logs = [log for log in logs if log["result"] == "forgot"]

    forgot_memory_ids = [log["memory_id"] for log in forgot_logs[-10:]]

    for memory_id in forgot_memory_ids:
        target = next((m for m in memories if m["id"] == memory_id), None)
        if target:
            st.write(f"- {target['word']}｜タグ: {target.get('tags') or 'なし'}")

elif menu == "フィードバック":
    st.subheader("感想・不具合報告")
    st.info("使ってみた感想、不具合、改善してほしい点を送れます。")

    category = st.selectbox(
        "種類",
        ["感想", "不具合", "改善案", "質問", "その他"]
    )

    content = st.text_area("内容")

    if st.button("送信"):
        if content.strip() == "":
            st.warning("内容を入力してください")
        else:
            add_feedback(category, content)
            st.success("送信しました。ありがとう！")