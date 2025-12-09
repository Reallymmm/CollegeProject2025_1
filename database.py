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
        conn.commit()
    except sqlite3.Error as e:
        from tkinter import messagebox
        messagebox.showerror("Ошибка БД", f"Ошибка инициализации таблиц: {e}")


def insert_sample_data(conn):
    try:
        cursor = conn.cursor()
        today = datetime.date.today()
        current_month_day1 = today.strftime('%Y-%m-01')
        yesterday_str = (today - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        # 1. Сотрудники
        cursor.execute('SELECT COUNT(*) FROM "Сотрудники"')
        if cursor.fetchone()[0] == 0:
            conn.execute('INSERT INTO "Сотрудники" ("Имя", "Должность", "Телефон") VALUES (?, ?, ?)',
                         ('Иванов И.И.', 'Менеджер', '555-0001'))
            conn.execute('INSERT INTO "Сотрудники" ("Имя", "Должность", "Телефон") VALUES (?, ?, ?)',
                         ('Петрова А.В.', 'Стилист', '555-0002'))

        # 2. Клиенты
        cursor.execute('SELECT COUNT(*) FROM "Клиенты"')
        if cursor.fetchone()[0] == 0:
            conn.execute('INSERT INTO "Клиенты" ("Имя", "Телефон", "Email") VALUES (?, ?, ?)',
                         ('Ольга С.', '777-1111', 'o.s@mail.ru'))
            conn.execute('INSERT INTO "Клиенты" ("Имя", "Телефон", "Email") VALUES (?, ?, ?)',
                         ('Николай П.', '777-2222', 'n.p@mail.ru'))
            conn.execute('INSERT INTO "Клиенты" ("Имя", "Телефон", "Email") VALUES (?, ?, ?)',
                         ('Анна К.', '777-3333', 'a.k@mail.ru'))

        # 3. График работы
        cursor.execute('SELECT COUNT(*) FROM "График работы"')
        if cursor.fetchone()[0] == 0:
            conn.execute(
                'INSERT INTO "График работы" ("ID_Сотрудника", "Дата", "Время_Начала", "Время_Конца") VALUES (?, ?, ?, ?)',
                (1, str(today), '09:00', '18:00'))
            conn.execute(
                'INSERT INTO "График работы" ("ID_Сотрудника", "Дата", "Время_Начала", "Время_Конца") VALUES (?, ?, ?, ?)',
                (2, str(today + datetime.timedelta(days=1)), '10:00', '19:00'))

        # 4. Записи
        cursor.execute('SELECT COUNT(*) FROM "Записи"')
        if cursor.fetchone()[0] == 0:
            today_str = str(datetime.date.today())
            conn.execute('INSERT INTO "Записи" ("Дата", "Время", "ID_Клиента", "ID_Сотрудника") VALUES (?, ?, ?, ?)',
                         (today_str, '10:00', 1, 2))
            conn.execute('INSERT INTO "Записи" ("Дата", "Время", "ID_Клиента", "ID_Сотрудника") VALUES (?, ?, ?, ?)',
                         (today_str, '11:30', 2, 1))

        # 5. Финансы
        cursor.execute('SELECT COUNT(*) FROM "Финансы"')
        if cursor.fetchone()[0] == 0:
            conn.execute('INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                         ('Доход', 2500.00, today.strftime('%Y-%m-%d'), 'Стрижка и укладка (Ольга С.)'))
            conn.execute('INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                         ('Расход', 35000.00, current_month_day1, 'Арендная плата за месяц'))

        # 6. Склад (Пример)
        cursor.execute('SELECT COUNT(*) FROM "Склад"')
        if cursor.fetchone()[0] == 0:
            conn.execute('INSERT INTO "Склад" ("Название_Товара", "Количество", "Единица_измерения") VALUES (?, ?, ?)',
                         ('Шампунь Pro', 10, 'литр'))
            conn.execute('INSERT INTO "Склад" ("Название_Товара", "Количество", "Единица_измерения") VALUES (?, ?, ?)',
                         ('Полотенца', 4, 'упаковка'))

        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при вставке тестовых данных: {e}")

