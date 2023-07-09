import telebot
import openai
import sqlite3 as sl
from telebot import types

user_db = sl.connect('qai.db', check_same_thread=False)
user_db_cursor = user_db.cursor()
replies_db = sl.connect("multilang_replies.db", check_same_thread=False)
replies_db_cursor = replies_db.cursor()

msgs = {}
history_debug = {}

bot = telebot.TeleBot(open("botapi.txt").readline(), parse_mode=None, skip_pending=True)


def get_user_data_row(user_id: int):
    user_db_cursor.execute('SELECT * FROM user_data WHERE user_id = ?', (user_id,))
    return user_db_cursor.fetchall()[0]


def get_reply_row(reply_name: str):
    replies_db_cursor.execute('SELECT * FROM multilang_replies WHERE reply_name = ?', (reply_name,))
    return replies_db_cursor.fetchall()[0]


def insert_reply_byid(reply_name: str, user_id: int):
    reply_row = get_reply_row(reply_name)
    user_db_cursor.execute('SELECT * FROM user_data WHERE user_id = ?', (user_id,))
    user_row = user_db_cursor.fetchall()[0]
    lang = user_row[3]
    if lang == 'en':
        return reply_row[2].replace('\\n', '\n')
    else:
        return reply_row[1].replace('\\n', '\n')


def insert_reply_bylang(reply_name: str, lang: str):
    reply_row = get_reply_row(reply_name)
    if lang == 'en':
        return reply_row[2].replace('\\n', '\n')
    else:
        return reply_row[1].replace('\\n', '\n')


def set_model_db(model: str, user_id: int):
    with user_db:
        user_db.execute(f"UPDATE user_data SET model = ? WHERE user_id = ?", (model, user_id,))


def set_apikey_db(api: str | None, user_id: int):
    with user_db:
        user_db.execute(f"UPDATE user_data SET apikey = ? WHERE user_id = ?", (api, user_id,))


def set_context_db(context_on: int, user_id: int):
    if context_on != 0:
        context_on = 1
    with user_db:
        user_db.execute(f"UPDATE user_data SET context_on = ? WHERE user_id = ?", (context_on, user_id,))


def set_lang_db(lang: str, user_id: int):
    with user_db:
        user_db.execute(f"UPDATE user_data SET lang = ? WHERE user_id = ?", (lang, user_id,))


def set_id_db(user_id: int):
    sql = 'INSERT OR IGNORE INTO user_data (user_id) values(?)'
    data = [user_id]
    with user_db:
        user_db.execute(sql, data)


@bot.callback_query_handler(func=lambda call: True)
def lang_call(call):
    set_lang_db(call.data, call.message.chat.id)
    if call.data == 'ru':
        bot.send_message(call.message.chat.id, 'Вы выбрали русский язык.')
    elif call.data == 'en':
        bot.send_message(call.message.chat.id, 'You have chosen English language.')


@bot.message_handler(commands=['start'])
def send_welcome(message):
    set_id_db(message.chat.id)
    bot.send_message(message.chat.id, insert_reply_byid('start', message.chat.id), parse_mode="HTML")
    lang_keyboard = types.InlineKeyboardMarkup()
    lang_keyboard.add(types.InlineKeyboardButton('Русский', callback_data='ru'))
    lang_keyboard.add(types.InlineKeyboardButton('English', callback_data='en'))
    bot.send_message(message.chat.id,
                     f"{insert_reply_bylang('choose_lang', 'ru')}\n"
                     f"{insert_reply_bylang('choose_lang', 'en')}", reply_markup=lang_keyboard)


@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message, insert_reply_byid('help', message.chat.id), parse_mode="HTML")


@bot.message_handler(commands=['api'])
def api(message):
    if get_user_data_row(message.chat.id)[1] is not None:
        bot.reply_to(message,
                     f"{insert_reply_byid('apiok_1', message.chat.id)}{get_user_data_row(message.chat.id)[1]}"
                     f"{insert_reply_byid('apiok_2', message.chat.id)}",
                     parse_mode="HTML")
    else:
        bot.reply_to(message, insert_reply_byid('api_enter', message.chat.id), parse_mode="HTML")
        bot.register_next_step_handler(message, setapi)


def setapi(message):
    set_apikey_db(message.text, message.chat.id)
    bot.reply_to(message, insert_reply_byid('setapi', message.chat.id))


@bot.message_handler(commands=['delete_api'])
def delete_api(message):
    set_apikey_db(None, message.chat.id)
    bot.reply_to(message, insert_reply_byid('delete_api', message.chat.id))


@bot.message_handler(commands=['switch_context_on'])
def switch_context_on(message):
    set_context_db(1, message.chat.id)
    bot.reply_to(message, insert_reply_byid('switch_context_on', message.chat.id))


@bot.message_handler(commands=['switch_context_off'])
def switch_context_off(message):
    set_context_db(0, message.chat.id)
    bot.reply_to(message, insert_reply_byid('switch_context_off', message.chat.id))


def context_is_on(user_id: int):
    if get_user_data_row(user_id)[2] in [1, None]:
        return True
    return False


@bot.message_handler(commands=['context_reset'])
def context_reset(message):
    bot.reply_to(message,
                 f"{insert_reply_byid('context_reset_1', message.chat.id)} {get_user_data_row(message.chat.id)[2]}.")
    if get_user_data_row(message.chat.id)[2] in [1, None]:
        bot.send_message(message.chat.id, insert_reply_byid("context_reset_2", message.chat.id))
    else:
        bot.send_message(message.chat.id, insert_reply_byid("context_reset_3", message.chat.id))
    msgs.pop(message.chat.id, None)
    user_db_cursor.execute("DELETE FROM msgs_history WHERE user_id = ?", (message.chat.id,))
    user_db.commit()


@bot.message_handler(commands=['debug'])
def debug(message):
    output = ""
    for n in get_user_data_row(message.chat.id):
        output += str(n) + "\n"
    bot.reply_to(message, output)
    print(output)
    '''
    history_debug[message.chat.id] = ""
    for i in msgs[message.chat.id]:
        history_debug[message.chat.id] += i["role"] + ": " + i["content"] + "\n\n"
    bot.reply_to(message, history_debug[message.chat.id])
    print(msgs[message.chat.id])
    '''


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
@bot.message_handler(commands=['motherlode'])
def demo(message):
    bot.reply_to(message, "ok")
    set_apikey_db(open("openaiapi.txt").readline(), message.chat.id)
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!! #


def add_context_element(role: str, content: str, user_id: int):
    with user_db:
        user_db.execute("INSERT INTO msgs_history (user_id, role, message) VALUES (?, ?, ?)", (user_id, role, content,))


@bot.message_handler(func=lambda message: True)
def ask(message):
    try:
        ### global msgs
        # Проверка на наличие установленного API-ключа
        if get_user_data_row(message.chat.id)[1] is None:
            bot.reply_to(message, insert_reply_byid("noapi_error", message.chat.id))
            return

        # loading = bot.reply_to(message, "Отправляю запрос...")

        bot.send_chat_action(chat_id=message.chat.id, action="typing", timeout=15)
        openai.api_key = get_user_data_row(message.chat.id)[1]

        if context_is_on(message.chat.id):
            # msgs[message.chat.id] = list(msgs.get(message.chat.id, {}))
            # msgs[message.chat.id].append({"role": "user", "content": message.text})
            add_context_element('user', message.text, message.chat.id)
            user_db_cursor.execute('SELECT * FROM msgs_history WHERE user_id = ?', (message.chat.id,))
            all_user_context = user_db_cursor.fetchall()
            msgs[message.chat.id] = list()
            for i in range(0, len(all_user_context)):
                msgs[message.chat.id].append({"role": all_user_context[i][1], "content": all_user_context[i][2]})
        else:
            msgs[message.chat.id] = [{"role": "user", "content": message.text}]

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=msgs[message.chat.id]
        )
        openai.api_key = None

        current_reply = completion.choices[0].message.content
        if context_is_on(message.chat.id):
            add_context_element("assistant", current_reply, message.chat.id)

        # bot.delete_message(message.chat.id, loading.message_id)
        bot.reply_to(message, current_reply, parse_mode=None)
        msgs.pop(message.chat.id, None)

    except Exception as e:
        bot.send_message(message.chat.id,
                         f"{insert_reply_byid('exception', message.chat.id)}\n\n<b><u>{type(e).__name__}.</u></b> {e}",
                         parse_mode="HTML")


bot.infinity_polling()
