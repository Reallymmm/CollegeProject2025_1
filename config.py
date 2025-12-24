import locale
import sys

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
    "Сотрудники": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Имя TEXT, Телефон TEXT",
    "Услуги": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Название TEXT, Цена REAL, Длительность INTEGER",
    "Клиенты": "ID INTEGER PRIMARY KEY AUTOINCREMENT, ФИО TEXT, Телефон TEXT",
    "Записи": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Дата TEXT, Время TEXT, ID_Клиента INTEGER, ID_Сотрудника INTEGER, ID_Услуги INTEGER",
    "График работы": "ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Сотрудника INTEGER, Дата TEXT, Время_Начала TEXT, Время_Конца TEXT",
    "Финансы": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Тип TEXT, Сумма REAL, Дата TEXT, Описание TEXT",
    "Склад": "ID INTEGER PRIMARY KEY AUTOINCREMENT, Название_Товара TEXT, Количество REAL, Единица_измерения TEXT, Цена_за_единицу REAL",
    "История_Склада": "ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Товара INTEGER, Дата TEXT, Тип TEXT, Количество REAL, Причина TEXT",
    "Расход_Материалов": "ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Услуги INTEGER, ID_Материала INTEGER, Количество REAL",
    "Сотрудник_Услуги": "ID INTEGER PRIMARY KEY AUTOINCREMENT, ID_Сотрудника INTEGER, ID_Услуги INTEGER"
}