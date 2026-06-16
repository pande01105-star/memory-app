import datetime

def load_memories():
    try:
        with open("memories_list", "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        with open("memories_list", "w", encoding="utf-8"):
            pass
        return []

def save_memories(memories):
    with open("memories_list", "w", encoding="utf-8") as f:
        for memory in memories:    
            f.write(memory)

def show_memories(memories):
    for index_num in range(len(memories)):
        print(str(index_num) + ':' + memories[index_num])

def add_memory():
    memo = input('メモを追加してください： ').strip()
    if memo == '':
        print('空の内容は保存できません')
        return
    memories = load_memories()
    dt_now = datetime.datetime.now()
    memories.append(dt_now.strftime("%Y-%m-%d %H:%M:%S")+ '|' + memo + "\n")
    save_memories(memories)
    print('保存しました')

def list_memories():
    print('メモ一覧')
    memories = load_memories()
    show_memories(memories)

def delete_memory():
    memories = load_memories()    
    show_memories(memories)
    try:
        index = int(input('削除するリストの番号を入力してください：(最小のリストを選択→０ )'))
    except:
        print('数字を入力してください')
        return
    if 0 <= index < len(memories):
        removed = memories.pop(index)
        save_memories(memories)
        print('リスト番号： ' + removed.strip() + 'を削除しました')
    else:
        print('エラー：存在しないリスト番号です')

def search_memory():
    search = input('検索するキーワードを入力してください：')
    memories = load_memories()    
    for memory in memories:
        if search in memory:
            print(memory)

def edit_memory():
    memories = load_memories()
    show_memories(memories)
    try:
        edit_memory_num = int(input('編集するリストの番号を入力してください：(最小のリストを選択→０ )'))
    except:
        print('数字を入力してください')
        return
    if 0 <= edit_memory_num < len(memories):
        edited_memory = input('編集後の内容を入力してください：')
        old_date = memories[edit_memory_num].split('|', 1)[0]
        memories[edit_memory_num] = (old_date + '|' + edited_memory + "\n")
        save_memories(memories)
        print('編集しました')        
        show_memories(memories)

    else:
        print('エラー：存在しないリスト番号です')

while True:
    print('0.' + 'メモ追加')
    print('1.' + 'メモ一覧')
    print('2.' + 'メモ削除')
    print('3.' + 'メモ検索')
    print('4.' + 'メモ編集')
    print('5.' + '終了')
    try:
        menu_action = int(input('メニューを選択してください： '))
    except:
        print('エラー：メニューの数字を入力してください')    
        continue

    if menu_action == 0:
        add_memory()

    elif menu_action == 1:
        list_memories()

    elif menu_action == 2:
        delete_memory()

    elif menu_action == 3:
        search_memory()
    
    elif menu_action == 4:
        edit_memory()
        
    else:
        print('終了')    
        answer = input('終了しますか(y/n):')
        if answer == "y":
            break
