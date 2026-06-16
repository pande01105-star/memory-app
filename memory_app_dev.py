#コメントありで見返す用
#ボタンを押したら以下の機能が起動する
# 1.メモ追加
# 2.メモ一覧
# 3.終了

#６月１１日→編集機能からスタート　削除機能との共通点を探す。らしい
# cd ~/Desktop/python_lesson pws ls python ./memory_app.py
import datetime
#dt_now = datetime.datetime.now()
#print(dt_now.strftime("%Y-%m-%d %H:%M:%S"))
# a 末尾にデータを追加する
# r 先頭から読み込む
# w 中身を全て削除して上書きする
# r+ w+ 読み込みと書き込みを同時に行う場合

#gitリリースの本質→ ローカル　→ github → デプロイ
#ターミナル上
#cd ~/Desktop/python_lesson

#git hub上
#リポジトリを作成する→トークンを作成する（必要ならパスワードも）

#ターミナル上
#git init　git初期化
#git add . ステージング
#git commit -m "first streamlit memory app"　初回コミット
#touch .gitignore　gitignoreは最初に作るのが理想
#git add . 
#git commit -m "clean project" 整理コミット
#github連携↓
#git remote add origin https://github.com/pande01105-star/memory-app.git
#git branch -M main
#git push -u origin main
#エラー：remote already exists → git remote set-url origin URL
#競合エラー → git push -u origin main --force

#ストリームリット上
#https://streamlit.io/cloud
#Repository: pande01105-star/memory-app
#Branch: main
#File: app.py

#while 条件式：
    #条件式がTRUEの間繰り返される処理
#while menu_action <= 1:

#ファイルを読み込んでリスト表示する関数
def load_memories():
    try:
        with open("memories_list", "r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        with open("memories_list", "w", encoding="utf-8"):
            pass
        return []

#リスト化されたファイルの中身を書き換えたり、追加したりして保存したい関数
def save_memories(memories):
    with open("memories_list", "w", encoding="utf-8") as f:
        for memory in memories:    
            f.write(memory)

#インデックス番号とリストの内容を表示する関数
def show_memories(memories):
    for index_num in range(len(memories)):
        print(str(index_num) + ':' + memories[index_num])

def add_memory():
    memo = input('メモを追加してください： ').strip()
    if memo == '':
        print('空の内容は保存できません')
        return
    dt_now = datetime.datetime.now()
    #追加だけ直接保存してるのでリストに追加する方法に統一する
    memories.append(dt_now.strftime("%Y-%m-%d %H:%M:%S")+ '|' + memo + "\n")
    save_memories(memories)
    #with open("memories_list", mode="a", encoding="utf-8") as f:  
            #f.write(dt_now.strftime("%Y-%m-%d %H:%M:%S")+ '|' + memo + "\n")
    print('保存しました')

def list_memories():
    print('メモ一覧')
    #with open("memories_list",mode = "r",encoding = "utf-8") as f:
        #memories = f.readlines()
    memories = load_memories()
        #for memory in memories:→いらない。
    show_memories(memories)
    #for index_num in range(len(memories)):
        #print(str(index_num) + ':' + memories[index_num] )
            #print(memories[index_num])
        #print(f.read())

def delete_memory():
    #with open("memories_list", "r", encoding="utf-8") as f:
        #memories = f.readlines()
    memories = load_memories()    
    show_memories(memories)
    #for index_num in range(len(memories)):
        #print(str(index_num) + ':' + memories[index_num] )

    #print(memories)
    try:
        delete_memory = int(input('削除するリストの番号を入力してください：(最小のリストを選択→０ )'))
    except:
        print('数字を入力してください')
        return
    if 0 <= delete_memory < len(memories):
        memories.pop(delete_memory)
        save_memories(memories)
        #with open("memories_list", "w", encoding="utf-8") as f:
            #for memory in memories:
                #f.write(memory)
        print('リスト番号： ' + str(delete_memory) + 'を削除しました')
    else:
        print('エラー：存在しないリスト番号です')

def search_memory():
    search = input('検索するキーワードを入力してください：')
    #with open("memories_list", "r", encoding="utf-8") as f:
        #memories = f.readlines()
    memories = load_memories()    
    for memory in memories:
        if search in memory:
            print(memory)

def edit_memory():
    #with open("memories_list", "r", encoding="utf-8") as f:
        #memories = f.readlines()
    memories = load_memories()
    show_memories(memories)
    #for index_num in range(len(memories)):
        #print(str(index_num) + ':' + memories[index_num] )
    try:
        edit_memory_num = int(input('編集するリストの番号を入力してください：(最小のリストを選択→０ )'))
    except:
        print('数字を入力してください')
        continue
    if 0 <= edit_memory_num < len(memories):
        edited_memory = input('編集後の内容を入力してください：')
        old_date = memories[edit_memory_num].split('|', 1)[0]
        memories[edit_memory_num] = (old_date + '|' + edited_memory + "\n")

        #new_content = memories.replace(memories[edit_memory_num],edited_memory)
        save_memories(memories)
        #with open("memories_list", "w", encoding="utf-8") as f:
            #for memory in memories:
                #f.write(memory)
        print('編集しました')        
        #memories[edit_memory_num] = edited_memory
        #with open("memories_list", "w", encoding="utf-8") as f:
            #f.write(edited_memory)
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


#def memories_addition(x):
    #path = r"Python_lesson$memories_list"
    #f = open(path, mode="a", encoding="utf-8")
# 2.
#def memories_list(x):
    #print(f.read())
    #f.close()

#変数 = open(ファイルのパス)　
     #変数.close()     
# 3.


#def action_function(x):
    #while x == 2:
        #break

#A(menu_action)


#def botton():
    #x = 0
    #while ?
    #if 
