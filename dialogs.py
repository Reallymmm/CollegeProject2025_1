import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk
import datetime
from datetime import timedelta


def center_dialog(parent, dialog):
    """Центрирует диалоговое окно относительно главного окна"""
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
    cursor.execute('SELECT "Название_Товара", "Количество", "Единица_измерения" FROM "Склад" WHERE ID = ?',
                   (item_id,))
    item = cursor.fetchone()
    item_name = item['Название_Товара']
    current_qty = item['Количество']
    unit = item['Единица_измерения']

    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Движение товара: {item_name}")
    dialog.geometry("400x350")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
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

            app.conn.execute('UPDATE "Склад" SET "Количество" = ? WHERE ID = ?', (new_qty, item_id))

            today_str = datetime.date.today().strftime("%Y-%m-%d")
            app.conn.execute(
                'INSERT INTO "История_Склада" ("ID_Товара", "Дата", "Тип", "Количество", "Причина") VALUES (?, ?, ?, ?, ?)',
                (item_id, today_str, op_type_db, qty_val, reason)
            )
            app.conn.commit()

            messagebox.showinfo("Успех", f"Новый остаток: {new_qty} {unit}", parent=dialog)
            dialog.destroy()
            app._display_entity_data("Склад")

        except ValueError:
            messagebox.showerror("Ошибка", "Неверное число.", parent=dialog)

    ctk.CTkButton(dialog, text="Выполнить", command=confirm, fg_color="green").grid(row=5, column=0, columnspan=2,
                                                                                    padx=20, pady=20, sticky="ew")


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
    style.configure("Treeview", background="#2a2d2e", fieldbackground="#2a2d2e", foreground="white", rowheight=25)
    style.configure("Treeview.Heading", background="#3A8FCD", foreground="white")

    tree = ttk.Treeview(history_win, columns=("Дата", "Тип", "Товар", "Кол", "Ед", "Причина"), show="headings")
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
        summa_str = fields["Сумма"].get()
        data_str = fields["Дата"].get()
        opisanie = fields["Описание"].get()

        if not all([tip, summa_str, data_str, opisanie]):
            messagebox.showwarning("Предупреждение", "Заполните все поля.", parent=dialog)
            return
        try:
            summa = float(summa_str.replace(',', '.'))
            app.conn.execute('INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                              (tip, summa, data_str, opisanie))
            app.conn.commit()
            messagebox.showinfo("Успех", "Добавлено.", parent=dialog)
            dialog.destroy()
            app._display_entity_data("Финансы")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=dialog)

    ctk.CTkButton(dialog, text="Сохранить", command=save_finance_record, fg_color="green").grid(row=4, columnspan=2,
                                                                                                pady=20,
                                                                                                sticky="ew")


def open_edit_record_dialog(app):
    """Диалог редактирования записи"""
    if app.selected_card is None:
        messagebox.showwarning("Предупреждение", "Выберите карточку.")
        return
    if app.current_entity in ["График работы", "Расписание", "Финансы"]:
        messagebox.showwarning("Предупреждение", "Редактирование здесь не поддерживается.")
        return

    record_id = app.selected_card.record_id
    entity_name = app.current_entity
    columns = app._get_table_columns(entity_name)
    data_columns = [(name, type_) for name, type_ in columns if name.upper() != 'ID']

    cursor = app.conn.cursor()
    cursor.execute(f'SELECT * FROM "{entity_name}" WHERE ID = ?', (record_id,))
    record = cursor.fetchone()

    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Изменить #{record_id}")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
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
        app.conn.execute(f'UPDATE "{entity_name}" SET {", ".join(updates)} WHERE ID=?', vals)
        app.conn.commit()
        dialog.destroy()
        app._display_entity_data(entity_name)

    ctk.CTkButton(dialog, text="Сохранить", command=save).grid(row=len(data_columns), columnspan=2, pady=10)


def open_add_appointment_dialog(app):
    """Диалог добавления записи (appointment)"""
    dialog = ctk.CTkToplevel(app)
    dialog.title("Добавить: Запись")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    # Получение справочников
    name_to_id_emp, id_to_name_emp = app._get_employee_map()
    cursor = app.conn.cursor()
    cursor.execute('SELECT "ID", "Имя" FROM "Клиенты"')
    clients = cursor.fetchall()
    name_to_id_cli = {c['Имя']: c['ID'] for c in clients}
    
    fields = {}
    row = 0

    # Дата
    ctk.CTkLabel(dialog, text="Дата").grid(row=row, column=0, padx=10, pady=5)
    entry_date = ctk.CTkEntry(dialog)
    entry_date.insert(0, str(datetime.date.today()))
    fields['Дата'] = entry_date
    entry_date.grid(row=row, column=1, padx=10, pady=5)
    row += 1

    # Сотрудник
    ctk.CTkLabel(dialog, text="Сотрудник").grid(row=row, column=0, padx=10, pady=5)
    combo_emp = ctk.CTkComboBox(dialog, values=list(name_to_id_emp.keys()))
    combo_emp.grid(row=row, column=1, padx=10, pady=5)
    fields['ID_Сотрудника'] = combo_emp
    row += 1

    # Клиент
    ctk.CTkLabel(dialog, text="Клиент").grid(row=row, column=0, padx=10, pady=5)
    combo_cli = ctk.CTkComboBox(dialog, values=list(name_to_id_cli.keys()))
    combo_cli.grid(row=row, column=1, padx=10, pady=5)
    fields['ID_Клиента'] = combo_cli
    row += 1

    # Время - динамическое, зависит от выбранного сотрудника и даты
    ctk.CTkLabel(dialog, text="Время").grid(row=row, column=0, padx=10, pady=5)
    combo_time = ctk.CTkComboBox(dialog, values=[])  # до выбора сотрудников пусто
    combo_time.grid(row=row, column=1, padx=10, pady=5)
    fields['Время'] = combo_time
    row += 1

    def update_time_options(*args):
        emp_name = combo_emp.get()
        date_str = entry_date.get()
        emp_id = name_to_id_emp.get(emp_name)
        if not emp_id or not date_str:
            combo_time.configure(values=[])
            return
        cur = app.conn.cursor()
        cur.execute('SELECT "Время_Начала", "Время_Конца" FROM "График работы" WHERE "ID_Сотрудника"=? AND "Дата"=?', (emp_id, date_str))
        res = cur.fetchone()
        if not res:
            combo_time.configure(values=[])
            combo_time.set("")
            return
        t_start, t_end = res['Время_Начала'], res['Время_Конца']
        fmt = "%H:%M"
        d_start = datetime.datetime.strptime(t_start, fmt)
        d_end = datetime.datetime.strptime(t_end, fmt)
        times = []
        step = timedelta(minutes=30)
        t = d_start
        while t < d_end:
            times.append(t.strftime(fmt))
            t += step
        combo_time.configure(values=times)
        if times:
            combo_time.set(times[0])
        else:
            combo_time.set("")

    combo_emp.bind("<<ComboboxSelected>>", lambda e: update_time_options())
    entry_date.bind("<FocusOut>", lambda e: update_time_options())

    # Сохранение
    def save():
        date_val = fields['Дата'].get()
        emp_val = combo_emp.get()
        cli_val = combo_cli.get()
        time_val = fields['Время'].get()
        if not all([date_val, emp_val, cli_val, time_val]):
            messagebox.showwarning("!", "Заполните все поля и выберите время, согласно смене сотрудника.")
            return
        emp_id = name_to_id_emp.get(emp_val)
        cli_id = name_to_id_cli.get(cli_val)
        app.conn.execute('INSERT INTO "Записи" ("Дата","Время","ID_Клиента","ID_Сотрудника") VALUES (?,?,?,?)',
                        (date_val, time_val, cli_id, emp_id))
        app.conn.commit()
        dialog.destroy()
        app._display_entity_data(app.current_entity)
    ctk.CTkButton(dialog, text="Сохранить", command=save).grid(row=row, columnspan=2, pady=10)


def open_add_schedule_dialog(app):
    """Диалог добавления смены в график работы"""
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
            'INSERT INTO "График работы" ("ID_Сотрудника", "Дата", "Время_Начала", "Время_Конца") VALUES (?,?,?,?)',
            (eid, e_date.get(), e_start.get(), e_end.get()))
        app.conn.commit()
        dialog.destroy()
        app._display_entity_data("График работы")

    ctk.CTkButton(dialog, text="ОК", command=save).pack(pady=10)


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
    # Универсальная генерация формы для остальных сущностей (в том числе Сотрудники, Клиенты)
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
        app.conn.execute(f'INSERT INTO "{app.current_entity}" ({cols}) VALUES ({qs})', vals)
        app.conn.commit()
        dialog.destroy()
        app._display_entity_data(app.current_entity)
    ctk.CTkButton(dialog, text="Сохранить", command=save).grid(row=len(columns), columnspan=2, pady=10)

