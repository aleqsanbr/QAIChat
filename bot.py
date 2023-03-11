import telebot
import openai

keylist = {}
context_on = {}
previous_msgs = {}
bot = telebot.TeleBot("", parse_mode=None, skip_pending=True)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 "Привет! Это QAI Chat! Я с удовольствием помогу вам использовать ChatGPT прямо в Telegram! Для более подробных инструкций введите /help",
                 parse_mode="HTML")
    bot.send_message(message.chat.id, "По умолчанию бот не запоминает историю переписки, соответственно, ChatGPT не будет ориентироваться на предыдущие сообщения. Если вы хотите включить, введите /switch_context_on.")


@bot.message_handler(commands=['help'])
def help(message):
    bot.reply_to(message,
                 "<b>Инструкция по использованию бота</b>\n\n1️⃣ Зарегистрируйтесь на OpenAI. Для этого сначала ознакомьтесь с материалом (https://habr.com/ru/post/704600) на Habr (там подробно описано, как зарегистрировать виртуальный номер и прочие моменты, потому что OpenAI, вообще говоря, недоступен в России)\n\n2️⃣ После регистрации получите API-ключ на https://platform.openai.com/account/api-keys. Далее введите команду /api, чтобы сохранить его здесь (без этого бот работать не будет)\n\n3️⃣ После установки ключа пишите любое сообщение, я передам его ChatGPT и возвращу ответ\n\n<b>Обратите внимание:</b> бот пока не умеет запоминать контекст предыдущих сообщений.\n\n4️⃣По умолчанию бот не запоминает историю переписки, соответственно, ChatGPT не будет ориентироваться на предыдущие сообщения. Если вы хотите включить, введите /switch_context_on. В таком случае бот перейдет в режим продолжения диалога и по API будет передаваться вся история переписки, чтобы модель могла распознавать контекст. Это может работать нестабильно. Чтобы очистить сохраненную переписку, введите /context_reset. Чтобы выйти из режима, введите /switch_context_off (это сохранит переписку, но бот обращаться к ней не будет).",
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
def send_welcome(message):
    context_on[message.chat.id] = True
    bot.reply_to(message,
                 "Запоминание контекста включено. Учтите, что запоминается вся переписка, начиная с этого момента, кроме служебных команд. Вероятно, вам понадобится ее сбросить, для этого введите /context_reset. Чтобы выключить этот режим, введите /switch_context_off",
                 parse_mode="HTML")


@bot.message_handler(commands=['switch_context_off'])
def send_welcome(message):
    context_on[message.chat.id] = False
    bot.reply_to(message, "Запоминание контекста отключено. Чтобы сбросить сохраненную историю, введите /context_reset. Чтобы включить снова, введите /switch_context_on",
                 parse_mode="HTML")

@bot.message_handler(commands=['context_reset'])
def send_welcome(message):
    bot.reply_to(message, f"История переписки сброшена. ChatGPT забыл все, статус запоминания контекста: {context_on[message.chat.id]}. {'Продолжайте переписку, чтобы бот начал запоминать историю. Выключить режим: /switch_context_off' if context_on[message.chat.id] else 'Чтобы включить режим запоминания контекста, введите /switch_context_on'}",
                 parse_mode="HTML")
    previous_msgs[message.chat.id] = ""

@bot.message_handler(commands=['debug'])
def debug(message):
    bot.reply_to(message, str(context_on.get(message.chat.id, False)) + " /// " + str(message.chat.id) + " /// " + keylist.get(
        message.chat.id, "None"))
    bot.reply_to(message, previous_msgs[message.chat.id])


@bot.message_handler(func=lambda message: True)
def ask(message):
    global previous_msgs
    if message.chat.id not in keylist.keys():
        bot.reply_to(message, "Вы не установили ключ. Введите /api для того, чтобы установить")
    else:
        loading = bot.reply_to(message, "Отправляю запрос...")
        openai.api_key = keylist[message.chat.id]
        if context_on.get(message.chat.id, False):
            what_are_you_asking = previous_msgs.get(message.chat.id, "") + f"\n\n{message.from_user.first_name}: " + ((message.text + ".") if message.text[-1] not in ".!?" else message.text)
        else:
            what_are_you_asking = message.text
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Добавь сюда только одну реплику собеседника 'ChatGPT'. \n\n\n" + what_are_you_asking}
            ]
        )
        openai.api_key = None
        current_reply = completion.choices[0].message.content
        if context_on.get(message.chat.id, False):
            previous_msgs[message.chat.id] = what_are_you_asking + "\n\nChatGPT: " + current_reply
        bot.delete_message(message.chat.id, loading.message_id)
        bot.reply_to(message, current_reply, parse_mode=None)


bot.infinity_polling()
