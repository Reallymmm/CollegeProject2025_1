import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
import datetime
import calendar
from datetime import timedelta

def time_str_to_minutes(time_str: str) -> int:
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except Exception:
        return 0


def minutes_to_time_str(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def get_appointment_duration(conn, appointment_id, default_service_id=None) -> int:

    cur = conn.cursor()

    cur.execute(
        'SELECT u."Длительность" FROM "Запись_Услуги" zu '
        'JOIN "Услуги" u ON zu."ID_Услуги" = u.ID '
        'WHERE zu."ID_Записи" = ?',
        (appointment_id,)
    )
    rows = cur.fetchall()
    durations = [int(r["Длительность"]) for r in rows if r["Длительность"]]

    if not durations and default_service_id:
        cur.execute(
            'SELECT "Длительность" FROM "Услуги" WHERE ID = ?',
            (default_service_id,)
        )
        r = cur.fetchone()
        if r and r["Длительность"]:
            durations = [int(r["Длительность"])]

    if not durations:
        return 30

    return sum(durations)

def center_dialog(parent, dialog):
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (dialog.winfo_reqwidth() // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (dialog.winfo_reqheight() // 2)
    dialog.geometry(f"+{x}+{y}")

def open_stock_transaction_dialog(app):
    """Диалог для движения товара на складе"""
    if app.selected_card is None:
        messagebox.showwarning("Внимание", "Выберите товар (карточку) на складе.")
        return

    item_id = app.selected_card.record_id

    cursor = app.conn.cursor()
    cursor.execute('SELECT "Название_Товара", "Количество", "Единица_измерения", "Цена_за_единицу" '
                   'FROM "Склад" WHERE ID = ?', (item_id,))
    item = cursor.fetchone()
    if not item:
        messagebox.showerror("Ошибка", "Товар не найден.", parent=app)
        return

    item_name = item['Название_Товара']
    current_qty = item['Количество']
    unit = item['Единица_измерения']
    item_price = item['Цена_за_единицу'] if item['Цена_за_единицу'] else 0

    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Движение товара: {item_name}")
    dialog.geometry("450x450")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(dialog, text=f"Товар: {item_name}",
                 font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0,
                                                                columnspan=2, pady=10)
    ctk.CTkLabel(dialog, text=f"Текущий остаток: {current_qty} {unit}",
                 text_color="gray").grid(row=1, column=0, columnspan=2, pady=(0, 10))

    ctk.CTkLabel(dialog, text="Тип операции:").grid(row=2, column=0, padx=20, pady=10, sticky="w")
    combo_type = ctk.CTkComboBox(dialog, values=["Расход (Списание)", "Приход (Закупка)"])
    combo_type.set("Расход (Списание)")
    combo_type.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

    ctk.CTkLabel(dialog, text=f"Количество ({unit}):").grid(row=3, column=0, padx=20, pady=10, sticky="w")
    entry_qty = ctk.CTkEntry(dialog)
    entry_qty.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

    price_label = ctk.CTkLabel(dialog, text="Цена за единицу (для прихода):")
    entry_price = ctk.CTkEntry(dialog,
                               placeholder_text=f"Текущая цена: {item_price:.2f}" if item_price else "Укажите цену")
    if item_price:
        entry_price.insert(0, str(item_price))

    reason_label = ctk.CTkLabel(dialog, text="Причина:")
    reason_label.grid(row=4, column=0, padx=20, pady=10, sticky="w")
    entry_reason = ctk.CTkEntry(dialog, placeholder_text="Напр: Стрижка, Клиент X")
    entry_reason.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

    def on_type_change(*_):
        is_income = "Приход" in combo_type.get()
        if is_income:
            price_label.grid(row=4, column=0, padx=20, pady=10, sticky="w")
            entry_price.grid(row=4, column=1, padx=20, pady=10, sticky="ew")
            reason_label.grid_configure(row=5, column=0)
            entry_reason.grid_configure(row=5, column=1)
            confirm_btn.grid_configure(row=6)
        else:
            price_label.grid_remove()
            entry_price.grid_remove()
            reason_label.grid_configure(row=4, column=0)
            entry_reason.grid_configure(row=4, column=1)
            confirm_btn.grid_configure(row=5)

    combo_type.bind("<<ComboboxSelected>>", on_type_change)

    def confirm():
        cursor = app.conn.cursor()
        try:
            qty_val = float(entry_qty.get().replace(',', '.'))
            op_type_raw = combo_type.get()
            reason = entry_reason.get().strip()

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

            price_to_use = item_price
            if not is_expense:
                price_str = entry_price.get().strip()
                if not price_str:
                    messagebox.showerror("Ошибка", "Укажите цену за единицу для прихода.", parent=dialog)
                    return
                try:
                    price_to_use = float(price_str.replace(',', '.'))
                    if price_to_use < 0:
                        messagebox.showerror("Ошибка", "Цена не может быть отрицательной.", parent=dialog)
                        return
                except ValueError:
                    messagebox.showerror("Ошибка", "Неверный формат цены.", parent=dialog)
                    return

                cursor.execute('UPDATE "Склад" SET "Цена_за_единицу"=? WHERE ID=?',
                               (price_to_use, item_id))

                total_cost = qty_val * price_to_use
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                cursor.execute(
                    'INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                    ('Расход', total_cost, today_str,
                     f'Закупка: {item_name} ({qty_val} {unit}) - {reason}')
                )

            cursor.execute('UPDATE "Склад" SET "Количество"=? WHERE ID=?', (new_qty, item_id))

            today_str = datetime.date.today().strftime("%Y-%m-%d")
            reason_with_price = reason if is_expense else f"{reason} (Цена: {price_to_use:.2f} за {unit})"
            cursor.execute(
                'INSERT INTO "История_Склада" ("ID_Товара", "Дата", "Тип", "Количество", "Причина") '
                'VALUES (?, ?, ?, ?, ?)',
                (item_id, today_str, op_type_db, qty_val, reason_with_price)
            )

            app.conn.commit()

            msg = f"Новый остаток: {new_qty} {unit}"
            if not is_expense:
                msg += f"\nСоздан расход в финансах: {qty_val * price_to_use:.2f} руб."
            messagebox.showinfo("Успех", msg, parent=dialog)
            dialog.destroy()
            app._display_entity_data("Склад")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверное число.", parent=dialog)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}", parent=dialog)

    confirm_btn = ctk.CTkButton(dialog, text="Выполнить", command=confirm, fg_color="green")
    confirm_btn.grid(row=5, column=0, columnspan=2, padx=20, pady=20, sticky="ew")


def show_stock_history(app):
    """Показать историю склада"""
    history_win = ctk.CTkToplevel(app)
    history_win.title("История склада")
    history_win.geometry("800x500")
    center_dialog(app, history_win)
    history_win.transient(app)
    history_win.grab_set()

    cursor = app.conn.cursor()
    cursor.execute('''
        SELECT h.Дата, h.Тип, s.Название_Товара, h.Количество, s.Единица_измерения, h.Причина
        FROM "История_Склада" h
        JOIN "Склад" s ON h.ID_Товара = s.ID
        ORDER BY h.ID DESC
    ''')
    records = cursor.fetchall()

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#2a2d2e",
                    fieldbackground="#2a2d2e", foreground="white", rowheight=25)
    style.configure("Treeview.Heading", background="#3A8FCD", foreground="white")

    tree = ttk.Treeview(history_win,
                        columns=("Дата", "Тип", "Товар", "Кол", "Ед", "Причина"),
                        show="headings")
    tree.heading("Дата", text="Дата")
    tree.column("Дата", width=90)
    tree.heading("Тип", text="Тип")
    tree.column("Тип", width=80)
    tree.heading("Товар", text="Товар")
    tree.column("Товар", width=200)
    tree.heading("Кол", text="Кол-во")
    tree.column("Кол", width=60)
    tree.heading("Ед", text="Ед.")
    tree.column("Ед", width=50)
    tree.heading("Причина", text="Причина")
    tree.column("Причина", width=200)

    for row in records:
        tree.insert("", "end", values=list(row))

    tree.pack(fill="both", expand=True, padx=10, pady=10)


def open_add_stock_dialog(app):
    """Диалог добавления материала на склад с ценой"""
    dialog = ctk.CTkToplevel(app)
    dialog.title("Добавить: Материал на склад")
    dialog.geometry("450x300")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    row = 0

    ctk.CTkLabel(dialog, text="Название товара:").grid(
        row=row, column=0, padx=10, pady=10, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Количество:").grid(
        row=row, column=0, padx=10, pady=10, sticky="w")
    entry_qty = ctk.CTkEntry(dialog)
    entry_qty.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Единица измерения:").grid(
        row=row, column=0, padx=10, pady=10, sticky="w")
    entry_unit = ctk.CTkEntry(dialog, placeholder_text="шт, литр, кг, упаковка и т.д.")
    entry_unit.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Цена за единицу:").grid(
        row=row, column=0, padx=10, pady=10, sticky="w")
    entry_price = ctk.CTkEntry(dialog, placeholder_text="Например: 150.50")
    entry_price.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    def save():
        name = entry_name.get().strip()
        qty_str = entry_qty.get().strip()
        unit = entry_unit.get().strip()
        price_str = entry_price.get().strip()

        if not all([name, qty_str, unit, price_str]):
            messagebox.showwarning("Предупреждение", "Заполните все поля.", parent=dialog)
            return

        try:
            qty = float(qty_str.replace(',', '.'))
            price = float(price_str.replace(',', '.'))
            if qty <= 0:
                messagebox.showerror("Ошибка", "Количество должно быть больше нуля.", parent=dialog)
                return
            if price < 0:
                messagebox.showerror("Ошибка", "Цена не может быть отрицательной.", parent=dialog)
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат числа.", parent=dialog)
            return

        cursor = app.conn.cursor()
        cursor.execute(
            'INSERT INTO "Склад" ("Название_Товара", "Количество", "Единица_измерения", "Цена_за_единицу") '
            'VALUES (?, ?, ?, ?)', (name, qty, unit, price))

        total_cost = qty * price
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        cursor.execute(
            'INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
            ('Расход', total_cost, today_str,
             f'Закупка материала: {name} ({qty} {unit})')
        )

        item_id = cursor.lastrowid
        cursor.execute(
            'INSERT INTO "История_Склада" ("ID_Товара", "Дата", "Тип", "Количество", "Причина") '
            'VALUES (?, ?, ?, ?, ?)',
            (item_id, today_str, 'Приход', qty,
             f'Первоначальное поступление (Цена: {price} за {unit})')
        )

        app.conn.commit()
        messagebox.showinfo("Успех",
                            f"Материал добавлен. Создан расход в финансах: {total_cost:.2f} руб.",
                            parent=dialog)
        dialog.destroy()
        app._display_entity_data("Склад")

    ctk.CTkButton(dialog, text="Сохранить", command=save,
                  fg_color="green").grid(row=row, column=0, columnspan=2,
                                         padx=10, pady=20, sticky="ew")


def open_edit_stock_dialog(app):
    """Диалог редактирования материала на складе"""
    if app.selected_card is None:
        messagebox.showwarning("Предупреждение", "Выберите карточку.")
        return

    record_id = app.selected_card.record_id
    cursor = app.conn.cursor()
    cursor.execute('SELECT * FROM "Склад" WHERE ID = ?', (record_id,))
    record = cursor.fetchone()
    if not record:
        messagebox.showerror("Ошибка", "Запись не найдена.", parent=app)
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Изменить: {record['Название_Товара']}")
    dialog.geometry("400x300")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    row = 0

    ctk.CTkLabel(dialog, text="Название товара:").grid(
        row=row, column=0, padx=10, pady=10, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.insert(0, str(record['Название_Товара']))
    entry_name.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Количество:").grid(
        row=row, column=0, padx=10, pady=10, sticky="w")
    entry_qty = ctk.CTkEntry(dialog)
    entry_qty.insert(0, str(record['Количество']))
    entry_qty.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Единица измерения:").grid(
        row=row, column=0, padx=10, pady=10, sticky="w")
    entry_unit = ctk.CTkEntry(dialog)
    entry_unit.insert(0, str(record['Единица_измерения']))
    entry_unit.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Цена за единицу:").grid(
        row=row, column=0, padx=10, pady=10, sticky="w")
    entry_price = ctk.CTkEntry(dialog)
    price_value = record['Цена_за_единицу'] if record['Цена_за_единицу'] else 0
    entry_price.insert(0, str(price_value))
    entry_price.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    def save():
        name = entry_name.get().strip()
        qty_str = entry_qty.get().strip()
        unit = entry_unit.get().strip()
        price_str = entry_price.get().strip()

        if not all([name, qty_str, unit, price_str]):
            messagebox.showwarning("Предупреждение", "Заполните все поля.", parent=dialog)
            return

        try:
            qty = float(qty_str.replace(',', '.'))
            price = float(price_str.replace(',', '.'))
            if qty < 0 or price < 0:
                messagebox.showerror("Ошибка",
                                     "Количество и цена не могут быть отрицательными.",
                                     parent=dialog)
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат числа.", parent=dialog)
            return

        cursor.execute(
            'UPDATE "Склад" SET "Название_Товара"=?, "Количество"=?, '
            '"Единица_измерения"=?, "Цена_за_единицу"=? WHERE ID=?',
            (name, qty, unit, price, record_id)
        )
        app.conn.commit()
        messagebox.showinfo("Успех", "Материал обновлён.", parent=dialog)
        dialog.destroy()
        app._display_entity_data("Склад")

    ctk.CTkButton(dialog, text="Сохранить", command=save,
                  fg_color="green").grid(row=row, column=0, columnspan=2,
                                         padx=10, pady=20, sticky="ew")

def open_add_finance_dialog(app):
    """Диалог добавления финансовой операции"""
    dialog = ctk.CTkToplevel(app)
    dialog.title("Добавить финансовую операцию")
    dialog.geometry("400x350")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
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
        summa_str = fields["Сумма"].get().strip()
        data_str = fields["Дата"].get().strip()
        opisanie = fields["Описание"].get().strip()

        if not all([tip, summa_str, data_str, opisanie]):
            messagebox.showwarning("Предупреждение", "Заполните все поля.", parent=dialog)
            return
        try:
            summa = float(summa_str.replace(',', '.'))
            app.conn.execute(
                'INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                (tip, summa, data_str, opisanie)
            )
            app.conn.commit()
            messagebox.showinfo("Успех", "Добавлено.", parent=dialog)
            dialog.destroy()
            app._display_entity_data("Финансы")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=dialog)

    ctk.CTkButton(dialog, text="Сохранить", command=save_finance_record,
                  fg_color="green").grid(row=4, columnspan=2, pady=20, sticky="ew")

def open_add_employee_dialog(app):
    dialog = ctk.CTkToplevel(app)
    dialog.title("Добавить: Сотрудник")
    dialog.geometry("500x450")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    cursor = app.conn.cursor()

    ctk.CTkLabel(dialog, text="Имя:").grid(
        row=0, column=0, padx=10, pady=8, sticky="w"
    )
    entry_name = ctk.CTkEntry(dialog)
    entry_name.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

    ctk.CTkLabel(dialog, text="Телефон:").grid(
        row=1, column=0, padx=10, pady=8, sticky="w"
    )
    entry_phone = ctk.CTkEntry(dialog)
    entry_phone.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

    ctk.CTkLabel(
        dialog,
        text="Назначить услуги (выберите):",
        font=ctk.CTkFont(size=12, weight="bold"),
    ).grid(row=2, column=0, columnspan=2, padx=10, pady=(12, 4), sticky="w")

    services_frame = ctk.CTkScrollableFrame(dialog, height=220)
    services_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=4, sticky="ew")
    services_frame.grid_columnconfigure(0, weight=1)

    cursor.execute('SELECT ID, "Название" FROM "Услуги" ORDER BY "Название"')
    services = cursor.fetchall()
    service_vars = []

    for i, s in enumerate(services):
        var = tk.IntVar()
        chk = ctk.CTkCheckBox(
            services_frame,
            text=s["Название"],
            variable=var,
        )
        chk.grid(row=i, column=0, sticky="w", padx=8, pady=2)
        service_vars.append((s["ID"], var))

    def save():
        name = entry_name.get().strip()
        phone = entry_phone.get().strip()

        if not name:
            messagebox.showwarning(
                "Внимание", "Укажите имя сотрудника.", parent=dialog
            )
            return

        cur = app.conn.cursor()

        cur.execute(
            'INSERT INTO "Сотрудники" ("Имя", "Телефон") VALUES (?, ?)',
            (name, phone),
        )
        emp_id = cur.lastrowid

        for sid, var in service_vars:
            try:
                if var.get():
                    cur.execute(
                        'INSERT INTO "Сотрудник_Услуги" ("ID_Сотрудника", "ID_Услуги") '
                        "VALUES (?, ?)",
                        (emp_id, sid),
                    )
            except Exception:
                continue

        app.conn.commit()
        messagebox.showinfo(
            "Успех",
            "Сотрудник добавлен и назначены услуги (если выбраны).",
            parent=dialog,
        )
        dialog.destroy()
        app._display_entity_data("Сотрудники")

    ctk.CTkButton(
        dialog,
        text="Сохранить",
        command=save,
        fg_color="green",
    ).grid(row=4, column=0, columnspan=2, padx=10, pady=12, sticky="ew")


def open_add_service_dialog(app):
    dialog = ctk.CTkToplevel(app)
    dialog.title("Добавить: Услуга")
    dialog.geometry("600x500")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    row = 0

    ctk.CTkLabel(dialog, text="Название:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Цена:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry_price = ctk.CTkEntry(dialog)
    entry_price.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Длительность (мин):").grid(
        row=row, column=0, padx=10, pady=5, sticky="w")
    entry_duration = ctk.CTkEntry(dialog)
    entry_duration.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Расход материалов:",
                 font=ctk.CTkFont(size=12, weight="bold")).grid(
        row=row, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w"
    )
    row += 1

    materials_frame = ctk.CTkScrollableFrame(dialog, height=200)
    materials_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
    materials_frame.grid_columnconfigure(1, weight=1)
    row += 1

    cursor = app.conn.cursor()
    cursor.execute('SELECT ID, "Название_Товара", "Единица_измерения" FROM "Склад" ORDER BY "Название_Товара"')
    materials = cursor.fetchall()

    material_widgets = {}

    def add_material_row():
        mat_row = len(material_widgets)
        material_names = [f"{m['Название_Товара']} ({m['Единица_измерения']})" for m in materials]
        if not material_names:
            messagebox.showwarning("Предупреждение",
                                   "Нет материалов на складе. Сначала добавьте материалы.",
                                   parent=dialog)
            return

        combo_material = ctk.CTkComboBox(materials_frame, values=material_names, width=250)
        combo_material.grid(row=mat_row, column=0, padx=5, pady=2, sticky="ew")

        entry_qty = ctk.CTkEntry(materials_frame, width=100, placeholder_text="0.0")
        entry_qty.grid(row=mat_row, column=1, padx=5, pady=2, sticky="ew")

        def remove_row(idx=mat_row):
            combo_material.grid_remove()
            entry_qty.grid_remove()
            btn_remove.grid_remove()
            material_widgets.pop(idx, None)

        btn_remove = ctk.CTkButton(materials_frame, text="✖", width=30,
                                   fg_color="red", command=remove_row)
        btn_remove.grid(row=mat_row, column=2, padx=5, pady=2)

        material_widgets[mat_row] = (combo_material, entry_qty, btn_remove)

    btn_add_material = ctk.CTkButton(dialog, text="➕ Добавить материал", command=add_material_row)
    btn_add_material.grid(row=row, column=0, columnspan=2, padx=10, pady=5)
    row += 1

    def save():
        name = entry_name.get().strip()
        price_str = entry_price.get().strip()
        duration_str = entry_duration.get().strip()

        if not all([name, price_str, duration_str]):
            messagebox.showwarning("Предупреждение",
                                   "Заполните все основные поля.",
                                   parent=dialog)
            return

        try:
            price = float(price_str.replace(',', '.'))
            duration = int(duration_str)
        except ValueError:
            messagebox.showerror("Ошибка",
                                 "Неверный формат цены или длительности.",
                                 parent=dialog)
            return

        if duration <= 0 or duration % 30 != 0:
            messagebox.showerror(
                "Ошибка",
                "Длительность должна быть положительной и кратной 30 минутам "
                "(например: 30, 60, 90, 120).",
                parent=dialog
            )
            return

        cursor.execute(
            'INSERT INTO "Услуги" ("Название", "Цена", "Длительность") VALUES (?, ?, ?)',
            (name, price, duration)
        )

        app.conn.commit()
        messagebox.showinfo("Успех", "Услуга добавлена.", parent=dialog)
        dialog.destroy()
        app._display_entity_data("Услуги")

    ctk.CTkButton(dialog, text="Сохранить", command=save,
                  fg_color="green").grid(row=row, column=0, columnspan=2,
                                         padx=10, pady=10, sticky="ew")


def open_edit_service_dialog(app):
    if app.selected_card is None:
        messagebox.showwarning("Предупреждение", "Выберите услугу.")
        return

    service_id = app.selected_card.record_id
    cursor = app.conn.cursor()
    cursor.execute('SELECT * FROM "Услуги" WHERE ID = ?', (service_id,))
    service = cursor.fetchone()
    if not service:
        messagebox.showerror("Ошибка", "Услуга не найдена.", parent=app)
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Изменить: {service['Название']}")
    dialog.geometry("600x500")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    row = 0

    ctk.CTkLabel(dialog, text="Название:").grid(
        row=row, column=0, padx=10, pady=5, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.insert(0, str(service['Название']))
    entry_name.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Цена:").grid(
        row=row, column=0, padx=10, pady=5, sticky="w")
    entry_price = ctk.CTkEntry(dialog)
    entry_price.insert(0, str(service['Цена']))
    entry_price.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Длительность (мин):").grid(
        row=row, column=0, padx=10, pady=5, sticky="w")
    entry_duration = ctk.CTkEntry(dialog)
    entry_duration.insert(0, str(service['Длительность']))
    entry_duration.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1

    ctk.CTkLabel(dialog, text="Расход материалов:",
                 font=ctk.CTkFont(size=12, weight="bold")).grid(
        row=row, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w"
    )
    row += 1

    materials_frame = ctk.CTkScrollableFrame(dialog, height=200)
    materials_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
    materials_frame.grid_columnconfigure(1, weight=1)
    row += 1

    cursor.execute('SELECT ID, "Название_Товара", "Единица_измерения" FROM "Склад" ORDER BY "Название_Товара"')
    materials = cursor.fetchall()

    cursor.execute(
        'SELECT "ID_Материала", "Количество" FROM "Расход_Материалов" WHERE "ID_Услуги"=?',
        (service_id,)
    )
    existing_materials = {r['ID_Материала']: r['Количество'] for r in cursor.fetchall()}

    material_widgets = {}

    for mat_id, qty in existing_materials.items():
        mat_row = len(material_widgets)
        material_info = next((m for m in materials if m['ID'] == mat_id), None)
        if not material_info:
            continue

        material_names = [f"{m['Название_Товара']} ({m['Единица_измерения']})" for m in materials]
        combo_material = ctk.CTkComboBox(materials_frame, values=material_names, width=250)
        combo_material.set(f"{material_info['Название_Товара']} ({material_info['Единица_измерения']})")
        combo_material.grid(row=mat_row, column=0, padx=5, pady=2, sticky="ew")

        entry_qty = ctk.CTkEntry(materials_frame, width=100)
        entry_qty.insert(0, str(qty))
        entry_qty.grid(row=mat_row, column=1, padx=5, pady=2, sticky="ew")

        def remove_row(idx=mat_row):
            combo_material.grid_remove()
            entry_qty.grid_remove()
            btn_remove.grid_remove()
            material_widgets.pop(idx, None)

        btn_remove = ctk.CTkButton(materials_frame, text="✖", width=30,
                                   fg_color="red", command=remove_row)
        btn_remove.grid(row=mat_row, column=2, padx=5, pady=2)

        material_widgets[mat_row] = (combo_material, entry_qty, btn_remove)

    def add_material_row():
        mat_row = len(material_widgets)
        material_names = [f"{m['Название_Товара']} ({m['Единица_измерения']})" for m in materials]
        if not material_names:
            messagebox.showwarning("Предупреждение",
                                   "Нет материалов на складе.",
                                   parent=dialog)
            return

        combo_material = ctk.CTkComboBox(materials_frame, values=material_names, width=250)
        combo_material.grid(row=mat_row, column=0, padx=5, pady=2, sticky="ew")

        entry_qty = ctk.CTkEntry(materials_frame, width=100, placeholder_text="0.0")
        entry_qty.grid(row=mat_row, column=1, padx=5, pady=2, sticky="ew")

        def remove_row(idx=mat_row):
            combo_material.grid_remove()
            entry_qty.grid_remove()
            btn_remove.grid_remove()
            material_widgets.pop(idx, None)

        btn_remove = ctk.CTkButton(materials_frame, text="✖", width=30,
                                   fg_color="red", command=remove_row)
        btn_remove.grid(row=mat_row, column=2, padx=5, pady=2)

        material_widgets[mat_row] = (combo_material, entry_qty, btn_remove)

    btn_add_material = ctk.CTkButton(dialog, text="➕ Добавить материал", command=add_material_row)
    btn_add_material.grid(row=row, column=0, columnspan=2, padx=10, pady=5)
    row += 1

    def save():
        name = entry_name.get().strip()
        price_str = entry_price.get().strip()
        duration_str = entry_duration.get().strip()

        if not all([name, price_str, duration_str]):
            messagebox.showwarning("Предупреждение",
                                   "Заполните все основные поля.",
                                   parent=dialog)
            return

        try:
            price = float(price_str.replace(',', '.'))
            duration = int(duration_str)
        except ValueError:
            messagebox.showerror("Ошибка",
                                 "Неверный формат цены или длительности.",
                                 parent=dialog)
            return

        cursor.execute(
            'UPDATE "Услуги" SET "Название"=?, "Цена"=?, "Длительность"=? WHERE ID=?',
            (name, price, duration, service_id)
        )

        cursor.execute('DELETE FROM "Расход_Материалов" WHERE "ID_Услуги"=?', (service_id,))

        for _, (combo, entry_qty, _) in material_widgets.items():
            material_name_unit = combo.get()
            if not material_name_unit:
                continue

            qty_str = entry_qty.get().strip()
            if not qty_str:
                continue

            try:
                qty = float(qty_str.replace(',', '.'))
                if qty <= 0:
                    continue
            except ValueError:
                continue

            material_name = material_name_unit.split(' (')[0]
            material_id = None
            for m in materials:
                if m['Название_Товара'] == material_name:
                    material_id = m['ID']
                    break

            if material_id:
                cursor.execute(
                    'INSERT INTO "Расход_Материалов" ("ID_Услуги", "ID_Материала", "Количество") '
                    'VALUES (?, ?, ?)',
                    (service_id, material_id, qty)
                )

        app.conn.commit()
        messagebox.showinfo("Успех", "Услуга обновлена.", parent=dialog)
        dialog.destroy()
        app._display_entity_data("Услуги")

    ctk.CTkButton(dialog, text="Сохранить", command=save,
                  fg_color="green").grid(row=row, column=0, columnspan=2,
                                         padx=10, pady=10, sticky="ew")

def open_add_schedule_dialog(app):
    name_to_id, _ = app._get_employee_map()
    dialog = ctk.CTkToplevel(app)
    dialog.title("Смена")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()

    ctk.CTkLabel(dialog, text="Сотрудник").pack()
    combo = ctk.CTkComboBox(dialog, values=list(name_to_id.keys()))
    combo.pack()
    ctk.CTkLabel(dialog, text="Дата (YYYY-MM-DD)").pack()
    e_date = ctk.CTkEntry(dialog)
    e_date.insert(0, str(datetime.date.today()))
    e_date.pack()
    ctk.CTkLabel(dialog, text="Начало").pack()
    e_start = ctk.CTkEntry(dialog)
    e_start.insert(0, "09:00")
    e_start.pack()
    ctk.CTkLabel(dialog, text="Конец").pack()
    e_end = ctk.CTkEntry(dialog)
    e_end.insert(0, "18:00")
    e_end.pack()

    def save():
        eid = name_to_id.get(combo.get())
        app.conn.execute(
            'INSERT INTO "График работы" ("ID_Сотрудника", "Дата", "Время_Начала", "Время_Конца") '
            'VALUES (?,?,?,?)',
            (eid, e_date.get().strip(), e_start.get().strip(), e_end.get().strip())
        )
        app.conn.commit()
        dialog.destroy()
        app._display_entity_data("График работы")

    ctk.CTkButton(dialog, text="ОК", command=save).pack(pady=10)


def open_add_appointment_dialog(app):
    """Диалог добавления записи (appointment) с несколькими услугами"""
    dialog = ctk.CTkToplevel(app)
    dialog.title("Добавить: Запись")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()

    name_to_id_emp, id_to_name_emp = app._get_employee_map()
    cursor = app.conn.cursor()
    cursor.execute('SELECT "ID", "ФИО" FROM "Клиенты"')
    clients = cursor.fetchall()
    name_to_id_cli = {c['ФИО']: c['ID'] for c in clients if c['ФИО']}

    cursor.execute('SELECT ID, "Название", "Длительность" FROM "Услуги" ORDER BY "Название"')
    all_services = cursor.fetchall()

    fields = {}
    row = 0

    ctk.CTkLabel(dialog, text="Дата").grid(row=row, column=0, padx=10, pady=5)
    entry_date = ctk.CTkEntry(dialog, state="disabled")
    entry_date.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    entry_date.insert(0, str(datetime.date.today()))
    fields['Дата'] = entry_date
    btn_pick_date = ctk.CTkButton(dialog, text="Выбрать дату")
    btn_pick_date.grid(row=row, column=2, padx=6, pady=5)
    row += 1

    def open_date_picker(parent, target_entry):
        top = tk.Toplevel(parent)
        top.title("Выберите дату")
        top.transient(parent)
        top.grab_set()
        center_dialog(parent, top)

        cur_date = datetime.date.today().replace(day=1)
        header = tk.Frame(top)
        header.pack(fill="x", pady=4)
        month_label = tk.Label(header,
                               text=cur_date.strftime('%B %Y').capitalize(),
                               font=("Arial", 12, "bold"))
        month_label.pack(side="top", pady=2)
        cal_fr = tk.Frame(top)
        cal_fr.pack(padx=6, pady=6)

        def render(month_date):
            for w in cal_fr.winfo_children():
                w.destroy()
            month_label.config(text=month_date.strftime('%B %Y').capitalize())
            cal = calendar.monthcalendar(month_date.year, month_date.month)
            days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            for c, d in enumerate(days):
                lbl = tk.Label(cal_fr, text=d, width=4, fg="#666666")
                lbl.grid(row=0, column=c)
            for r, week in enumerate(cal, start=1):
                for c, d in enumerate(week):
                    if d == 0:
                        tk.Label(cal_fr, text="", width=4).grid(row=r, column=c, padx=2, pady=2)
                        continue

                    def on_choose(day=d, md=month_date):
                        chosen = datetime.date(md.year, md.month, day)
                        target_entry.configure(state="normal")
                        target_entry.delete(0, tk.END)
                        target_entry.insert(0, str(chosen))
                        target_entry.configure(state="disabled")
                        top.destroy()

                    btn = tk.Button(cal_fr, text=str(d), width=4, command=on_choose)
                    if datetime.date.today() == datetime.date(
                        month_date.year, month_date.month, d
                    ):
                        btn.config(relief='solid')
                    btn.grid(row=r, column=c, padx=2, pady=2)

        def prev_month():
            nonlocal cur_date
            y = cur_date.year
            m = cur_date.month - 1
            if m < 1:
                m = 12
                y -= 1
            cur_date = cur_date.replace(year=y, month=m, day=1)
            render(cur_date)

        def next_month():
            nonlocal cur_date
            y = cur_date.year
            m = cur_date.month + 1
            if m > 12:
                m = 1
                y += 1
            cur_date = cur_date.replace(year=y, month=m, day=1)
            render(cur_date)

        nav = tk.Frame(top)
        nav.pack(fill="x")
        tk.Button(nav, text="◀", command=prev_month, width=3).pack(side="left", padx=6)
        tk.Button(nav, text="▶", command=next_month, width=3).pack(side="right", padx=6)

        render(cur_date)

    btn_pick_date.configure(command=lambda: open_date_picker(dialog, entry_date))
    ctk.CTkLabel(dialog, text="Сотрудник").grid(row=row, column=0, padx=10, pady=5)
    combo_emp = ctk.CTkComboBox(dialog, values=list(name_to_id_emp.keys()))
    combo_emp.grid(row=row, column=1, padx=10, pady=5)
    fields['ID_Сотрудника'] = combo_emp
    row += 1

    ctk.CTkLabel(dialog, text="Клиент").grid(row=row, column=0, padx=10, pady=5)
    combo_cli = ctk.CTkComboBox(dialog, values=list(name_to_id_cli.keys()))
    combo_cli.grid(row=row, column=1, padx=10, pady=5)
    fields['ID_Клиента'] = combo_cli
    row += 1

    ctk.CTkLabel(dialog, text="Услуги").grid(row=row, column=0, padx=10, pady=5, sticky="nw")
    services_frame = ctk.CTkScrollableFrame(dialog, height=160)
    services_frame.grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="nsew")
    row += 1

    service_vars = []

    def render_services_for_employee(*_):
        for w in services_frame.winfo_children():
            w.destroy()
        service_vars.clear()

        emp_name = combo_emp.get()
        emp_id = name_to_id_emp.get(emp_name)

        allowed_ids = set()
        if emp_id:
            cur = app.conn.cursor()
            cur.execute(
                'SELECT "ID_Услуги" FROM "Сотрудник_Услуги" WHERE "ID_Сотрудника"=?',
                (emp_id,)
            )
            allowed_ids = {r['ID_Услуги'] for r in cur.fetchall()}

        r_ = 0
        for s in all_services:
            if allowed_ids and s["ID"] not in allowed_ids:
                continue
            var = tk.IntVar()
            txt = f'{s["Название"]} ({s["Длительность"]} мин)'
            chk = ctk.CTkCheckBox(services_frame, text=txt, variable=var)
            chk.grid(row=r_, column=0, sticky="w", pady=1, padx=5)
            service_vars.append((s["ID"], var, int(s["Длительность"] or 30), s["Название"]))
            r_ += 1

    combo_emp.bind("<<ComboboxSelected>>", render_services_for_employee)
    render_services_for_employee()

    def get_selected_services():
        res = []
        for sid, var, dur, name in service_vars:
            if var.get():
                res.append((sid, name, dur))
        return res


    ctk.CTkLabel(dialog, text="Время").grid(row=row, column=0, padx=10, pady=5)
    combo_time = ctk.CTkEntry(dialog, state="disabled")
    combo_time.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    combo_time._slots = []
    btn_pick_time = ctk.CTkButton(dialog, text="Выбрать время")
    btn_pick_time.grid(row=row, column=2, padx=6, pady=5)
    fields['Время'] = combo_time
    row += 1

    def update_time_options(*_):

        emp_name = combo_emp.get()
        date_str = entry_date.get()
        emp_id = name_to_id_emp.get(emp_name)
        if not emp_id or not date_str:
            combo_time._slots = []
            return
        cur = app.conn.cursor()
        cur.execute(
            'SELECT "Время_Начала", "Время_Конца" FROM "График работы" '
            'WHERE "ID_Сотрудника"=? AND "Дата"=?',
            (emp_id, date_str)
        )
        res = cur.fetchone()
        if not res:
            combo_time._slots = []
            combo_time.configure(state="normal")
            combo_time.delete(0, tk.END)
            combo_time.configure(state="disabled")
            return
        t_start, t_end = res['Время_Начала'], res['Время_Конца']
        fmt = "%H:%M"
        d_start = datetime.datetime.strptime(t_start, fmt)
        d_end = datetime.datetime.strptime(t_end, fmt)
        times = []
        step = timedelta(minutes=30)
        t_ = d_start
        while t_ < d_end:
            times.append(t_.strftime(fmt))
            t_ += step
        combo_time._slots = times
        combo_time.configure(state="normal")
        combo_time.delete(0, tk.END)
        if times:
            combo_time.insert(0, times[0])
        combo_time.configure(state="disabled")

    combo_emp.bind("<<ComboboxSelected>>", lambda e: update_time_options())
    entry_date.bind("<FocusOut>", lambda e: update_time_options())

    def open_time_picker(parent, target_entry):
        top = tk.Toplevel(parent)
        top.title("Выберите время")
        top.transient(parent)
        top.grab_set()
        center_dialog(parent, top)

        list_frame = tk.Frame(top)
        list_frame.pack(fill="both", expand=True, padx=6, pady=6)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                             width=20, height=12)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        slots = []
        try:
            update_time_options()
            if hasattr(combo_time, '_slots') and combo_time._slots:
                slots = list(combo_time._slots)
        except Exception:
            slots = []

        if not slots:
            fmt = "%H:%M"
            start = datetime.datetime.strptime("08:00", fmt)
            end = datetime.datetime.strptime("22:00", fmt)
            t_ = start
            while t_ <= end:
                slots.append(t_.strftime(fmt))
                t_ += timedelta(minutes=30)

        for s in slots:
            listbox.insert("end", s)

        def choose_time(_evt=None):
            sel = listbox.curselection()
            if not sel:
                return
            value = listbox.get(sel[0])
            target_entry.configure(state="normal")
            target_entry.delete(0, tk.END)
            target_entry.insert(0, value)
            target_entry.configure(state="disabled")
            top.destroy()

        listbox.bind("<Double-Button-1>", choose_time)
        btn_frame = tk.Frame(top)
        btn_frame.pack(fill="x", pady=6)
        tk.Button(btn_frame, text="OK", command=choose_time).pack(side="right", padx=6)

    btn_pick_time.configure(command=lambda: open_time_picker(dialog, combo_time))

    def save():
        date_val = fields['Дата'].get()
        emp_val = combo_emp.get()
        cli_val = combo_cli.get()
        time_val = fields['Время'].get()

        selected_services = get_selected_services()

        if not all([date_val, emp_val, cli_val, time_val]):
            messagebox.showwarning("!",
                                   "Заполните все поля и выберите время, согласно смене сотрудника.",
                                   parent=dialog)
            return

        if not selected_services:
            messagebox.showwarning("!",
                                   "Выберите хотя бы одну услугу.",
                                   parent=dialog)
            return
        total_duration = sum(d for _, _, d in selected_services)
        try:
            parts = time_val.split(":")
            if len(parts) != 2:
                raise ValueError()
            hour = int(parts[0])
            minute = int(parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError()
        except Exception:
            messagebox.showerror("Ошибка",
                                 "Неверный формат времени. Используйте HH:MM.",
                                 parent=dialog)
            return

        if hour < 8 or hour > 22 or (hour == 22 and minute > 0):
            messagebox.showerror("Ошибка",
                                 "Время должно быть в интервале 08:00–22:00 (включительно).",
                                 parent=dialog)
            return

        time_val_norm = f"{hour:02d}:{minute:02d}"
        emp_id = name_to_id_emp.get(emp_val)
        cli_id = name_to_id_cli.get(cli_val)

        if not emp_id or not cli_id:
            messagebox.showerror("Ошибка", "Выберите сотрудника и клиента.", parent=dialog)
            return
        cur = app.conn.cursor()

        cur.execute(
            'SELECT "Время_Начала", "Время_Конца" FROM "График работы" '
            'WHERE "ID_Сотрудника"=? AND "Дата"=?',
            (emp_id, date_val)
        )
        shift = cur.fetchone()
        if not shift:
            messagebox.showerror(
                "Ошибка",
                "На выбранную дату для этого сотрудника нет смены в графике.",
                parent=dialog,
            )
            return

        shift_start = time_str_to_minutes(shift["Время_Начала"])
        shift_end = time_str_to_minutes(shift["Время_Конца"])
        start_minute = time_str_to_minutes(time_val_norm)
        end_minute = start_minute + total_duration

        if start_minute < shift_start or end_minute > shift_end:
            messagebox.showerror(
                "Ошибка",
                "Суммарная длительность услуг выходит за пределы смены сотрудника.",
                parent=dialog,
            )
            return

        cur.execute(
            'SELECT ID, "Время", "ID_Услуги" FROM "Записи" '
            'WHERE "Дата"=? AND "ID_Сотрудника"=?',
            (date_val, emp_id)
        )
        existing = cur.fetchall()

        for ex in existing:
            ex_start = time_str_to_minutes(ex["Время"])
            ex_dur = get_appointment_duration(
                app.conn,
                ex["ID"],
                ex["ID_Услуги"] if "ID_Услуги" in ex.keys() else None
            )
            ex_end = ex_start + ex_dur
            if not (end_minute <= ex_start or start_minute >= ex_end):
                messagebox.showerror(
                    "Ошибка",
                    f"Сотрудник {emp_val} уже занят c {ex['Время']} до {minutes_to_time_str(ex_end)}.",
                    parent=dialog,
                )
                return

        first_service_id = selected_services[0][0]
        cur.execute(
            'INSERT INTO "Записи" ("Дата","Время","ID_Клиента","ID_Сотрудника","ID_Услуги") '
            'VALUES (?,?,?,?,?)',
            (date_val, time_val_norm, cli_id, emp_id, first_service_id)
        )
        record_id = cur.lastrowid
        service_ids = []
        service_names = []
        for sid, name, dur in selected_services:
            service_ids.append(sid)
            service_names.append(name)
            cur.execute(
                'INSERT INTO "Запись_Услуги" ("ID_Записи","ID_Услуги") VALUES (?, ?)',
                (record_id, sid)
            )

        materials_needed = {}
        for sid in service_ids:
            cur.execute(
                'SELECT "ID_Материала", "Количество" '
                'FROM "Расход_Материалов" WHERE "ID_Услуги"=?',
                (sid,)
            )
            for r in cur.fetchall():
                mid = r["ID_Материала"]
                qty = float(r["Количество"])
                materials_needed[mid] = materials_needed.get(mid, 0) + qty

        insufficient_materials = []
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        for mat_id, required_qty in materials_needed.items():
            cur.execute(
                'SELECT "Количество", "Название_Товара", "Единица_измерения" '
                'FROM "Склад" WHERE ID=?',
                (mat_id,)
            )
            mat_info = cur.fetchone()
            if not mat_info:
                continue

            current_qty = float(mat_info["Количество"])
            mat_name = mat_info["Название_Товара"]
            unit = mat_info["Единица_измерения"]

            if current_qty < required_qty:
                insufficient_materials.append(
                    f"{mat_name} (требуется: {required_qty}, доступно: {current_qty})"
                )
                continue

            new_qty = current_qty - required_qty
            cur.execute(
                'UPDATE "Склад" SET "Количество"=? WHERE ID=?',
                (new_qty, mat_id)
            )
            reason = f"Услуги: {', '.join(service_names)}, Клиент: {cli_val}"
            cur.execute(
                'INSERT INTO "История_Склада" ("ID_Товара", "Дата", "Тип", "Количество", "Причина") '
                'VALUES (?, ?, ?, ?, ?)',
                (mat_id, today_str, "Расход", required_qty, reason)
            )

        app.conn.commit()

        if insufficient_materials:
            messagebox.showwarning(
                "Внимание",
                "Запись создана, но недостаточно материалов:\n" +
                "\n".join(insufficient_materials),
                parent=dialog,
            )
        else:
            messagebox.showinfo(
                "Успех",
                "Запись создана. Материалы списаны со склада.",
                parent=dialog,
            )

        dialog.destroy()
        app._display_entity_data(app.current_entity)

    ctk.CTkButton(dialog, text="Сохранить", command=save).grid(
        row=row, columnspan=2, pady=10
    )


def open_edit_record_dialog(app):
    """Диалог редактирования записи"""
    if app.selected_card is None:
        messagebox.showwarning("Предупреждение", "Выберите карточку.")
        return
    if app.current_entity in ["График работы", "Расписание", "Финансы"]:
        messagebox.showwarning("Предупреждение", "Редактирование здесь не поддерживается.")
        return
    if app.current_entity == "Услуги":
        open_edit_service_dialog(app)
        return
    if app.current_entity == "Склад":
        open_edit_stock_dialog(app)
        return

    record_id = app.selected_card.record_id
    entity_name = app.current_entity
    columns = app._get_table_columns(entity_name)
    data_columns = [(name, t) for name, t in columns if name.upper() != 'ID']
    if entity_name == "Сотрудники":
        data_columns = [(name, t) for name, t in data_columns if name != "Должность"]

    cursor = app.conn.cursor()
    cursor.execute(f'SELECT * FROM "{entity_name}" WHERE ID=?', (record_id,))
    record = cursor.fetchone()
    if not record:
        messagebox.showerror("Ошибка", "Запись не найдена.", parent=app)
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Изменить #{record_id}")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()

    if entity_name == "Записи":
        name_to_id_emp, id_to_name_emp = app._get_employee_map()
        cursor = app.conn.cursor()
        cursor.execute('SELECT "ID", "ФИО" FROM "Клиенты"')
        clients = cursor.fetchall()
        name_to_id_cli = {c['ФИО']: c['ID'] for c in clients if c['ФИО']}

        row = 0

        ctk.CTkLabel(dialog, text="Дата").grid(row=row, column=0, padx=10, pady=5)
        entry_date = ctk.CTkEntry(dialog, state="disabled")
        entry_date.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        entry_date.insert(0, str(record['Дата']))
        row += 1

        def open_date_picker(parent, target_entry):
            top = tk.Toplevel(parent)
            top.title("Выберите дату")
            top.transient(parent)
            top.grab_set()
            center_dialog(parent, top)

            cur_date = datetime.date.today().replace(day=1)
            header = tk.Frame(top)
            header.pack(fill="x", pady=4)
            month_label = tk.Label(header,
                                   text=cur_date.strftime('%B %Y').capitalize(),
                                   font=("Arial", 12, "bold"))
            month_label.pack(side="top", pady=2)
            cal_fr = tk.Frame(top)
            cal_fr.pack(padx=6, pady=6)

            def render(month_date):
                for w in cal_fr.winfo_children():
                    w.destroy()
                month_label.config(text=month_date.strftime('%B %Y').capitalize())
                cal = calendar.monthcalendar(month_date.year, month_date.month)
                days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                for c, d in enumerate(days):
                    tk.Label(cal_fr, text=d, width=4, fg="#666666").grid(row=0, column=c)
                for r, week in enumerate(cal, start=1):
                    for c, d in enumerate(week):
                        if d == 0:
                            tk.Label(cal_fr, text="", width=4).grid(row=r, column=c, padx=2, pady=2)
                            continue

                        def on_choose(day=d, md=month_date):
                            chosen = datetime.date(md.year, md.month, day)
                            target_entry.configure(state="normal")
                            target_entry.delete(0, tk.END)
                            target_entry.insert(0, str(chosen))
                            target_entry.configure(state="disabled")
                            top.destroy()

                        btn = tk.Button(cal_fr, text=str(d), width=4, command=on_choose)
                        if datetime.date.today() == datetime.date(
                                month_date.year, month_date.month, d
                        ):
                            btn.config(relief='solid')
                        btn.grid(row=r, column=c, padx=2, pady=2)

            def prev_month():
                nonlocal cur_date
                y = cur_date.year
                m = cur_date.month - 1
                if m < 1:
                    m = 12
                    y -= 1
                cur_date = cur_date.replace(year=y, month=m, day=1)
                render(cur_date)

            def next_month():
                nonlocal cur_date
                y = cur_date.year
                m = cur_date.month + 1
                if m > 12:
                    m = 1
                    y += 1
                cur_date = cur_date.replace(year=y, month=m, day=1)
                render(cur_date)

            nav = tk.Frame(top)
            nav.pack(fill="x")
            tk.Button(nav, text="◀", command=prev_month, width=3).pack(side="left", padx=6)
            tk.Button(nav, text="▶", command=next_month, width=3).pack(side="right", padx=6)
            render(cur_date)

        btn_pick_date = ctk.CTkButton(dialog, text="Выбрать дату",
                                      command=lambda: open_date_picker(dialog, entry_date))
        btn_pick_date.grid(row=row - 1, column=2, padx=6, pady=5)

        ctk.CTkLabel(dialog, text="Сотрудник").grid(row=row, column=0, padx=10, pady=5)
        combo_emp = ctk.CTkComboBox(dialog, values=list(name_to_id_emp.keys()))
        combo_emp.grid(row=row, column=1, padx=10, pady=5)
        combo_emp.set(id_to_name_emp.get(record['ID_Сотрудника'], ''))
        row += 1

        ctk.CTkLabel(dialog, text="Клиент").grid(row=row, column=0, padx=10, pady=5)
        combo_cli = ctk.CTkComboBox(dialog, values=list(name_to_id_cli.keys()))
        combo_cli.grid(row=row, column=1, padx=10, pady=5)
        try:
            current_cli = next(
                k for k, v in name_to_id_cli.items() if v == record['ID_Клиента']
            )
            combo_cli.set(current_cli)
        except StopIteration:
            pass
        row += 1

        cursor.execute(
            'SELECT u."Название" FROM "Запись_Услуги" zu '
            'JOIN "Услуги" u ON zu."ID_Услуги" = u.ID '
            'WHERE zu."ID_Записи" = ?',
            (record_id,)
        )
        svc_rows = cursor.fetchall()
        service_names = [r["Название"] for r in svc_rows]
        if not service_names and record["ID_Услуги"]:
            cursor.execute(
                'SELECT "Название" FROM "Услуги" WHERE ID = ?',
                (record["ID_Услуги"],)
            )
            r = cursor.fetchone()
            if r:
                service_names = [r["Название"]]

        if service_names:
            ctk.CTkLabel(dialog, text="Услуги:").grid(row=row, column=0, padx=10, pady=5, sticky="nw")
            ctk.CTkLabel(
                dialog,
                text=" + ".join(service_names),
                wraplength=260,
                justify="left",
            ).grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="w")
            row += 1

        ctk.CTkLabel(dialog, text="Время").grid(row=row, column=0, padx=10, pady=5)
        combo_time = ctk.CTkEntry(dialog, state='disabled')
        combo_time.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
        combo_time._slots = []
        btn_pick_time = ctk.CTkButton(dialog, text='Выбрать время')
        btn_pick_time.grid(row=row, column=2, padx=6, pady=5)

        combo_time.configure(state='normal')
        combo_time.delete(0, tk.END)
        combo_time.insert(0, record['Время'])
        combo_time.configure(state='disabled')
        row += 1

        def update_time_options(*_):
            emp_name = combo_emp.get()
            date_str = entry_date.get()
            emp_id = name_to_id_emp.get(emp_name)
            if not emp_id or not date_str:
                combo_time._slots = []
                return
            cur = app.conn.cursor()
            cur.execute(
                'SELECT "Время_Начала", "Время_Конца" FROM "График работы" '
                'WHERE "ID_Сотрудника"=? AND "Дата"=?',
                (emp_id, date_str)
            )
            res = cur.fetchone()
            if not res:
                combo_time._slots = []
                combo_time.configure(state='normal')
                combo_time.delete(0, tk.END)
                combo_time.configure(state='disabled')
                return
            t_start, t_end = res['Время_Начала'], res['Время_Конца']
            fmt = '%H:%M'
            d_start = datetime.datetime.strptime(t_start, fmt)
            d_end = datetime.datetime.strptime(t_end, fmt)
            times = []
            step = timedelta(minutes=30)
            t_ = d_start
            while t_ < d_end:
                times.append(t_.strftime(fmt))
                t_ += step
            combo_time._slots = times

        entry_date.bind('<FocusOut>', lambda e: update_time_options())
        combo_emp.bind("<<ComboboxSelected>>", lambda e: update_time_options())

        def open_time_picker(parent, target_entry):
            top = tk.Toplevel(parent)
            top.title('Выберите время')
            top.transient(parent)
            top.grab_set()
            center_dialog(parent, top)

            list_frame = tk.Frame(top)
            list_frame.pack(fill='both', expand=True, padx=6, pady=6)
            scrollbar = tk.Scrollbar(list_frame)
            scrollbar.pack(side='right', fill='y')
            listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                 width=20, height=12)
            listbox.pack(side='left', fill='both', expand=True)
            scrollbar.config(command=listbox.yview)

            slots = []
            try:
                update_time_options()
                if hasattr(combo_time, '_slots') and combo_time._slots:
                    slots = list(combo_time._slots)
            except Exception:
                slots = []

            if not slots:
                fmt = '%H:%M'
                start = datetime.datetime.strptime('08:00', fmt)
                end = datetime.datetime.strptime('22:00', fmt)
                t_ = start
                while t_ <= end:
                    slots.append(t_.strftime(fmt))
                    t_ += timedelta(minutes=30)

            for s in slots:
                listbox.insert('end', s)

            def choose_time(_evt=None):
                sel = listbox.curselection()
                if not sel:
                    return
                value = listbox.get(sel[0])
                target_entry.configure(state='normal')
                target_entry.delete(0, tk.END)
                target_entry.insert(0, value)
                target_entry.configure(state='disabled')
                top.destroy()

            listbox.bind('<Double-Button-1>', choose_time)
            btn_frame = tk.Frame(top)
            btn_frame.pack(fill='x', pady=6)
            tk.Button(btn_frame, text='OK', command=choose_time).pack(side='right', padx=6)

        btn_pick_time.configure(command=lambda: open_time_picker(dialog, combo_time))

        def save_record():
            date_val = entry_date.get()
            emp_val = combo_emp.get()
            cli_val = combo_cli.get()
            time_val = combo_time.get()

            if not all([date_val, emp_val, cli_val, time_val]):
                messagebox.showwarning('!',
                                       'Заполните все поля и выберите время, согласно смене сотрудника.')
                return

            try:
                parts = time_val.split(':')
                if len(parts) != 2:
                    raise ValueError()
                hour = int(parts[0])
                minute = int(parts[1])
            except Exception:
                messagebox.showerror('Ошибка',
                                     'Неверный формат времени. Используйте HH:MM.',
                                     parent=dialog)
                return

            if hour < 8 or hour > 22 or (hour == 22 and minute > 0):
                messagebox.showerror('Ошибка',
                                     'Время должно быть в интервале 08:00–22:00 (включительно).',
                                     parent=dialog)
                return

            emp_id = name_to_id_emp.get(emp_val)
            cli_id = name_to_id_cli.get(cli_val)
            if not emp_id or not cli_id:
                messagebox.showerror("Ошибка", "Выберите сотрудника и клиента.", parent=dialog)
                return

            total_duration = get_appointment_duration(
                app.conn,
                record_id,
                record["ID_Услуги"] if "ID_Услуги" in record.keys() else None
            )
            start_minute = time_str_to_minutes(time_val)
            end_minute = start_minute + total_duration

            cursor.execute(
                'SELECT "Время_Начала", "Время_Конца" FROM "График работы" '
                'WHERE "ID_Сотрудника"=? AND "Дата"=?',
                (emp_id, date_val)
            )
            shift = cursor.fetchone()
            if not shift:
                messagebox.showerror(
                    "Ошибка",
                    "На выбранную дату для этого сотрудника нет смены в графике.",
                    parent=dialog,
                )
                return
            shift_start = time_str_to_minutes(shift["Время_Начала"])
            shift_end = time_str_to_minutes(shift["Время_Конца"])
            if start_minute < shift_start or end_minute > shift_end:
                messagebox.showerror(
                    "Ошибка",
                    "Суммарная длительность услуг выходит за пределы смены сотрудника.",
                    parent=dialog,
                )
                return

            cursor.execute(
                'SELECT ID, "Время", "ID_Услуги" FROM "Записи" '
                'WHERE "Дата"=? AND "ID_Сотрудника"=? AND ID<>?',
                (date_val, emp_id, record_id)
            )
            existing = cursor.fetchall()
            for ex in existing:
                ex_start = time_str_to_minutes(ex["Время"])
                ex_dur = get_appointment_duration(
                    app.conn,
                    ex["ID"],
                    ex["ID_Услуги"] if "ID_Услуги" in ex.keys() else None
                )
                ex_end = ex_start + ex_dur
                if not (end_minute <= ex_start or start_minute >= ex_end):
                    messagebox.showerror(
                        "Ошибка",
                        f"Сотрудник {emp_val} уже занят c {ex['Время']} до {minutes_to_time_str(ex_end)}.",
                        parent=dialog,
                    )
                    return

            cursor.execute(
                'UPDATE "Записи" SET "Дата"=?, "Время"=?, "ID_Клиента"=?, '
                '"ID_Сотрудника"=? WHERE ID=?',
                (date_val, time_val, cli_id, emp_id, record_id)
            )
            app.conn.commit()
            dialog.destroy()
            app._display_entity_data(entity_name)

        ctk.CTkButton(dialog, text='Сохранить', command=save_record).grid(
            row=row, columnspan=3, pady=10)
        return

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
        app.conn.execute(
            f'UPDATE "{entity_name}" SET {", ".join(updates)} WHERE ID=?',
            vals
        )
        app.conn.commit()
        dialog.destroy()
        app._display_entity_data(entity_name)

    ctk.CTkButton(dialog, text="Сохранить", command=save).grid(
        row=len(data_columns), columnspan=2, pady=10
    )


# ========================= УНИВЕРСАЛЬНОЕ ДОБАВЛЕНИЕ =================

def open_add_record_dialog(app):
    """Универсальный диалог добавления записи"""
    if app.current_entity == "График работы":
        open_add_schedule_dialog(app)
        return
    if app.current_entity == "Финансы":
        open_add_finance_dialog(app)
        return
    if app.current_entity == "Записи":
        open_add_appointment_dialog(app)
        return
    if app.current_entity == "Услуги":
        open_add_service_dialog(app)
        return
    if app.current_entity == "Склад":
        open_add_stock_dialog(app)
        return
    if app.current_entity == "Сотрудники":
        open_add_employee_dialog(app)
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Добавить: {app.current_entity}")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()

    columns = [(c[0], c[1]) for c in app._get_table_columns(app.current_entity) if c[0] != 'ID']
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
        app.conn.execute(
            f'INSERT INTO "{app.current_entity}" ({cols}) VALUES ({qs})',
            vals
        )
        app.conn.commit()
        dialog.destroy()
        app._display_entity_data(app.current_entity)

    ctk.CTkButton(dialog, text="Сохранить", command=save).grid(
        row=len(columns), columnspan=2, pady=10
    )
def open_schedule_date_picker(app):
    top = tk.Toplevel(app)
    top.title("Выберите дату")
    top.transient(app)
    top.grab_set()
    top.geometry("300x320")

    # Центрируем окно
    center_dialog(app, top)

    # Текущая дата для календаря
    cur_date = app.schedule_date.replace(day=1)

    header = tk.Frame(top)
    header.pack(fill="x", pady=4)

    month_label = tk.Label(header, text=cur_date.strftime('%B %Y').capitalize(), font=("Arial", 12, "bold"))
    month_label.pack(side="top", pady=2)

    cal_fr = tk.Frame(top)
    cal_fr.pack(padx=6, pady=6)

    def render(month_date):
        for w in cal_fr.winfo_children():
            w.destroy()
        month_label.config(text=month_date.strftime('%B %Y').capitalize())
        cal = calendar.monthcalendar(month_date.year, month_date.month)

        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for c, d in enumerate(days):
            tk.Label(cal_fr, text=d, width=4, fg="#666666").grid(row=0, column=c)

        for r, week in enumerate(cal, start=1):
            for c, d in enumerate(week):
                if d == 0:
                    tk.Label(cal_fr, text="", width=4).grid(row=r, column=c, padx=2, pady=2)
                    continue

                def on_choose(day=d, md=month_date):
                    chosen = datetime.date(md.year, md.month, day)
                    app.schedule_date = chosen
                    app._display_entity_data("Расписание")
                    top.destroy()

                btn = tk.Button(cal_fr, text=str(d), width=4, command=on_choose)
                if datetime.date.today() == datetime.date(month_date.year, month_date.month, d):
                    btn.config(relief='solid')
                btn.grid(row=r, column=c, padx=2, pady=2)

    def prev_month():
        nonlocal cur_date
        y, m = (cur_date.year, cur_date.month - 1) if cur_date.month > 1 else (cur_date.year - 1, 12)
        cur_date = cur_date.replace(year=y, month=m)
        render(cur_date)

    def next_month():
        nonlocal cur_date
        y, m = (cur_date.year, cur_date.month + 1) if cur_date.month < 12 else (cur_date.year + 1, 1)
        cur_date = cur_date.replace(year=y, month=m)
        render(cur_date)

    nav = tk.Frame(top)
    nav.pack(fill="x", pady=5)
    tk.Button(nav, text="◀", command=prev_month, width=3).pack(side="left", padx=10)
    tk.Button(nav, text="▶", command=next_month, width=3).pack(side="right", padx=10)

    render(cur_date)