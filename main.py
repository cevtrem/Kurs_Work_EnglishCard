"""
Программа представляет собой телеграм-бота,
предназначенного для изучения английских слов.
Бот позволяет добавлять, удалять и учить слова в двух режимах:
учить новые слова или учить сохраненные слова.
"""

import random
import configparser
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from connect_with_db import words, users, user_words


def read_token_telegram():
    """
    Функция считывает токен для доступа к Telegram API
    из конфигурационного файла settings.ini.
    """
    config = configparser.ConfigParser()
    config.read("/home/mladinsky/Study/settings.ini")
    token_tg = config['TG']['TELEGRAM_TOKEN']
    return token_tg


print('Start telegram bot...')
state_storage = StateMemoryStorage()
token_bot = read_token_telegram()
bot = TeleBot(token_bot, state_storage=state_storage)
buttons = []


def show_hint(*lines):
    """ объединяет строки в одну строку с переносами для отображения подсказок"""
    return '\n'.join(lines)


def show_target(data):
    """ формирует строку для отображения целевого слова и его перевода"""
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    """
    Класс содержит названия команд для добавления,
     удаления слов, выбора режимов обучения и перехода между ними.
    """
    ADD_WORD = 'Добавить слово к изучению ➕'
    DELETE_WORD = 'Убрать слово из изучения🔙'
    NEXT = 'Дальше ⏭'
    LEARN_NEW = 'Учить новые слова'
    LEARN_SAVED = 'Учить сохраненные слова'
    BACK_TO_MODE = 'Назад к выбору режима'


class MyStates(StatesGroup):
    """
    Класс определяет состояния для управления процессом
    ввода и обработки данных пользователем
    """
    target_word = State()
    translate_word = State()
    another_words = State()
    target_id = State()
    learning_mode = State()


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    """
    Обработчик команд /cards и /start, который проверяет, является ли пользователь новым,
    сохраняет его в базе данных, и предлагает выбрать режим обучения.
    """
    user_id = message.from_user.id
    if user_id not in users.get_known_users():
        user_name = (bot.get_chat(user_id)).first_name
        bot.send_message(user_id, f"Hello, {user_name}, let's study English...?")
        users.save_user(user_id, user_name)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if 'learning_mode' not in data:
            select_learning_mode(message)
        else:
            show_cards(message)


def select_learning_mode(message):
    """
    Предлагает пользователю выбрать режим обучения
    (новые или сохраненные слова) и устанавливает состояние learning_mode.
    """
    markup = types.ReplyKeyboardMarkup(row_width=2)
    learn_new_btn = types.KeyboardButton(Command.LEARN_NEW)
    learn_saved_btn = types.KeyboardButton(Command.LEARN_SAVED)
    markup.add(learn_new_btn, learn_saved_btn)
    bot.send_message(message.chat.id, "Выберите режим обучения:", reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.learning_mode, message.chat.id)


@bot.message_handler(func=lambda message: message.text in [Command.LEARN_NEW, Command.LEARN_SAVED])
def set_learning_mode(message):
    """ Обработчик для установки выбранного режима обучения и вызова функции show_cards(message)."""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['learning_mode'] = message.text
    show_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def show_cards(message):
    """
    Функция, которая загружает слово в зависимости от выбранного режима обучения
     (новые или сохраненные слова) и отображает его вместе с вариантами перевода.
    """
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        learning_mode = data.get('learning_mode')
        if learning_mode == Command.LEARN_NEW:
            target_word, translate_word, others, target_id = words.get_word_from_words()
        elif learning_mode == Command.LEARN_SAVED:
            user_id = message.from_user.id
            target_word, translate_word, others, target_id = user_words.get_user_words(user_id)
        if not target_word:
            bot.send_message(message.chat.id,
                f"У вас мало сохраненных слов = {user_words.count_user_words(user_id)}, "
                f"для выбранного режима, "
                f"добавьте к изучению не меньше {10-user_words.count_user_words(user_id)} слов. "
                f"Выберите режим - Учить новые слова")
            select_learning_mode(message)
            return
    markup = types.ReplyKeyboardMarkup(row_width=2)
    global buttons
    buttons = []
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    back_to_mode_btn = types.KeyboardButton(Command.BACK_TO_MODE)
    buttons.extend([next_btn, add_word_btn, delete_word_btn, back_to_mode_btn])
    markup.add(*buttons)
    greeting = f"Выбери перевод слова:\n🇷🇺 {translate_word}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate_word
        data['other_words'] = others
        data['target_id'] = target_id


@bot.message_handler(func=lambda message: message.text == Command.BACK_TO_MODE)
def back_to_mode(message):
    """
    Функция, которая удаляет текущий режим из данных
    и вызывает функцию select_learning_mode для повторного выбора режима.
    """
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if 'learning_mode' in data:
            del data['learning_mode']
    select_learning_mode(message)


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    """Функция, которая вызывает create_cards для отображения следующей карточки."""
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    """ Функция, которая получает идентификатор слова и удаляет его из базы данных пользователя."""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = message.from_user.id
        target_id = data['target_id']
        user_words.delete_word(user_id, target_id)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    """Функция, которая получает идентификатор слова и добавляет его в базу данных пользователя."""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = message.from_user.id
        target_id = data['target_id']
        user_words.add_word(user_id, target_id)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    """
    Функция, которая проверяет ответ пользователя,
    отображает сообщение с результатом (правильно или неправильно)
    и обновляет клавиатуру с кнопками.
    """
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
