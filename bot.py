import telebot
import openai
import sqlite3 as sl
from telebot import types

user_db = sl.connect('qai.db', check_same_thread=False)
user_db_cursor = user_db.cursor()
replies_db = sl.connect("multilang_replies.db", check_same_thread=False)
replies_db_cursor = replies_db.cursor()

keylist = {}
context_on = {}
msgs = {}
history_debug = {}

bot = telebot.TeleBot(open("botapi.txt").readline(), parse_mode=None, skip_pending=True)


def get_reply_row(reply_name: str):
    replies_db_cursor.execute('SELECT * FROM multilang_replies WHERE reply_name = ?', (reply_name,))
    reply_row = replies_db_cursor.fetchall()[0]
    return reply_row


def insert_reply_id(reply_name: str, id: int):
    reply_row = get_reply_row(reply_name)
    user_db_cursor.execute('SELECT * FROM user_data WHERE user_id = ?', (id,))
    user_row = user_db_cursor.fetchall()[0]
    lang = user_row[3]
    if lang == 'en':
        return reply_row[2].replace('\\n', '\n')
    else:
        return reply_row[1].replace('\\n', '\n')


def insert_reply_lang(reply_name: str, lang: str):
    reply_row = get_reply_row(reply_name)
    if lang == 'en':
        return reply_row[2].replace('\\n', '\n')
    else:
        return reply_row[1].replace('\\n', '\n')


def set_model_db(model: str, user_id: int):
    with user_db:
        user_db.execute(f"UPDATE user_data SET model = ? WHERE user_id = ?", (model, user_id,))


def set_apikey_db(api: str, user_id: int):
    with user_db:
        user_db.execute(f"UPDATE user_data SET apikey = ? WHERE user_id = ?", (api, user_id,))


def set_context_db(context_on: bool, user_id: int):
    context_int = 1
    if not context_on:
        context_int = 0
    with user_db:
        user_db.execute(f"UPDATE user_data SET context_on = ? WHERE user_id = ?", (context_int, user_id,))


def set_lang_db(lang: str, user_id: int):
    with user_db:
        user_db.execute(f"UPDATE user_data SET lang = ? WHERE user_id = ?", (lang, user_id,))


def set_id_db(id: int):
    sql = 'INSERT OR REPLACE INTO user_data (user_id) values(?)'
    data = [id]
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
    bot.send_message(message.chat.id, insert_reply_id('start', message.chat.id), parse_mode="HTML")
    lang_keyboard = types.InlineKeyboardMarkup()
    lang_keyboard.add(types.InlineKeyboardButton('Русский', callback_data='ru'))
    lang_keyboard.add(types.InlineKeyboardButton('English', callback_data='en'))
    bot.send_message(message.chat.id,
                     f"{insert_reply_lang('choose_lang', 'ru')}\n"
                     f"{insert_reply_lang('choose_lang', 'en')}", reply_markup=lang_keyboard)


@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message, insert_reply_id('help', message.chat.id), parse_mode="HTML")


@bot.message_handler(commands=['api'])
def api(message):
    if message.chat.id in keylist.keys():
        bot.reply_to(message,
                     f"{insert_reply_id('apiok_1', message.chat.id)}{keylist[message.chat.id]}"
                     f"{insert_reply_id('apiok_2', message.chat.id)}",
                     parse_mode="HTML")
    else:
        bot.reply_to(message, insert_reply_id('api_enter', message.chat.id), parse_mode="HTML")
        bot.register_next_step_handler(message, setapi)


def setapi(message):
    keylist[message.chat.id] = message.text
    bot.reply_to(message, insert_reply_id('setapi', message.chat.id))


@bot.message_handler(commands=['delete_api'])
def delete_api(message):
    keylist.pop(message.chat.id, None)
    bot.reply_to(message, insert_reply_id('delete_api', message.chat.id))


@bot.message_handler(commands=['switch_context_on'])
def switch_context_on(message):
    context_on[message.chat.id] = True
    bot.reply_to(message, insert_reply_id('switch_context_on', message.chat.id))


@bot.message_handler(commands=['switch_context_off'])
def switch_context_off(message):
    context_on[message.chat.id] = False
    bot.reply_to(message, insert_reply_id('switch_context_off', message.chat.id))


@bot.message_handler(commands=['context_reset'])
def context_reset(message):
    bot.reply_to(message,
                 f"{insert_reply_id('context_reset_1', message.chat.id)} {context_on.get(message.chat.id, True)}.")
    if context_on.get(message.chat.id, True):
        bot.send_message(message.chat.id, insert_reply_id("context_reset_2", message.chat.id))
    else:
        bot.send_message(message.chat.id, insert_reply_id("context_reset_3", message.chat.id))
    msgs.pop(message.chat.id, None)


@bot.message_handler(commands=['debug'])
def debug(message):
    bot.reply_to(message,
                 str(context_on.get(message.chat.id, True)) + " /// " + str(message.chat.id) + " /// " + keylist.get(
                     message.chat.id, "None"))
    history_debug[message.chat.id] = ""
    for i in msgs[message.chat.id]:
        history_debug[message.chat.id] += i["role"] + ": " + i["content"] + "\n\n"
    bot.reply_to(message, history_debug[message.chat.id])
    print(msgs[message.chat.id])


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
@bot.message_handler(commands=['motherlode'])
def demo(message):
    bot.reply_to(message, "Motherlode-ключ активирован")
    keylist[message.chat.id] = open("openaiapi.txt").readline()


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!! #

@bot.message_handler(func=lambda message: True)
def ask(message):
    try:
        global msgs
        if message.chat.id not in keylist.keys():
            bot.reply_to(message, insert_reply_id("noapi_error", message.chat.id))
        else:
            # loading = bot.reply_to(message, "Отправляю запрос...")
            bot.send_chat_action(chat_id=message.chat.id, action="typing", timeout=15)
            openai.api_key = keylist[message.chat.id]
            if context_on.get(message.chat.id, True):
                msgs[message.chat.id] = list(msgs.get(message.chat.id, {}))
                msgs[message.chat.id].append({"role": "user", "content": message.text})
                what_are_you_asking = msgs[message.chat.id]
            else:
                what_are_you_asking = [{"role": "user", "content": message.text}]
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=what_are_you_asking
            )
            openai.api_key = None
            current_reply = completion.choices[0].message.content
            if context_on.get(message.chat.id, True):
                msgs[message.chat.id] = list(msgs.get(message.chat.id, {}))
                msgs[message.chat.id].append({"role": "assistant", "content": current_reply})
            # bot.delete_message(message.chat.id, loading.message_id)
            bot.reply_to(message, current_reply, parse_mode=None)
    except Exception as e:
        bot.send_message(message.chat.id, f"{insert_reply_id('exception', message.chat.id)}\n\n{e}")


bot.infinity_polling()
