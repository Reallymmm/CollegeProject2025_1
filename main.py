import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk
import sqlite3
import datetime
import calendar
import locale
import sys

try:
    if sys.platform.startswith('win'):
        locale.setlocale(locale.LC_TIME, 'Russian')
    else:
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU')
    except locale.Error:
        print("Предупреждение: Не удалось установить русскую локаль.")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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


class DBApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Менеджер Салонной БД")
        self.geometry("1100x800")

        self.conn = self._get_db_connection()
        self.current_entity = None
        self.selected_card = None
        self.card_frames = []

        self.initialize_database()
        insert_sample_data(self.conn)

        self.calendar_date = datetime.date.today()
        self.schedule_date = datetime.date.today()
        self.finance_date = datetime.date.today()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Сайдбар ---
        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar_frame, text="РАЗДЕЛЫ СИСТЕМЫ", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0,
                                                                                                                column=0,
                                                                                                                padx=20,
                                                                                                                pady=(
                                                                                                                    20,
                                                                                                                    10))

        row_counter = 1
        for entity_name in FIXED_ENTITIES:
            btn = ctk.CTkButton(self.sidebar_frame, text=entity_name,
                                command=lambda name=entity_name: self.select_entity(name))
            btn.grid(row=row_counter, column=0, padx=20, pady=5, sticky="ew")
            row_counter += 1

        self.sidebar_frame.grid_rowconfigure(row_counter, weight=1)

        # --- Контент ---
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_rowconfigure(1, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.top_controls = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.top_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.top_controls.grid_columnconfigure((0, 1, 2), weight=1)

        self.scrollable_cards_frame = ctk.CTkScrollableFrame(self.content_frame, label_text="Данные:", label_anchor="w",
                                                             corner_radius=10)
        self.scrollable_cards_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scrollable_cards_frame.grid_columnconfigure(0, weight=1)

        if FIXED_ENTITIES:
            self.select_entity(FIXED_ENTITIES[0])

    def initialize_database(self):
        try:
            for entity, schema in INITIAL_SCHEMAS.items():
                self.conn.execute(f'CREATE TABLE IF NOT EXISTS "{entity}" ({schema})')
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Ошибка инициализации таблиц: {e}")

    def _get_db_connection(self):
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_table_columns(self, entity_name):
        cursor = self.conn.cursor()
        cursor.execute(f'PRAGMA table_info("{entity_name}")')
        return [(col[1], col[2]) for col in cursor.fetchall()]

    def select_entity(self, entity_name):
        self.current_entity = entity_name
        self.selected_card = None
        self._display_entity_data(entity_name)

    def _display_entity_data(self, entity_name):
        for widget in self.top_controls.winfo_children():
            widget.destroy()

        self.top_controls.grid_columnconfigure((0, 1, 2, 3, 4), weight=0)

        if entity_name == "Финансы":
            self._display_finance_report_view()
            return

        elif entity_name == "График работы":
            records = self._get_schedule_data()
            self.scrollable_cards_frame.configure(label_text=f"График работы на месяц")
            self._display_calendar_view(entity_name, records)
            return

        elif entity_name == "Расписание":
            records = self._get_appointment_data(self.schedule_date)
            date_label_text = self.schedule_date.strftime("%d %B %Y").capitalize()
            self.scrollable_cards_frame.configure(
                label_text=f"Расписание на {date_label_text} ({len(records)} записей)")
            self._display_schedule_view(records, self.schedule_date)
            return

        else:
            # Стандартный вид (Карточки)
            self.top_controls.grid_columnconfigure((0, 1, 2), weight=1)
            cursor = self.conn.cursor()
            cursor.execute(f'SELECT * FROM "{entity_name}"')
            records = cursor.fetchall()
            columns = self._get_table_columns(entity_name)

            self._setup_card_controls()  # Настройка кнопок

            self.scrollable_cards_frame.configure(label_text=f"Данные: {entity_name} ({len(records)} записей)")
            self._display_entity_cards(entity_name, records, columns)

        self.title(f"Менеджер Салонной БД - {entity_name}")

    def _setup_card_controls(self):
        # Стандартные кнопки
        ctk.CTkButton(self.top_controls, text="➕ Добавить", command=self.open_add_record_dialog).grid(row=0, column=0,
                                                                                                      padx=5, pady=10,
                                                                                                      sticky="ew")
        ctk.CTkButton(self.top_controls, text="✏️ Изменить", command=self.open_edit_record_dialog,
                      fg_color="#E67E22").grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        ctk.CTkButton(self.top_controls, text="➖ Удалить", command=self.delete_record, fg_color="red").grid(row=0,
                                                                                                            column=2,
                                                                                                            padx=5,
                                                                                                            pady=10,
                                                                                                            sticky="ew")

        # === СПЕЦИАЛЬНЫЕ КНОПКИ ДЛЯ СКЛАДА ===
        if self.current_entity == "Склад":
            # Сброс сетки для вмещения новых кнопок
            self.top_controls.grid_columnconfigure((0, 1, 2), weight=0)
            self.top_controls.grid_columnconfigure(3, weight=2)
            self.top_controls.grid_columnconfigure(4, weight=1)

            ctk.CTkButton(self.top_controls, text="📉 Списать / 📈 Пополнить",
                          command=self._open_stock_transaction_dialog,
                          fg_color="#800080").grid(row=0, column=3, padx=5, pady=10, sticky="ew")

            ctk.CTkButton(self.top_controls, text="📜 История",
                          command=self._show_stock_history,
                          fg_color="#555555").grid(row=0, column=4, padx=5, pady=10, sticky="ew")

    # -----------------------------------------------------------
    # --- ФУНКЦИИ СКЛАДА ---
    # -----------------------------------------------------------
    def _open_stock_transaction_dialog(self):
        if self.selected_card is None:
            messagebox.showwarning("Внимание", "Выберите товар (карточку) на складе.")
            return

        item_id = self.selected_card.record_id

        cursor = self.conn.cursor()
        cursor.execute('SELECT "Название_Товара", "Количество", "Единица_измерения" FROM "Склад" WHERE ID = ?',
                       (item_id,))
        item = cursor.fetchone()
        item_name = item['Название_Товара']
        current_qty = item['Количество']
        unit = item['Единица_измерения']

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Движение товара: {item_name}")
        dialog.geometry("400x350")
        dialog.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dialog, text=f"Товар: {item_name}", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0,
                                                                                                        columnspan=2,
                                                                                                        pady=10)
        ctk.CTkLabel(dialog, text=f"Текущий остаток: {current_qty} {unit}", text_color="gray").grid(row=1, column=0,
                                                                                                    columnspan=2,
                                                                                                    pady=(0, 10))

        ctk.CTkLabel(dialog, text="Тип операции:").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        combo_type = ctk.CTkComboBox(dialog, values=["Расход (Списание)", "Приход (Закупка)"])
        combo_type.set("Расход (Списание)")
        combo_type.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(dialog, text=f"Количество ({unit}):").grid(row=3, column=0, padx=20, pady=10, sticky="w")
        entry_qty = ctk.CTkEntry(dialog)
        entry_qty.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(dialog, text="Причина:").grid(row=4, column=0, padx=20, pady=10, sticky="w")
        entry_reason = ctk.CTkEntry(dialog, placeholder_text="Напр: Стрижка, Клиент X")
        entry_reason.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

        def confirm():
            try:
                qty_val = float(entry_qty.get().replace(',', '.'))
                op_type_raw = combo_type.get()
                reason = entry_reason.get()

                if qty_val <= 0:
                    messagebox.showerror("Ошибка", "Количество должно быть больше нуля.", parent=dialog)
                    return
                if not reason:
                    messagebox.showwarning("Внимание", "Укажите причину.", parent=dialog)
                    return

                is_expense = "Расход" in op_type_raw
                op_type_db = "Расход" if is_expense else "Приход"

                new_qty = current_qty - qty_val if is_expense else current_qty + qty_val

                if new_qty < 0:
                    messagebox.showerror("Ошибка", "Недостаточно товара!", parent=dialog)
                    return

                self.conn.execute('UPDATE "Склад" SET "Количество" = ? WHERE ID = ?', (new_qty, item_id))

                today_str = datetime.date.today().strftime("%Y-%m-%d")
                self.conn.execute(
                    'INSERT INTO "История_Склада" ("ID_Товара", "Дата", "Тип", "Количество", "Причина") VALUES (?, ?, ?, ?, ?)',
                    (item_id, today_str, op_type_db, qty_val, reason)
                )
                self.conn.commit()

                messagebox.showinfo("Успех", f"Новый остаток: {new_qty} {unit}", parent=dialog)
                dialog.destroy()
                self._display_entity_data("Склад")

            except ValueError:
                messagebox.showerror("Ошибка", "Неверное число.", parent=dialog)

        ctk.CTkButton(dialog, text="Выполнить", command=confirm, fg_color="green").grid(row=5, column=0, columnspan=2,
                                                                                        padx=20, pady=20, sticky="ew")

    def _show_stock_history(self):
        history_win = ctk.CTkToplevel(self)
        history_win.title("История склада")
        history_win.geometry("800x500")

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT h.Дата, h.Тип, s.Название_Товара, h.Количество, s.Единица_измерения, h.Причина
            FROM "История_Склада" h
            JOIN "Склад" s ON h.ID_Товара = s.ID
            ORDER BY h.ID DESC
        ''')
        records = cursor.fetchall()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2a2d2e", fieldbackground="#2a2d2e", foreground="white", rowheight=25)
        style.configure("Treeview.Heading", background="#3A8FCD", foreground="white")

        tree = ttk.Treeview(history_win, columns=("Дата", "Тип", "Товар", "Кол", "Ед", "Причина"), show="headings")
        tree.heading("Дата", text="Дата");
        tree.column("Дата", width=90)
        tree.heading("Тип", text="Тип");
        tree.column("Тип", width=80)
        tree.heading("Товар", text="Товар");
        tree.column("Товар", width=200)
        tree.heading("Кол", text="Кол-во");
        tree.column("Кол", width=60)
        tree.heading("Ед", text="Ед.");
        tree.column("Ед", width=50)
        tree.heading("Причина", text="Причина");
        tree.column("Причина", width=200)

        for row in records:
            tree.insert("", "end", values=list(row))

        tree.pack(fill="both", expand=True, padx=10, pady=10)

    # -----------------------------------------------------------
    # --- ФИНАНСЫ И КАЛЕНДАРЬ ---
    # -----------------------------------------------------------

    def _get_monthly_finance_data(self, target_date):
        year, month = target_date.year, target_date.month
        start_date = datetime.date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime.date(year, month, last_day)

        cursor = self.conn.cursor()
        cursor.execute("""SELECT SUM(Сумма) FROM "Финансы" WHERE Тип = 'Доход' AND Дата BETWEEN ? AND ?""",
                       (str(start_date), str(end_date)))
        total_income = cursor.fetchone()[0] or 0.0
        cursor.execute("""SELECT SUM(Сумма) FROM "Финансы" WHERE Тип = 'Расход' AND Дата BETWEEN ? AND ?""",
                       (str(start_date), str(end_date)))
        total_expense = cursor.fetchone()[0] or 0.0
        cursor.execute("""SELECT * FROM "Финансы" WHERE Дата BETWEEN ? AND ? ORDER BY Дата DESC, ID DESC""",
                       (str(start_date), str(end_date)))
        transactions = cursor.fetchall()

        return {"total_income": total_income, "total_expense": total_expense, "profit": total_income - total_expense,
                "transactions": transactions}

    def change_finance_month(self, delta):
        current_year = self.finance_date.year
        current_month = self.finance_date.month
        new_month = (current_month - 1 + delta) % 12 + 1
        new_year = current_year + (current_month - 1 + delta) // 12
        self.finance_date = datetime.date(new_year, new_month, 1)
        self._display_entity_data("Финансы")

    def _open_add_finance_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить финансовую операцию")
        dialog.geometry("400x350")
        dialog.grid_columnconfigure(1, weight=1)

        fields = {
            "Тип": ctk.CTkComboBox(dialog, values=["Доход", "Расход"]),
            "Сумма": ctk.CTkEntry(dialog, placeholder_text="Например, 1500.50"),
            "Дата": ctk.CTkEntry(dialog),
            "Описание": ctk.CTkEntry(dialog, placeholder_text="Например, Стрижка или Аренда")
        }
        fields["Тип"].set("Доход")
        fields["Дата"].insert(0, datetime.date.today().strftime('%Y-%m-%d'))

        for i, (label, widget) in enumerate(fields.items()):
            ctk.CTkLabel(dialog, text=f"{label}:").grid(row=i, column=0, padx=10, pady=10, sticky="w")
            widget.grid(row=i, column=1, padx=10, pady=10, sticky="ew")

        def save_finance_record():
            tip = fields["Тип"].get()
            summa_str = fields["Сумма"].get()
            data_str = fields["Дата"].get()
            opisanie = fields["Описание"].get()

            if not all([tip, summa_str, data_str, opisanie]):
                messagebox.showwarning("Предупреждение", "Заполните все поля.", parent=dialog)
                return
            try:
                summa = float(summa_str.replace(',', '.'))
                self.conn.execute('INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                                  (tip, summa, data_str, opisanie))
                self.conn.commit()
                messagebox.showinfo("Успех", "Добавлено.", parent=dialog)
                dialog.destroy()
                self._display_entity_data("Финансы")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e), parent=dialog)

        ctk.CTkButton(dialog, text="Сохранить", command=save_finance_record, fg_color="green").grid(row=4, columnspan=2,
                                                                                                    pady=20,
                                                                                                    sticky="ew")

    def _display_finance_report_view(self):
        self.top_controls.grid_columnconfigure((0, 1, 2, 3), weight=0)
        self.top_controls.grid_columnconfigure(0, weight=1)
        self.top_controls.grid_columnconfigure(1, weight=2)
        self.top_controls.grid_columnconfigure(2, weight=1)
        self.top_controls.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(self.top_controls, text="< Пред.", command=lambda: self.change_finance_month(-1)).grid(row=0,
                                                                                                             column=0,
                                                                                                             padx=5,
                                                                                                             sticky="w")
        month_name = self.finance_date.strftime("%B %Y").capitalize()
        ctk.CTkLabel(self.top_controls, text=month_name, font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=1,
                                                                                                        sticky="ew")
        ctk.CTkButton(self.top_controls, text="След. >", command=lambda: self.change_finance_month(1)).grid(row=0,
                                                                                                            column=3,
                                                                                                            padx=5,
                                                                                                            sticky="e")
        ctk.CTkButton(self.top_controls, text="➕ Добавить", fg_color="green",
                      command=self._open_add_finance_dialog).grid(row=0, column=2, padx=5, sticky="ew")

        finance_data = self._get_monthly_finance_data(self.finance_date)
        for widget in self.scrollable_cards_frame.winfo_children(): widget.destroy()
        self.scrollable_cards_frame.configure(label_text=f"Финансы ({len(finance_data['transactions'])} операций)")

        summary_frame = ctk.CTkFrame(self.scrollable_cards_frame, fg_color="transparent")
        summary_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        summary_frame.grid_columnconfigure((0, 1, 2), weight=1)

        def create_sum_box(col, title, val, color):
            fr = ctk.CTkFrame(summary_frame, border_width=2, border_color=color)
            fr.grid(row=0, column=col, padx=5, sticky="nsew")
            ctk.CTkLabel(fr, text=title, text_color="#A9A9A9").pack(pady=(5, 0))
            ctk.CTkLabel(fr, text=f"{val:,.2f}", font=("Arial", 20, "bold"), text_color=color).pack(pady=(0, 5))

        create_sum_box(0, "ДОХОД", finance_data['total_income'], "#32CD32")
        create_sum_box(1, "РАСХОД", finance_data['total_expense'], "#C00000")
        create_sum_box(2, "ПРИБЫЛЬ", finance_data['profit'], "#32CD32" if finance_data['profit'] >= 0 else "#FF4500")

        for i, trans in enumerate(finance_data['transactions']):
            fr = ctk.CTkFrame(self.scrollable_cards_frame)
            fr.grid(row=i + 2, column=0, sticky="ew", padx=10, pady=2)
            ctk.CTkLabel(fr, text=trans['Дата']).pack(side="left", padx=10)
            color = "#32CD32" if trans['Тип'] == 'Доход' else "#FF4500"
            ctk.CTkLabel(fr, text=f"{trans['Сумма']:,.2f}", text_color=color).pack(side="left", padx=10)
            ctk.CTkLabel(fr, text=trans['Описание']).pack(side="left", padx=10)

    def delete_record(self):
        if self.selected_card is None:
            messagebox.showwarning("Предупреждение", "Выберите карточку.")
            return
        if self.current_entity in ["График работы", "Расписание", "Финансы"]:
            messagebox.showwarning("Предупреждение", "Удаление здесь не поддерживается.")
            return
        if messagebox.askyesno("Подтверждение", "Удалить запись?"):
            self.conn.execute(f'DELETE FROM "{self.current_entity}" WHERE ID = ?', (self.selected_card.record_id,))
            self.conn.commit()
            self._display_entity_data(self.current_entity)

    def open_edit_record_dialog(self):
        if self.selected_card is None:
            messagebox.showwarning("Предупреждение", "Выберите карточку.")
            return
        if self.current_entity in ["График работы", "Расписание", "Финансы"]:
            messagebox.showwarning("Предупреждение", "Редактирование здесь не поддерживается.")
            return

        record_id = self.selected_card.record_id
        entity_name = self.current_entity
        columns = self._get_table_columns(entity_name)
        data_columns = [(name, type_) for name, type_ in columns if name.upper() != 'ID']

        cursor = self.conn.cursor()
        cursor.execute(f'SELECT * FROM "{entity_name}" WHERE ID = ?', (record_id,))
        record = cursor.fetchone()

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Изменить #{record_id}")
        entries = {}
        for i, (name, _) in enumerate(data_columns):
            ctk.CTkLabel(dialog, text=name).grid(row=i, column=0, padx=10, pady=5)
            e = ctk.CTkEntry(dialog)
            e.insert(0, str(record[name]))
            e.grid(row=i, column=1, padx=10, pady=5)
            entries[name] = e

        def save():
            updates = []
            vals = []
            for name, _ in data_columns:
                updates.append(f'"{name}" = ?')
                vals.append(entries[name].get())
            vals.append(record_id)
            self.conn.execute(f'UPDATE "{entity_name}" SET {", ".join(updates)} WHERE ID=?', vals)
            self.conn.commit()
            dialog.destroy()
            self._display_entity_data(entity_name)

        ctk.CTkButton(dialog, text="Сохранить", command=save).grid(row=len(data_columns), columnspan=2, pady=10)

    def _get_employee_map(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT "ID", "Имя" FROM "Сотрудники"')
        employees = cursor.fetchall()
        return {row['Имя']: row['ID'] for row in employees}, {row['ID']: row['Имя'] for row in employees}

    def open_add_record_dialog(self):
        if self.current_entity == "График работы":
            self._open_add_schedule_dialog()
            return
        if self.current_entity == "Финансы":
            self._open_add_finance_dialog()
            return
        if self.current_entity == "Расписание":
            messagebox.showwarning("!", "Добавляйте через 'Записи'.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Добавить: {self.current_entity}")
        columns = [(c[0], c[1]) for c in self._get_table_columns(self.current_entity) if c[0] != 'ID']
        entries = []
        for i, (name, _) in enumerate(columns):
            ctk.CTkLabel(dialog, text=name).grid(row=i, column=0, padx=10, pady=5)
            e = ctk.CTkEntry(dialog)
            e.grid(row=i, column=1, padx=10, pady=5)
            entries.append(e)

        def save():
            vals = [e.get() for e in entries]
            cols = ", ".join([f'"{c[0]}"' for c in columns])
            qs = ", ".join(["?"] * len(columns))
            self.conn.execute(f'INSERT INTO "{self.current_entity}" ({cols}) VALUES ({qs})', vals)
            self.conn.commit()
            dialog.destroy()
            self._display_entity_data(self.current_entity)

        ctk.CTkButton(dialog, text="Сохранить", command=save).grid(row=len(columns), columnspan=2, pady=10)

    def _open_add_schedule_dialog(self):
        name_to_id, _ = self._get_employee_map()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Смена")
        ctk.CTkLabel(dialog, text="Сотрудник").pack()
        combo = ctk.CTkComboBox(dialog, values=list(name_to_id.keys()))
        combo.pack()
        ctk.CTkLabel(dialog, text="Дата (YYYY-MM-DD)").pack()
        e_date = ctk.CTkEntry(dialog);
        e_date.insert(0, str(datetime.date.today()));
        e_date.pack()
        ctk.CTkLabel(dialog, text="Начало").pack()
        e_start = ctk.CTkEntry(dialog);
        e_start.insert(0, "09:00");
        e_start.pack()
        ctk.CTkLabel(dialog, text="Конец").pack()
        e_end = ctk.CTkEntry(dialog);
        e_end.insert(0, "18:00");
        e_end.pack()

        def save():
            eid = name_to_id.get(combo.get())
            self.conn.execute(
                'INSERT INTO "График работы" ("ID_Сотрудника", "Дата", "Время_Начала", "Время_Конца") VALUES (?,?,?,?)',
                (eid, e_date.get(), e_start.get(), e_end.get()))
            self.conn.commit()
            dialog.destroy()
            self._display_entity_data("График работы")

        ctk.CTkButton(dialog, text="ОК", command=save).pack(pady=10)

    def _get_schedule_data(self):
        _, id_to_name = self._get_employee_map()
        start = self.calendar_date.replace(day=1)
        _, last = calendar.monthrange(start.year, start.month)
        end = start.replace(day=last)
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM "График работы" WHERE Дата BETWEEN ? AND ?', (str(start), str(end)))
        data = {}
        for r in cur.fetchall():
            s = f"{id_to_name.get(r['ID_Сотрудника'], '?')}: {r['Время_Начала']}-{r['Время_Конца']}"
            data.setdefault(r['Дата'], []).append(s)
        return data

    def change_calendar_month(self, d):
        m = (self.calendar_date.month - 1 + d) % 12 + 1
        y = self.calendar_date.year + (self.calendar_date.month - 1 + d) // 12
        self.calendar_date = datetime.date(y, m, 1)
        self._display_entity_data("График работы")

    def _display_calendar_view(self, entity_name, schedule_data):
        for w in self.top_controls.winfo_children(): w.destroy()
        self.top_controls.grid_columnconfigure(0, weight=1);
        self.top_controls.grid_columnconfigure(1, weight=2);
        self.top_controls.grid_columnconfigure(3, weight=1)
        ctk.CTkButton(self.top_controls, text="<", command=lambda: self.change_calendar_month(-1)).grid(row=0, column=0)
        ctk.CTkLabel(self.top_controls, text=self.calendar_date.strftime("%B %Y"), font=("Arial", 18, "bold")).grid(
            row=0, column=1)
        ctk.CTkButton(self.top_controls, text=">", command=lambda: self.change_calendar_month(1)).grid(row=0, column=3)
        ctk.CTkButton(self.top_controls, text="➕ Смена", command=self._open_add_schedule_dialog).grid(row=0, column=2)

        for w in self.scrollable_cards_frame.winfo_children(): w.destroy()
        cal_fr = ctk.CTkFrame(self.scrollable_cards_frame)
        cal_fr.pack(fill="both", expand=True)
        for i in range(7): cal_fr.columnconfigure(i, weight=1)
        cal = calendar.monthcalendar(self.calendar_date.year, self.calendar_date.month)
        for r, week in enumerate(cal):
            for c, d in enumerate(week):
                if d == 0: continue
                cell = ctk.CTkFrame(cal_fr, border_width=1)
                cell.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                ctk.CTkLabel(cell, text=str(d), font=("Arial", 12, "bold")).pack(anchor="nw")
                ds = str(datetime.date(self.calendar_date.year, self.calendar_date.month, d))
                if ds in schedule_data:
                    for shift in schedule_data[ds]: ctk.CTkLabel(cell, text=shift, font=("Arial", 10)).pack()

    def change_schedule_date(self, delta):
        self.schedule_date += datetime.timedelta(days=delta)
        self._display_entity_data("Расписание")

    def _get_appointment_data(self, date):
        _, id_to_name_emp = self._get_employee_map()
        cur = self.conn.cursor()
        cur.execute('SELECT ID, Имя FROM "Клиенты"')
        cl_map = {r['ID']: r['Имя'] for r in cur.fetchall()}
        cur.execute('SELECT * FROM "Записи" WHERE Дата=? ORDER BY Время', (str(date),))
        return [{'time': r['Время'],
                 'details': f"Кл: {cl_map.get(r['ID_Клиента'], '?')}, Сотр: {id_to_name_emp.get(r['ID_Сотрудника'], '?')}",
                 'id': r['ID']} for r in cur.fetchall()]

    def _display_schedule_view(self, appointments, date):
        for w in self.top_controls.winfo_children(): w.destroy()
        self.top_controls.grid_columnconfigure(0, weight=1);
        self.top_controls.grid_columnconfigure(1, weight=2);
        self.top_controls.grid_columnconfigure(2, weight=1)
        ctk.CTkButton(self.top_controls, text="<", command=lambda: self.change_schedule_date(-1)).grid(row=0, column=0)
        ctk.CTkLabel(self.top_controls, text=date.strftime("%d %B %Y"), font=("Arial", 18)).grid(row=0, column=1)
        ctk.CTkButton(self.top_controls, text=">", command=lambda: self.change_schedule_date(1)).grid(row=0, column=2)

        for w in self.scrollable_cards_frame.winfo_children(): w.destroy()
        sch_fr = ctk.CTkFrame(self.scrollable_cards_frame)
        sch_fr.pack(fill="both", expand=True)
        sch_fr.columnconfigure(1, weight=1)
        for i, h in enumerate(range(9, 19)):
            ts = f"{h:02d}:00"
            ctk.CTkLabel(sch_fr, text=ts).grid(row=i, column=0, padx=10)
            slot = ctk.CTkFrame(sch_fr, height=40, border_width=1)
            slot.grid(row=i, column=1, sticky="ew", pady=1)
            for app in appointments:
                if app['time'].startswith(f"{h:02d}"):
                    ctk.CTkLabel(slot, text=f"[{app['time']}] {app['details']}", fg_color="#3A8FCD").pack(fill="x",
                                                                                                          pady=1)

    def _display_entity_cards(self, entity_name, records, columns):
        for widget in self.scrollable_cards_frame.winfo_children():
            widget.destroy()
        self.card_frames = []
        self.scrollable_cards_frame.grid_columnconfigure((0, 1, 2), weight=1)
        column_names = [name for name, _ in columns]

        for index, record in enumerate(records):
            row, col = index // 3, index % 3
            card = ctk.CTkFrame(self.scrollable_cards_frame, width=300, height=200, corner_radius=10,
                                fg_color=('#2a2d2e', '#212121'), border_width=2)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            card.record_id = record['ID']
            card.bind("<Button-1>", lambda event, card=card: self._select_card(card))
            self.card_frames.append(card)
            card.grid_columnconfigure(1, weight=1)

            # Заголовок
            header_text = f"#{record['ID']}"
            if len(column_names) > 1:
                header_text += f" - {record[column_names[1]]}"

            header_frame = ctk.CTkFrame(card, fg_color="#3A8FCD")
            header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            header_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(header_frame, text=header_text, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0,
                                                                                                        padx=10, pady=5,
                                                                                                        sticky="w")

            data_rows = 1
            for name in column_names:
                if name.upper() == 'ID': continue

                value = str(record[name])
                display_label = name

                # Замена ID на Имена в Записях
                if entity_name == "Записи":
                    if name == 'ID_Сотрудника':
                        display_label = "Сотрудник"
                        _, id_to_name_emp = self._get_employee_map()
                        value = id_to_name_emp.get(record[name], 'Неизвестно')
                    elif name == 'ID_Клиента':
                        display_label = "Клиент"
                        cursor = self.conn.cursor()
                        cursor.execute('SELECT "Имя" FROM "Клиенты" WHERE ID = ?', (record[name],))
                        client_row = cursor.fetchone()
                        value = client_row['Имя'] if client_row else 'Неизвестно'

                # Цвет текста для склада (Мало товара = Красный)
                text_color = "white"
                if entity_name == "Склад" and name == "Количество":
                    try:
                        if float(value) < 5:
                            text_color = "#FF5555"
                        else:
                            text_color = "#55FF55"
                    except:
                        pass

                ctk.CTkLabel(card, text=f"{display_label}:", text_color="#aaaaaa").grid(row=data_rows, column=0,
                                                                                        padx=(10, 5), pady=2,
                                                                                        sticky="w")
                ctk.CTkLabel(card, text=value, font=ctk.CTkFont(weight="bold"), text_color=text_color).grid(
                    row=data_rows, column=1, padx=(5, 10), pady=2, sticky="w")
                data_rows += 1
                if data_rows >= 6: break

    def _select_card(self, card):
        for c in self.card_frames:
            c.configure(border_color=('#2a2d2e', '#212121'))
        card.configure(border_color=('#3A8FCD', '#3A8FCD'))
        self.selected_card = card


if __name__ == "__main__":
    app = DBApp()
    app.mainloop()