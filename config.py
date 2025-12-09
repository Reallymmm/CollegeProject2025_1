import locale
import sys

# Настройка локали
if sys.platform.startswith('win'):
    locale.setlocale(locale.LC_TIME, 'Russian')
else:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

DATABASE_NAME = "salon_db.sqlite"

FIXED_ENTITIES = [
    "Финансы",
    "Расписание",
    "График работы",
    "Записи",
    "Сотрудники",
    "Услуги",
    "Клиенты",
    "Склад"
]

INITIAL_SCHEMAS = {
    "Сотрудники": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Имя TEXT, Должность TEXT, Телефон TEXT",
    "Услуги": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Название TEXT, Цена REAL, Длительность INTEGER",
    "Клиенты": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Имя TEXT, Телефон TEXT, Email TEXT",
    "Записи": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Дата TEXT, Время TEXT, ID_Клиента INTEGER, ID_Сотрудника INTEGER",
    "График работы": "ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Сотрудника INTEGER, Дата TEXT, Время_Начала TEXT, Время_Конца TEXT",
    "Финансы": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Тип TEXT, Сумма REAL, Дата TEXT, Описание TEXT",
    "Склад": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Название_Товара TEXT, Количество REAL, Единица_измерения TEXT",
    "История_Склада": "ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Товара INTEGER, Дата TEXT, Тип TEXT, Количество REAL, Причина TEXT"
}

