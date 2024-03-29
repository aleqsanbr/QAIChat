import sqlite3 as sl

print("Сейчас мы настроим некоторые необходимые файлы для работы бота...")

with open("botapi.txt", "w") as botapi_txt:
    key = input("Введите API-ключ бота: ")
    botapi_txt.write(key)
    print("Создан файл botapi.txt")
with open("openaiapi.txt", "w") as openaiapi_txt:
    key = input("Введите API-ключ OpenAI: ")
    openaiapi_txt.write(key)
    print("Создан файл openaiapi.txt")

with open("creator_id.txt", "w") as creator_id_txt:
    creator_id = input("Введите ваш (как создателя бота) идентификатор телеграм "
                       "(можно, например, получить в боте https://t.me/MyChatInfoBot): ")
    creator_id_txt.write(creator_id)
    print("Создан файл creator_id.txt")

print("Создаю базу данных...")
qaidb = sl.connect('qai.db')
with qaidb:
    data = qaidb.execute("select count(*) from sqlite_master where type='table' and name='user_data'")
    for row in data:
        if row[0] == 0:
            qaidb.execute("""
                CREATE TABLE user_data (
                    user_id INTEGER PRIMARY KEY,
                    apikey TEXT,
                    context_on INTEGER,
                    lang TEXT,
                    model TEXT
                );""")
    data = qaidb.execute("select count(*) from sqlite_master where type='table' and name='msgs_history'")
    for row in data:
        if row[0] == 0:
            qaidb.execute("""
                CREATE TABLE msgs_history (
                    user_id INTEGER,
                    role TEXT,
                    message TEXT,
                    message_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES user_data(user_id)
                );""")

print("Процесс инициализации завершен.")
