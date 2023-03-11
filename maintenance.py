import telebot
import openai
bot = telebot.TeleBot("6173439493:AAFlMp3JSqy9yf8lDPX4-pg3i18VH-skS2Y", parse_mode=None, skip_pending=True)

@bot.message_handler(func=lambda message: True)
def ask(message):
    bot.reply_to(message, "Извините, в данный момент я на <b>техническом обслуживании</b>. Вернусь позже!", parse_mode="HTML")

bot.infinity_polling()

