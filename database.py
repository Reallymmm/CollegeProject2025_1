import sqlite3
import datetime
from config import DATABASE_NAME, INITIAL_SCHEMAS


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(conn):
    try:
        for entity, schema in INITIAL_SCHEMAS.items():
            conn.execute(f'CREATE TABLE IF NOT EXISTS "{entity}" ({schema})')

        try:
            cursor = conn.cursor()
            cursor.execute('PRAGMA table_info("Клиенты")')
            columns = [col[1] for col in cursor.fetchall()]

            if 'Имя' in columns and 'ФИО' not in columns:
                conn.execute('CREATE TABLE "Клиенты_new" (ID INTEGER PRIMARY KEY AUTOINCREMENT, ФИО TEXT, Телефон TEXT)')
                cursor.execute('SELECT ID, Имя, Телефон FROM "Клиенты"')
                rows = cursor.fetchall()
                for r in rows:
                    conn.execute('INSERT INTO "Клиенты_new" (ID, ФИО, Телефон) VALUES (?, ?, ?)', 
                                (r['ID'], r['Имя'], r['Телефон']))
                conn.execute('DROP TABLE "Клиенты"')
                conn.execute('ALTER TABLE "Клиенты_new" RENAME TO "Клиенты"')
        except sqlite3.Error as e:
            print(f"Ошибка миграции таблицы Клиенты: {e}")

        try:
            cursor = conn.cursor()
            cursor.execute('PRAGMA table_info("Записи")')
            columns = [col[1] for col in cursor.fetchall()]
            if 'ID_Услуги' not in columns:
                conn.execute('ALTER TABLE "Записи" ADD COLUMN "ID_Услуги" INTEGER')
        except sqlite3.Error:
            pass
        try:
            cursor.execute('PRAGMA table_info("Склад")')
            columns = [col[1] for col in cursor.fetchall()]
            if 'Цена_за_единицу' not in columns:
                conn.execute('ALTER TABLE "Склад" ADD COLUMN "Цена_за_единицу" REAL')
        except sqlite3.Error:
            pass

        try:
            conn.execute(
                'CREATE TABLE IF NOT EXISTS "Запись_Услуги" ('
                'ID INTEGER PRIMARY KEY AUTOINCREMENT, '
                '"ID_Записи" INTEGER, '
                '"ID_Услуги" INTEGER)'
            )
        except sqlite3.Error as e:
            print(f"Ошибка создания таблицы Запись_Услуги: {e}")

        conn.commit()
    except sqlite3.Error as e:
        from tkinter import messagebox
        messagebox.showerror("Ошибка БД", f"Ошибка инициализации таблиц: {e}")