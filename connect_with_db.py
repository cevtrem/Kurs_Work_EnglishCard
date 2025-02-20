"""
Модуль connect_with_db отвечает за взаимодействие с базой данных,
включая создание подключения, управление таблицами
и выполнение запросов для получения и обработки данных.
"""

import configparser
import json
import random
import psycopg2


def read_user_data():
    """
    Функция для чтения данных пользователя (имя пользователя, пароль и имя базы данных)
     из конфигурационного файла settings.ini.
    """
    config = configparser.ConfigParser()
    config.read("/home/mladinsky/Study/Kurs_Work_EnglishCard/settings.ini")
    user_db = config['BD']['user']
    password_db = config['BD']['password']
    name_db = config['BD']['db_name']
    return user_db, password_db, name_db


class Words:
    """
    Класс Words предназначен для управления словарем слов в базе данных,
    включая создание таблицы слов, заполнение таблицы данными из JSON-файла,
    а также получение случайных слов и их переводов для использования в телеграм-боте.
    """

    def __init__(self, user_db, password_db, name_db):
        self.user = user_db
        self.password = password_db
        self.db_name = name_db

    def connect_to_database(self):
        """Метод для создания подключения к базе данных"""
        return psycopg2.connect(database=self.db_name, user=self.user, password=self.password)

    def get_data_from_json(self, json_file_name):
        """
        Метод для чтения данных из указанного JSON-файла,
        который используется для заполнения таблицы слов в базе данных.
        """
        with open(f'Data_Base_Words/{json_file_name}', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data

    def drop_table_words(self, table_name):
        """Метод для удаления указанной таблицы из базы данных."""
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                DROP TABLE {table_name};
                """)
                conn.commit()

    def create_table_words(self):
        """
        Метод для создания таблицы words,
        если она еще не существует, с полями id, en, ru и tr.
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS words (
                id SERIAL PRIMARY KEY UNIQUE,
                en VARCHAR(150) UNIQUE,
                ru VARCHAR(150),
                tr VARCHAR(150)
                    );''')
                conn.commit()

    def fill_table_words(self):
        """Метод для заполнения таблицы words данными из JSON-файла words.json."""
        data = self.get_data_from_json('words.json')
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                for line in data:
                    cursor.execute('''
                    INSERT INTO words (en, ru, tr) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING''',
                    (line["en"], line["ru"], line["tr"]))
                conn.commit()

    def get_word_from_words(self):
        """
        Метод для получения случайного слова из таблицы words,
        его перевода и списка других случайных слов для создания карточек.
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''SELECT MAX(id) FROM words''')
                max_id = cursor.fetchone()[0]
                random_ids = set()
                while len(random_ids) < 4:
                    random_ids.add(random.randint(1, max_id))
                cursor.execute("SELECT id, en, ru FROM words WHERE id IN %s", (tuple(random_ids),))
                rows = cursor.fetchall()
                target_word = rows[0][1]
                translate_word = rows[0][2]
                target_id = rows[0][0]
                others = []
                for idx, row in enumerate(rows):
                    if idx != 0:
                        others.append(row[1])
        return target_word, translate_word, others, target_id


    def count_words(self):
        """Метод для получения количества слов в таблице words"""
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM words;")
                return cursor.fetchone()[0]


class Users:
    """
    Класс Users предназначен для управления пользователями в базе данных,
    включая создание таблицы пользователей,
    сохранение новых пользователей и получение списка известных пользователей.
    """

    def __init__(self, user_db, password_db, name_db):
        self.user = user_db
        self.password = password_db
        self.db_name = name_db

    def connect_to_database(self):
        """Метод для создания подключения к базе данных"""
        return psycopg2.connect(database=self.db_name, user=self.user, password=self.password)

    def create_table_users(self):
        """Метод для создания таблицы users,
        если она еще не существует, с полями id и username.
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY UNIQUE,
                username VARCHAR(100)
                    );''')

    def save_user(self, user_id, name_user):
        """
        Метод для добавления нового пользователя в таблицу users
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO users (user_id, username) VALUES (%s, %s);",
                               (user_id, name_user))
                conn.commit()

    def get_known_users(self):
        """
        Метод для получения всех известных пользователей из таблицы users,
        возвращая список всех user_id
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                known_users = []
                cursor.execute("""
                        SELECT * FROM users;
                        """)
                for data in cursor.fetchall():
                    user_id = data[0]
                    known_users.append(user_id)
                return known_users

    def count_users(self):
        """Метод для получения количества пользователей"""
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users;")
                return cursor.fetchone()[0]


class UserWords:
    """
    Класс User_Words предназначен для управления связями
    между пользователями и словами в базе данных, включая создание таблицы user_words,
    добавление и удаление слов для конкретного пользователя,
    а также получение слов, сохраненных пользователем.
    """

    def __init__(self, user_db, password_db, name_db):
        self.user = user_db
        self.password = password_db
        self.db_name = name_db

    def connect_to_database(self):
        """Метод для создания подключения к базе данных"""
        return psycopg2.connect(database=self.db_name, user=self.user, password=self.password)

    def create_table_user_words(self):
        """
        Метод для создания таблицы user_words, если она еще не существует,
        с полями user_id и word_id, связанными с таблицами users и words.
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_words (
                user_id BIGINT REFERENCES users(user_id),
                word_id INTEGER REFERENCES words(id),
                PRIMARY KEY (user_id, word_id)
                    );''')

    def add_word(self, user_id, word_id):
        """
        Метод для добавления нового слова в список сохраненных слов пользователя,
        передавая user_id и word_id.
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO user_words (user_id, word_id) VALUES (%s, %s);",
                               (user_id, word_id))
                conn.commit()

    def delete_word(self, user_id, word_id):
        """
        Метод для удаления слова из списка сохраненных слов пользователя,
        передавая user_id и word_id.
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_words WHERE user_id = %s AND word_id = %s;",
                           (user_id, word_id))
                conn.commit()

    def get_user_words(self, user_id):
        """
        Метод для получения случайного слова из списка сохраненных слов пользователя,
        его перевода и списка других случайных слов для создания карточек.
        Возвращает target_word, translate_word, others и target_id.
        Если у пользователя меньше 10 сохраненных слов, возвращает None.
        """
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT word_id FROM user_words WHERE user_id = %s;", (user_id,))
                word_ids = cursor.fetchall()
                word_ids = [row[0] for row in word_ids]
                if not word_ids or self.count_user_words(user_id) < 10:
                    return None, None, None, None
                random_ids = set()
                while len(random_ids) < 4:
                    random_ids.add(random.choice(word_ids))
                cursor.execute("SELECT id, en, ru FROM words WHERE id IN %s", (tuple(random_ids),))
                rows = cursor.fetchall()
                target_word = rows[0][1]
                translate_word = rows[0][2]
                target_id = rows[0][0]
                others = []
                for idx, row in enumerate(rows):
                    if idx != 0:
                        others.append(row[1])
        return target_word, translate_word, others, target_id

    def count_user_words(self, user_id):
        """Метод для получения количества слов конкретного пользователя"""
        with self.connect_to_database() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM user_words WHERE user_id = %s;", (user_id,))
                return cursor.fetchone()[0]


# чтение данных для подключения к БД
user, password, db_name = read_user_data()
# создаем экземпляр класса Words
words = Words(user, password, db_name)
# создаем таблицу words
words.create_table_words()
# word.drop_table_words('user_words')
# word.drop_table_words('users')
# word.drop_table_words('words')
# заполняем таблицу words
words.fill_table_words()
# создаем экземпляр класса Users
users = Users(user, password, db_name)
# создаем таблицу users
users.create_table_users()
# создаем экземпляр класса User_Words
user_words = UserWords(user, password, db_name)
# создаем таблицу user_words
user_words.create_table_user_words()
