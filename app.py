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

    count = 0

    for m in memories:
        try:
            base_date = datetime.strptime(m["base_date"], "%Y-%m-%d").date()
            days_passed = (today - base_date).days

            if days_passed in review_days:
                count += 1
        except Exception:
            pass

    return count

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
                except Exception:
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
    st.warning(f"今日の復習が {today_review_count} 件あります。")
else:
    st.success("今日の復習はありません。")

review_menu_label = (
    f"🔥 復習（{today_review_count}件）"
    if today_review_count > 0
    else "復習"
)

menu = st.sidebar.selectbox(
    "メニュー",
    [
        "アプリ説明",
        "追加",
        "一覧",
        "検索",
        review_menu_label,
        "AIクイズ",
        "統計",
        "AI要約",
        "編集",
        "削除"
    ]
)

# ---------- アプリ説明 ----------
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
                add_memory(word, final_description, tags, importance)

                memories = load_memories()
                latest_memory = max(memories, key=lambda m: m["id"])

                quiz_data = generate_quiz(word, final_description)
                update_memory_quiz(
                    latest_memory["id"],
                    quiz_data
                )

            if st.session_state.get("use_ai_data"):
                memories = load_memories()
                latest_memory = max(memories, key=lambda m: m["id"])
                update_memory_ai(
                    latest_memory["id"],
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

# ---------- 編集 ----------
elif menu == "編集":
    st.subheader("メモ編集")

    memories = load_memories()

    if not memories:
        st.info("編集できるメモがありません")
    else:
        for i, m in enumerate(memories):
            display_text = m.get("description") or m.get("ai_one_line") or "説明なし"

            st.write(
                f"{i}: ⭐{m.get('importance') or 3} | {m['word']} | {display_text} | タグ: {m.get('tags') or 'なし'}"
            )

        index = st.number_input("編集番号", step=1, min_value=0)

        if 0 <= index < len(memories):
            target = memories[int(index)]

            new_word = st.text_input("編集後の単語", value=target["word"])
            new_description = st.text_area("編集後の説明", value=target.get("description") or "")
            new_tags = st.text_input("編集後のタグ", value=target.get("tags") or "")
            new_importance = st.slider(
                "編集後の重要度",
                min_value=1,
                max_value=5,
                value=target.get("importance") or 3
            )

            if st.button("編集"):
                if new_word.strip() == "":
                    st.warning("単語を入力してください")
                else:
                    memory_id = target["id"]
                    update_memory(memory_id, new_word, new_description, new_tags, new_importance)
                    st.success("編集しました")
                    st.rerun()
        else:
            st.error("存在しない番号です")

# ---------- 復習 ----------
elif menu == review_menu_label:
    st.subheader("今日の復習")
    st.info("単語を見て、それが何か説明できるように思い出してください。")

    with st.expander("復習機能の使い方"):
        st.markdown("""
    復習機能では、「追加」機能で単語を追加した日から、エビングハウスの忘却曲線を参考にして、

    - 1日後
    - 3日後
    - 7日後
    - 30日後

    の周期で復習カードが表示されます。

    単語を見て、それが何か説明できるか思い出してください。

    **「答えを見る」** ボタンを押した後、  
    **「覚えてた」** または **「忘れてた」** のどちらかを押してください。
    """)

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
                    if m.get("description"):
                        st.write("#### 【自分の説明】")
                        st.write(m["description"])

                    if m.get("ai_one_line"):
                        st.write("#### 【自分の言葉で1行】")
                        st.write(m.get("ai_one_line"))

                    if m.get("ai_understanding"):
                        with st.expander("理解・例え話・補足を見る"):
                            st.write("#### 【理解】")
                            st.write(m.get("ai_understanding"))

                            st.write("#### 【例え話】")
                            st.write(m.get("ai_example"))

                            st.write("#### 【補足】")
                            st.write(m.get("ai_extra"))

                    if not m.get("description") and not m.get("ai_one_line"):
                        st.write("説明がありません")

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

# ---------- AIクイズ ----------
elif menu == "AIクイズ":
    st.subheader("AIクイズ")
    st.info("追加機能で保存した単語カードには、自動でAIクイズが作成されます。")

    with st.expander("AIクイズの使い方"):
        st.markdown("""
    AIクイズでは、追加した単語カードから自動生成された問題がランダムに出題されます。

    タグと重要度を使って、出題範囲を変更できます。

    例えば、

    - 任意のタグだけ出題する
    - 重要度3以上だけ出題する
    - 特定の分野だけ復習する

    といった使い方ができます。

    問題を見て答えを思い出し、必要に応じて **ヒントを見る**、**答えを見る** を押してください。
    """)

    memories = load_memories()

    st.write("### 出題設定")

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

    if not quiz_memories:
        st.info("条件に合うクイズがありません")
    else:
        import random

        if "quiz_index" not in st.session_state:
            st.session_state.quiz_index = random.randint(
                0,
                len(quiz_memories) - 1
            )

        if st.session_state.quiz_index >= len(quiz_memories):
            st.session_state.quiz_index = 0

        target = quiz_memories[
            st.session_state.quiz_index
        ]

        st.write("### 問題")

        st.info(
            target.get("ai_quiz_question", "")
        )

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
                st.session_state.quiz_index = random.randint(
                    0,
                    len(quiz_memories) - 1
                )
                st.rerun()

        with col2:
            if st.button("忘れてた", key=f"quiz_forgot_{target['id']}"):
                add_review_log(target["id"], "forgot")
                reset_review_cycle(target["id"])
                st.warning("復習サイクルを今日からやり直します")
                st.session_state.quiz_index = random.randint(
                    0,
                    len(quiz_memories) - 1
                )
                st.rerun()

        if st.button("次の問題", key=f"next_quiz_{quiz_id}"):
            st.session_state[hint_key] = False
            st.session_state[answer_key] = False
            st.session_state.quiz_index = random.randint(
                0,
                len(quiz_memories) - 1
            )
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
            display_text = m.get("description") or m.get("ai_one_line") or "説明なし"

            with st.container(border=True):
                st.markdown(f"### {i}: {m['word']}")
                st.write(display_text)
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