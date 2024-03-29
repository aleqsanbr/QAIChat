import math
import hashlib
import os
import time
import telebot
import openai
from telebot import types
import re
from sqlite3worker import Sqlite3Worker as slw
import tiktoken


encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
user_db = slw("qai.db")
replies_db = slw("multilang_replies.db")
msgs = {}
history_debug = {}
bot = telebot.TeleBot(open("botapi.txt").readline(), parse_mode=None, skip_pending=True)


def get_all_users_ids():
    ids_raw = user_db.execute("SELECT user_id FROM user_data")
    ids = []
    for id in ids_raw:
        ids.append(int(id[0]))
    return ids


@bot.message_handler(commands=['admin_send_message'])
def admin_send_message(message):
    if int(message.chat.id) == int(open("creator_id.txt", "r").readline()):
        bot.send_message(message.chat.id, "Введите сообщение для отправки пользователям.")
        bot.register_next_step_handler(message, admin_send_message_worker)
    else:
        bot.send_message(message.chat.id, "❌")


def admin_send_message_worker(message):
    for id in get_all_users_ids():
        bot.send_message(id, f"<b>ℹ️ {insert_reply_byid('service_notification', id)}</b>\n\n{message.text}",
                         parse_mode="HTML")
        time.sleep(5)


def get_user_data_row(user_id: int):
    results = user_db.execute('SELECT * FROM user_data WHERE user_id = ?', (user_id,))
    return results[0]


def get_reply_row(reply_name: str):
    results = replies_db.execute('SELECT * FROM multilang_replies WHERE reply_name = ?', (reply_name,))
    return results[0]


def insert_reply_byid(reply_name: str, user_id: int):
    reply_row = get_reply_row(reply_name)
    user_row = user_db.execute('SELECT * FROM user_data WHERE user_id = ?', (user_id,))[0]
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
    user_db.execute(f"UPDATE user_data SET model = ? WHERE user_id = ?", (model, user_id,))


def set_apikey_db(api: str | None, user_id: int):
    user_db.execute(f"UPDATE user_data SET apikey = ? WHERE user_id = ?", (api, user_id,))


def set_context_db(context_on: int, user_id: int):
    if context_on != 0:
        context_on = 1
    user_db.execute(f"UPDATE user_data SET context_on = ? WHERE user_id = ?", (context_on, user_id,))


def set_lang_db(lang: str, user_id: int):
    user_db.execute(f"UPDATE user_data SET lang = ? WHERE user_id = ?", (lang, user_id,))


def set_id_db(user_id: int):
    sql = 'INSERT OR IGNORE INTO user_data (user_id) values(?)'
    data = [user_id]
    user_db.execute(sql, data)


@bot.callback_query_handler(func=lambda call: call.data in ['ru', 'en'])
def lang_call(call):
    set_lang_db(call.data, call.message.chat.id)
    if call.data == 'ru':
        bot.send_message(call.message.chat.id, 'Вы выбрали русский язык.')
    elif call.data == 'en':
        bot.send_message(call.message.chat.id, 'You have chosen English language.')
    else:
        bot.send_message(call.message.chat.id, 'Хммм....')


@bot.message_handler(func=lambda message: message.chat.id not in get_all_users_ids())
@bot.message_handler(commands=['start'])
def send_welcome(message):
    set_id_db(message.chat.id)
    if context_is_on(message.chat.id):
        set_context_db(1, message.chat.id)
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
    user_db.execute("DELETE FROM msgs_history WHERE user_id = ?", (message.chat.id,))


@bot.message_handler(commands=['debug'])
def debug(message):
    output = ""
    for n in get_user_data_row(message.chat.id):
        output += str(n) + "\n"
    bot.reply_to(message, output)


@bot.callback_query_handler(func=lambda call: str(call.data).startswith("DEL_"))
def delete_call(call):
    user_db.execute("DELETE FROM msgs_history WHERE message_id = ?", (call.data[4:],))
    bot.send_message(call.message.chat.id, insert_reply_byid("deleted", call.message.chat.id))


@bot.message_handler(commands=['select_to_delete'])
def select_to_delete(message):
    all_user_context = user_db.execute('SELECT * FROM msgs_history WHERE user_id = ?', (message.chat.id,))
    if len(all_user_context) < 1:
        bot.send_message(message.chat.id, insert_reply_byid("no_msgs", message.chat.id))
        return
    wait_msg = bot.send_message(message.chat.id, insert_reply_byid("counting_tokens", message.chat.id))
    delete_keyboard = types.InlineKeyboardMarkup()
    for i in range(0, len(all_user_context)):
        msg = all_user_context[i][2]
        msg_tokens = len(encoding.encode(msg))
        delete_keyboard.add(types.InlineKeyboardButton(
            f'[{msg_tokens}] {all_user_context[i][1].capitalize()}: "{msg[:100]}"',
            callback_data="DEL_" + str(all_user_context[i][3]))
        )
    bot.send_message(message.chat.id, insert_reply_byid("select_to_delete", message.chat.id),
                     reply_markup=delete_keyboard)
    bot.delete_message(message.chat.id, wait_msg.id)


@bot.message_handler(commands=['export'])
def export(message):
    all_user_context = user_db.execute('SELECT * FROM msgs_history WHERE user_id = ?', (message.chat.id,))
    if len(all_user_context) < 1:
        bot.send_message(message.chat.id, insert_reply_byid("no_msgs_to_export", message.chat.id))
        return
    file_name = f"export_{message.chat.id}.txt"
    with open(file_name, "w", encoding='utf-8') as txt:
        for i in range(0, len(all_user_context)):
            msg = all_user_context[i][2]
            txt.write(f'{all_user_context[i][1].capitalize()}: "{msg}"\n\n')

    bot.send_document(message.chat.id,
                      open(file_name, "rb"),
                      None,
                      insert_reply_byid("file_sent", message.chat.id),
                      )
    os.remove(file_name)


@bot.message_handler(commands=['motherlode'])
def demo(message):
    bot.reply_to(message, "ok")
    set_apikey_db(open("openaiapi.txt").readline(), message.chat.id)


def add_context_element(role: str, content: str, user_id: int):
    data = f"{user_id}{role}{content}{time.time()}"
    muid = hashlib.md5(data.encode()).hexdigest()
    user_db.execute("INSERT INTO msgs_history (user_id, role, message, message_id) VALUES (?, ?, ?, ?)",
                    (user_id, role, content, muid))


def select_all_user_context(user_id: int):
    all_user_context = user_db.execute('SELECT * FROM msgs_history WHERE user_id = ?', (user_id,))
    msgs[user_id] = list()
    for i in range(0, len(all_user_context)):
        msgs[user_id].append({"role": all_user_context[i][1], "content": all_user_context[i][2]})


@bot.callback_query_handler(func=lambda call: call.data == "continue_system")
def continue_system_call(call):
    bot.send_message(call.message.chat.id, insert_reply_byid("enter_system_text", call.message.chat.id))
    bot.register_next_step_handler(call.message, set_system_worker)


@bot.message_handler(commands=['set_system'])
def set_system(message):
    continue_system_kb = types.InlineKeyboardMarkup()
    continue_system_kb.add(types.InlineKeyboardButton(insert_reply_byid("add_system_button", message.chat.id),
                                                      callback_data="continue_system"))
    bot.send_message(message.chat.id, insert_reply_byid("set_system", message.chat.id), reply_markup=continue_system_kb)


def set_system_worker(message):
    add_context_element("system", message.text, message.chat.id)
    bot.send_message(message.chat.id, "✔️")


@bot.callback_query_handler(func=lambda call: call.data in ["context_reset", "select_to_delete"])
def length_err_call(call):
    if call.data == "context_reset":
        context_reset(call.message)
    if call.data == "select_to_delete":
        select_to_delete(call.message)


def custom_Exception(e, user_id):
    bot.send_message(user_id, f"{insert_reply_byid('exception', user_id)}\n\n<b><u>{type(e).__name__}.</u></b> {e}",
                     parse_mode="HTML")


def custom_openai_InvalidRequestError(e, user_id):
    token_lengths = re.findall(r"\d+(?=\s+tokens)", str(e))
    to_remove = int(token_lengths[1]) - int(token_lengths[0])
    length_err_keyboard = types.InlineKeyboardMarkup()
    length_err_keyboard.add(types.InlineKeyboardButton(insert_reply_byid("select_to_delete", user_id),
                                                       callback_data="select_to_delete"))
    length_err_keyboard.add(types.InlineKeyboardButton(insert_reply_byid("context_reset_button", user_id),
                                                       callback_data="context_reset", ))
    bot.send_message(user_id, f"{insert_reply_byid('token_length_error_1', user_id)}"
                                      f"{token_lengths[0]}"
                                      f"{insert_reply_byid('token_length_error_2', user_id)}"
                                      f"{token_lengths[1]}"
                                      f"{insert_reply_byid('token_length_error_3', user_id)}"
                                      f"{to_remove}"
                                      f"{insert_reply_byid('token_length_error_4', user_id)}"
                                      f"{math.ceil(to_remove * 3 / 4)}.",
                     parse_mode="HTML", reply_markup=length_err_keyboard)


def openai_request(user_id: int):
    openai.api_key = get_user_data_row(user_id)[1]
    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=msgs[user_id])
    openai.api_key = None
    return completion.choices[0].message.content


def process_text_msg(message_text: str, user_id: int):
    if get_user_data_row(user_id)[1] is None:
        return insert_reply_byid("noapi_error", user_id)

    bot.send_chat_action(chat_id=user_id, action="typing", timeout=10)
    if context_is_on(user_id):
        add_context_element('user', message_text, user_id)
        select_all_user_context(user_id)
    else:
        msgs[user_id] = [{"role": "user", "content": message_text}]

    current_reply = openai_request(user_id)

    if context_is_on(user_id):
        add_context_element("assistant", current_reply, user_id)

    msgs.pop(user_id, None)
    return current_reply


@bot.message_handler(func=lambda message: message.chat.id in get_all_users_ids(), content_types=['text'])
def ask_text(message):
    try:
        bot.reply_to(message, process_text_msg(message.text, message.chat.id), parse_mode=None)

    except openai.InvalidRequestError as e:
        custom_openai_InvalidRequestError(e, message.chat.id)

    except Exception as e:
        custom_Exception(e, message.chat.id)


@bot.message_handler(func=lambda message: message.chat.id in get_all_users_ids(), content_types=['document'])
def ask_document(message):
    try:
        '''
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        temp_file_path = f'temp_{message.chat.id}_{file_info}_{math.ceil(time.time())}'
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(downloaded_file)

        mime_type, _ = mimetypes.guess_type(temp_file_path)

        if mime_type and mime_type.startswith('text/'):
            with open(temp_file_path, 'r') as text_file:
                file_content = text_file.read()
                add_context_element("system",
                                    insert_reply_byid("text_file_system_notice", message.chat.id),
                                    message.chat.id)
        else:
            bot.reply_to(message, "Вы отправили не текстовый файл")

        os.remove(temp_file_path)
        '''
        bot.reply_to(message, insert_reply_byid("ud_files", message.chat.id))

    except openai.InvalidRequestError as e:
        custom_openai_InvalidRequestError(e, message.chat.id)

    except Exception as e:
        custom_Exception(e, message.chat.id)


@bot.message_handler(func=lambda message: message.chat.id in get_all_users_ids(), content_types=['voice'])
def ask_text(message):
    try:
        bot.reply_to(message, insert_reply_byid("ud_voice", message.chat.id))

    except openai.InvalidRequestError as e:
        custom_openai_InvalidRequestError(e, message.chat.id)

    except Exception as e:
        custom_Exception(e, message.chat.id)


@bot.message_handler(func=lambda message: message.chat.id in get_all_users_ids(), content_types=['video_note'])
def ask_text(message):
    try:
        bot.reply_to(message, insert_reply_byid("ud_video_note", message.chat.id))

    except openai.InvalidRequestError as e:
        custom_openai_InvalidRequestError(e, message.chat.id)

    except Exception as e:
        custom_Exception(e, message.chat.id)


bot.infinity_polling()
