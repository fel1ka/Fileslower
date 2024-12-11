import os
import requests
import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import threading

# Максимальный размер файла Telegram (2 ГБ)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  # Размер блока 1 МБ

# Инициализация бота
TOKEN = "7672677237:AAE72qOuVzpj9JAEBk1QACEVltxJVyoSN9o"  # Замените на токен вашего бота
bot = telebot.TeleBot(TOKEN)

# Хранилище состояния загрузки
download_state = {}

# Функция для загрузки файла с прогрессом
def download_file_with_progress(url, output_path, chat_id, message_id):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded_size = 0

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chat_id in download_state and not download_state[chat_id]:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Загрузка остановлена.")
                return

            if chunk:  # Проверка, чтобы не писать пустые блоки
                f.write(chunk)
                downloaded_size += len(chunk)
                percent = downloaded_size / total_size * 100
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Загружено: {percent:.2f}%")

    # После завершения загрузки отправить файл
    try:
        bot.send_document(chat_id, open(output_path, 'rb'))
        os.remove(output_path)  # Удаление временного файла
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Загрузка завершена и файл отправлен.")
    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Ошибка при отправке файла: {str(e)}")

# Команда /start для начала работы
@bot.message_handler(commands=['start'])
def start(message: Message):
    bot.reply_to(message, "Привет! Отправь мне прямую ссылку на файл, и я скачаю его для тебя.")

# Обработчик сообщений с ссылками
@bot.message_handler(func=lambda message: True)
def handle_message(message: Message):
    url = message.text

    # Проверка на валидность ссылки
    if not url.startswith("http://") and not url.startswith("https://"):
        bot.reply_to(message, "Пожалуйста, отправь действительную прямую ссылку на файл.")
        return

    # Отправка сообщения с прогрессом и кнопкой "Остановить"
    markup = InlineKeyboardMarkup()
    stop_button = InlineKeyboardButton("Остановить", callback_data="stop")
    markup.add(stop_button)

    msg = bot.reply_to(message, "Начинаю загрузку файла... 0.00%", reply_markup=markup)
    chat_id = message.chat.id
    message_id = msg.message_id

    # Установка состояния загрузки в активное
    download_state[chat_id] = True

    try:
        # Получение имени файла из URL
        file_name = url.split('/')[-1]
        temp_path = f"temp_{file_name}"

        # Запуск загрузки файла в отдельном потоке
        threading.Thread(target=download_file_with_progress, args=(url, temp_path, chat_id, message_id)).start()

    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Произошла ошибка при загрузке: {str(e)}")

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: call.data == "stop")
def stop_download(call):
    chat_id = call.message.chat.id
    if chat_id in download_state:
        download_state[chat_id] = False
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Загрузка остановлена.")

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
