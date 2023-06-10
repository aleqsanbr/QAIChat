import telebot
import openai

keylist = {}
context_on = {}
msgs = {}
history_debug = {}
bot = telebot.TeleBot(open("botapi.txt").readline(), parse_mode=None, skip_pending=True)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 "Привет! Это QAI Chat! Я с удовольствием помогу вам использовать ChatGPT прямо в Telegram! Для более подробных инструкций введите /help",
                 parse_mode="HTML")
    bot.send_message(message.chat.id,
                     "По умолчанию бот запоминает историю переписки, соответственно, ChatGPT будет ориентироваться на предыдущие сообщения. Если вы хотите выключить, введите /switch_context_off.")


@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message,
                 "<b>Инструкция по использованию бота</b>\n\n1️⃣ Зарегистрируйтесь на OpenAI. Для этого сначала ознакомьтесь с материалом (https://habr.com/ru/post/704600) на Habr (там подробно описано, как зарегистрировать виртуальный номер и прочие моменты, потому что OpenAI, вообще говоря, недоступен в России)\n\n2️⃣ После регистрации получите API-ключ на https://platform.openai.com/account/api-keys. Далее введите команду /api, чтобы сохранить его здесь (без этого бот работать не будет)\n\n3️⃣ После установки ключа пишите любое сообщение, я передам его ChatGPT и возвращу ответ\n\n4️⃣ По умолчанию бот запоминает историю переписки, соответственно, ChatGPT будет ориентироваться на предыдущие сообщения. Если вы хотите выключить, введите /switch_context_off. В таком случае бот выйдет из режима продолжения диалога и по API не будет передаваться вся история переписки. Чтобы очистить сохраненную переписку, введите /context_reset. Чтобы войти из режима, введите /switch_context_on.",
                 parse_mode="HTML")


@bot.message_handler(commands=['api'])
def api(message):
    if message.chat.id in keylist.keys():
        bot.reply_to(message,
                     f"Вы уже установили ключ, вот он: <pre>{keylist[message.chat.id]}</pre>. Для удаления: /delete_api",
                     parse_mode="HTML")
    else:
        bot.reply_to(message,
                     "Введите ваш API-ключ. Он должен быть в формате <pre>sk-************************************************</pre>",
                     parse_mode="HTML")
        bot.register_next_step_handler(message, setapi)


def setapi(message):
    keylist[message.chat.id] = message.text
    bot.reply_to(message, "Ключ установлен. Изменить можно, вызвав /api", parse_mode="HTML")


@bot.message_handler(commands=['delete_api'])
def delete_api(message):
    keylist.pop(message.chat.id, None)
    bot.reply_to(message, "Ключ удален. Установить: /api", parse_mode="HTML")


@bot.message_handler(commands=['switch_context_on'])
def switch_context_on(message):
    context_on[message.chat.id] = True
    bot.reply_to(message,
                 "Запоминание контекста включено. Учтите, что запоминается вся переписка, начиная с этого момента, кроме служебных команд. Вероятно, вам понадобится ее сбросить, для этого введите /context_reset. Чтобы выключить этот режим, введите /switch_context_off",
                 parse_mode="HTML")


@bot.message_handler(commands=['switch_context_off'])
def switch_context_off(message):
    context_on[message.chat.id] = False
    bot.reply_to(message,
                 "Запоминание контекста отключено. Чтобы сбросить сохраненную историю, введите /context_reset. Чтобы включить снова, введите /switch_context_on",
                 parse_mode="HTML")


@bot.message_handler(commands=['context_reset'])
def context_reset(message):
    bot.reply_to(message,
                 f"История переписки сброшена. ChatGPT забыл все, статус запоминания контекста: {context_on.get(message.chat.id, True)}. {'Продолжайте переписку, чтобы бот начал запоминать историю. Выключить режим: /switch_context_off' if context_on.get(message.chat.id, True) else 'Чтобы включить режим запоминания контекста, введите /switch_context_on'}",
                 parse_mode="HTML")
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
            bot.reply_to(message, "Вы не установили ключ. Введите /api для того, чтобы установить")
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
                model = "gpt-3.5-turbo",
                messages = what_are_you_asking
            )
            openai.api_key = None
            current_reply = completion.choices[0].message.content
            if context_on.get(message.chat.id, True):
                msgs[message.chat.id] = list(msgs.get(message.chat.id, {}))
                msgs[message.chat.id].append({"role": "assistant", "content": current_reply})
            # bot.delete_message(message.chat.id, loading.message_id)
            bot.reply_to(message, current_reply, parse_mode=None)
    except Exception as e:
        bot.send_message(message.chat.id, f"❗️ Извините, произошла ошибка: \n\n{e}")


bot.infinity_polling()
