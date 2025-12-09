import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk
import tkinter as tk
import datetime
import calendar
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
    cursor.execute('SELECT "Название_Товара", "Количество", "Единица_измерения", "Цена_за_единицу" FROM "Склад" WHERE ID = ?',
                   (item_id,))
    item = cursor.fetchone()
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
    
    # Поле для цены (только для прихода, по умолчанию скрыто)
    price_label = ctk.CTkLabel(dialog, text="Цена за единицу (для прихода):")
    entry_price = ctk.CTkEntry(dialog, placeholder_text=f"Текущая цена: {item_price:.2f}" if item_price else "Укажите цену")
    if item_price:
        entry_price.insert(0, str(item_price))
    # По умолчанию скрываем (так как выбрано "Расход")

    reason_label = ctk.CTkLabel(dialog, text="Причина:")
    reason_label.grid(row=4, column=0, padx=20, pady=10, sticky="w")
    entry_reason = ctk.CTkEntry(dialog, placeholder_text="Напр: Стрижка, Клиент X")
    entry_reason.grid(row=4, column=1, padx=20, pady=10, sticky="ew")
    
    def on_type_change(*args):
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

            # Для прихода - получаем или обновляем цену
            price_to_use = item_price
            if not is_expense:  # Приход
                price_str = entry_price.get()
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
                
                # Обновляем цену в базе
                cursor.execute('UPDATE "Склад" SET "Цена_за_единицу" = ? WHERE ID = ?', (price_to_use, item_id))
                
                # Создаем финансовую запись - расход на закупку
                total_cost = qty_val * price_to_use
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                cursor.execute('INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                              ('Расход', total_cost, today_str, f'Закупка: {item_name} ({qty_val} {unit}) - {reason}'))

            # Обновляем количество
            cursor.execute('UPDATE "Склад" SET "Количество" = ? WHERE ID = ?', (new_qty, item_id))

            # Добавляем запись в историю склада
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            reason_with_price = f"{reason}" if is_expense else f"{reason} (Цена: {price_to_use:.2f} за {unit})"
            cursor.execute(
                'INSERT INTO "История_Склада" ("ID_Товара", "Дата", "Тип", "Количество", "Причина") VALUES (?, ?, ?, ?, ?)',
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
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}", parent=dialog)

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


def open_edit_stock_dialog(app):
    """Диалог редактирования материала на складе"""
    if app.selected_card is None:
        messagebox.showwarning("Предупреждение", "Выберите карточку.")
        return
    
    record_id = app.selected_card.record_id
    cursor = app.conn.cursor()
    cursor.execute('SELECT * FROM "Склад" WHERE ID = ?', (record_id,))
    record = cursor.fetchone()

    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Изменить: {record['Название_Товара']}")
    dialog.geometry("400x300")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)
    
    row = 0
    
    ctk.CTkLabel(dialog, text="Название товара:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.insert(0, str(record['Название_Товара']))
    entry_name.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1
    
    ctk.CTkLabel(dialog, text="Количество:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
    entry_qty = ctk.CTkEntry(dialog)
    entry_qty.insert(0, str(record['Количество']))
    entry_qty.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1
    
    ctk.CTkLabel(dialog, text="Единица измерения:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
    entry_unit = ctk.CTkEntry(dialog)
    entry_unit.insert(0, str(record['Единица_измерения']))
    entry_unit.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1
    
    ctk.CTkLabel(dialog, text="Цена за единицу:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
    entry_price = ctk.CTkEntry(dialog)
    price_value = record['Цена_за_единицу'] if record['Цена_за_единицу'] else 0
    entry_price.insert(0, str(price_value))
    entry_price.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1

    def save():
        name = entry_name.get()
        qty_str = entry_qty.get()
        unit = entry_unit.get()
        price_str = entry_price.get()
        
        if not all([name, qty_str, unit, price_str]):
            messagebox.showwarning("Предупреждение", "Заполните все поля.", parent=dialog)
            return
        
        try:
            qty = float(qty_str.replace(',', '.'))
            price = float(price_str.replace(',', '.'))
            if qty < 0 or price < 0:
                messagebox.showerror("Ошибка", "Количество и цена не могут быть отрицательными.", parent=dialog)
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат числа.", parent=dialog)
            return
        
        cursor.execute('UPDATE "Склад" SET "Название_Товара"=?, "Количество"=?, "Единица_измерения"=?, "Цена_за_единицу"=? WHERE ID=?',
                      (name, qty, unit, price, record_id))
        app.conn.commit()
        messagebox.showinfo("Успех", "Материал обновлен.", parent=dialog)
        dialog.destroy()
        app._display_entity_data("Склад")

    ctk.CTkButton(dialog, text="Сохранить", command=save, fg_color="green").grid(row=row, column=0, columnspan=2, padx=10, pady=20, sticky="ew")


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

    # Дата (выбор через календарь)
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
                lbl = tk.Label(cal_fr, text=d, width=4, fg="#666666")
                lbl.grid(row=0, column=c)
            for r, week in enumerate(cal, start=1):
                for c, d in enumerate(week):
                    if d == 0:
                        lbl = tk.Label(cal_fr, text="", width=4)
                        lbl.grid(row=r, column=c, padx=2, pady=2)
                        continue
                    def on_choose(day=d, md=month_date):
                        chosen = datetime.date(md.year, md.month, day)
                        # Вставляем дату в поле (в формате YYYY-MM-DD)
                        target_entry.configure(state="normal")
                        target_entry.delete(0, tk.END)
                        target_entry.insert(0, str(chosen))
                        target_entry.configure(state="disabled")
                        # Обновляем варианты времени
                        update_time_options()
                        top.destroy()

                    btn = tk.Button(cal_fr, text=str(d), width=4, command=on_choose)
                    if datetime.date.today() == datetime.date(month_date.year, month_date.month, d):
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
        prev_btn = tk.Button(nav, text="◀", command=prev_month, width=3)
        prev_btn.pack(side="left", padx=6)
        next_btn = tk.Button(nav, text="▶", command=next_month, width=3)
        next_btn.pack(side="right", padx=6)

        render(cur_date)

    btn_pick_date.configure(command=lambda: open_date_picker(dialog, entry_date))

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

    # Услуга
    cursor.execute('SELECT ID, "Название" FROM "Услуги" ORDER BY "Название"')
    services = cursor.fetchall()
    service_id_to_name = {s['ID']: s['Название'] for s in services}
    service_name_to_id = {s['Название']: s['ID'] for s in services}
    
    ctk.CTkLabel(dialog, text="Услуга").grid(row=row, column=0, padx=10, pady=5)
    combo_service = ctk.CTkComboBox(dialog, values=list(service_name_to_id.keys()))
    combo_service.grid(row=row, column=1, padx=10, pady=5)
    fields['ID_Услуги'] = combo_service
    row += 1

    # Время - динамическое, зависит от выбранного сотрудника и даты
    ctk.CTkLabel(dialog, text="Время").grid(row=row, column=0, padx=10, pady=5)
    # Показываем простое поле (entry) без стрелки; выбор времени осуществляется кнопкой
    combo_time = ctk.CTkEntry(dialog, state="disabled")
    combo_time.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    # храним доступные слоты в атрибуте ._slots
    combo_time._slots = []
    btn_pick_time = ctk.CTkButton(dialog, text="Выбрать время")
    btn_pick_time.grid(row=row, column=2, padx=6, pady=5)
    fields['Время'] = combo_time
    row += 1

    def update_time_options(*args):
        emp_name = combo_emp.get()
        date_str = entry_date.get()
        emp_id = name_to_id_emp.get(emp_name)
        if not emp_id or not date_str:
            combo_time._slots = []
            return
        cur = app.conn.cursor()
        cur.execute('SELECT "Время_Начала", "Время_Конца" FROM "График работы" WHERE "ID_Сотрудника"=? AND "Дата"=?', (emp_id, date_str))
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
        t = d_start
        while t < d_end:
            times.append(t.strftime(fmt))
            t += step
        combo_time._slots = times
        combo_time.configure(state="normal")
        combo_time.delete(0, tk.END)
        if times:
            combo_time.insert(0, times[0])
        combo_time.configure(state="disabled")

    combo_emp.bind("<<ComboboxSelected>>", lambda e: update_time_options())
    entry_date.bind("<FocusOut>", lambda e: update_time_options())

    # выбор времени теперь осуществляется кнопкой рядом; при клике появляется окно со слотами
    
    def open_time_picker(parent, target_combo):
        """Открывает окно со списком слотов времени (каждые 30 минут).
        Если для выбранного сотрудника и даты есть смена — используем её слоты, иначе полный интервал 08:00-22:00."""
        top = tk.Toplevel(parent)
        top.title("Выберите время")
        top.transient(parent)
        top.grab_set()
        center_dialog(parent, top)

        list_frame = tk.Frame(top)
        list_frame.pack(fill="both", expand=True, padx=6, pady=6)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=20, height=12)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        # Получаем доступные слоты: если смена сотрудника задана, используем update_time_options
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
            t = start
            while t <= end:
                slots.append(t.strftime(fmt))
                t += timedelta(minutes=30)

        for s in slots:
            listbox.insert("end", s)

        def choose_time(evt=None):
            sel = listbox.curselection()
            if not sel:
                return
            value = listbox.get(sel[0])
            target_combo.set(value)
            top.destroy()

        listbox.bind('<Double-Button-1>', choose_time)

        btn_frame = tk.Frame(top)
        btn_frame.pack(fill="x", pady=6)
        ok_btn = tk.Button(btn_frame, text="OK", command=choose_time)
        ok_btn.pack(side="right", padx=6)

    btn_pick_time.configure(command=lambda: open_time_picker(dialog, combo_time))

    # Сохранение
    def save():
        date_val = fields['Дата'].get()
        emp_val = combo_emp.get()
        cli_val = combo_cli.get()
        time_val = fields['Время'].get()
        service_name = combo_service.get()
        
        if not all([date_val, emp_val, cli_val, time_val, service_name]):
            messagebox.showwarning("!", "Заполните все поля и выберите время, согласно смене сотрудника.")
            return

        # Проверка формата времени и диапазона (включительно 08:00 - 22:00)
        try:
            parts = time_val.split(":")
            if len(parts) != 2:
                raise ValueError()
            hour = int(parts[0])
            minute = int(parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError()
        except Exception:
            messagebox.showerror("Ошибка", "Неверный формат времени. Используйте HH:MM.", parent=dialog)
            return

        # Запрет времени раньше 08:00 и позже 22:00 (22:00 допустимо, 22:01 — нет)
        if hour < 8 or hour > 22 or (hour == 22 and minute > 0):
            messagebox.showerror("Ошибка", "Время должно быть в интервале 08:00–22:00 (включительно).", parent=dialog)
            return

        # Приводим к шаблону HH:MM
        time_val = f"{hour:02d}:{minute:02d}"
        
        emp_id = name_to_id_emp.get(emp_val)
        cli_id = name_to_id_cli.get(cli_val)
        service_id = service_name_to_id.get(service_name)
        
        if not service_id:
            messagebox.showerror("Ошибка", "Услуга не найдена.")
            return
        
        # Создаем запись
        cursor.execute('INSERT INTO "Записи" ("Дата","Время","ID_Клиента","ID_Сотрудника","ID_Услуги") VALUES (?,?,?,?,?)',
                      (date_val, time_val, cli_id, emp_id, service_id))
        
        # Автоматически списываем материалы со склада
        cursor.execute('SELECT "ID_Материала", "Количество" FROM "Расход_Материалов" WHERE "ID_Услуги"=?', (service_id,))
        material_expenses = cursor.fetchall()
        
        insufficient_materials = []
        for mat_expense in material_expenses:
            mat_id = mat_expense['ID_Материала']
            required_qty = mat_expense['Количество']
            
            # Получаем текущее количество материала
            cursor.execute('SELECT "Количество", "Название_Товара" FROM "Склад" WHERE ID=?', (mat_id,))
            mat_info = cursor.fetchone()
            if not mat_info:
                continue
            
            current_qty = mat_info['Количество']
            mat_name = mat_info['Название_Товара']
            
            if current_qty < required_qty:
                insufficient_materials.append(f"{mat_name} (требуется: {required_qty}, доступно: {current_qty})")
                continue
            
            # Списываем материал
            new_qty = current_qty - required_qty
            cursor.execute('UPDATE "Склад" SET "Количество"=? WHERE ID=?', (new_qty, mat_id))
            
            # Добавляем запись в историю склада
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            service_full_name = service_name
            client_name = cli_val
            reason = f"Услуга: {service_full_name}, Клиент: {client_name}"
            cursor.execute('INSERT INTO "История_Склада" ("ID_Товара", "Дата", "Тип", "Количество", "Причина") VALUES (?, ?, ?, ?, ?)',
                          (mat_id, today_str, "Расход", required_qty, reason))
        
        app.conn.commit()
        
        if insufficient_materials:
            messagebox.showwarning("Внимание", 
                                 f"Запись создана, но недостаточно материалов:\n" + "\n".join(insufficient_materials),
                                 parent=dialog)
        else:
            messagebox.showinfo("Успех", "Запись создана. Материалы списаны со склада.", parent=dialog)
        
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


def open_add_service_dialog(app):
    """Диалог добавления услуги с выбором материалов"""
    dialog = ctk.CTkToplevel(app)
    dialog.title("Добавить: Услуга")
    dialog.geometry("600x500")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)
    
    row = 0
    
    # Название
    ctk.CTkLabel(dialog, text="Название:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1
    
    # Цена
    ctk.CTkLabel(dialog, text="Цена:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry_price = ctk.CTkEntry(dialog)
    entry_price.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1
    
    # Длительность
    ctk.CTkLabel(dialog, text="Длительность (мин):").grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry_duration = ctk.CTkEntry(dialog)
    entry_duration.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1
    
    # Заголовок для материалов
    ctk.CTkLabel(dialog, text="Расход материалов:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=row, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
    row += 1
    
    # Фрейм для списка материалов
    materials_frame = ctk.CTkScrollableFrame(dialog, height=200)
    materials_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
    materials_frame.grid_columnconfigure(1, weight=1)
    row += 1
    
    # Получаем список материалов со склада
    cursor = app.conn.cursor()
    cursor.execute('SELECT ID, "Название_Товара", "Единица_измерения" FROM "Склад" ORDER BY "Название_Товара"')
    materials = cursor.fetchall()
    
    material_widgets = {}  # ID материала -> (combo, entry)
    
    # Кнопка добавления материала
    def add_material_row():
        mat_row = len(material_widgets)
        
        # Выбор материала
        material_names = [f"{m['Название_Товара']} ({m['Единица_измерения']})" for m in materials]
        if not material_names:
            messagebox.showwarning("Предупреждение", "Нет материалов на складе. Сначала добавьте материалы.", parent=dialog)
            return
        
        combo_material = ctk.CTkComboBox(materials_frame, values=material_names, width=250)
        combo_material.grid(row=mat_row, column=0, padx=5, pady=2, sticky="ew")
        
        # Количество
        entry_qty = ctk.CTkEntry(materials_frame, width=100, placeholder_text="0.0")
        entry_qty.grid(row=mat_row, column=1, padx=5, pady=2, sticky="ew")
        
        # Кнопка удаления
        def remove_row(mat_id=mat_row):
            combo_material.grid_remove()
            entry_qty.grid_remove()
            btn_remove.grid_remove()
            material_widgets.pop(mat_id, None)
        
        btn_remove = ctk.CTkButton(materials_frame, text="✖", width=30, fg_color="red", command=remove_row)
        btn_remove.grid(row=mat_row, column=2, padx=5, pady=2)
        
        material_widgets[mat_row] = (combo_material, entry_qty, btn_remove)
    
    btn_add_material = ctk.CTkButton(dialog, text="➕ Добавить материал", command=add_material_row)
    btn_add_material.grid(row=row, column=0, columnspan=2, padx=10, pady=5)
    row += 1
    
    def save():
        name = entry_name.get()
        price_str = entry_price.get()
        duration_str = entry_duration.get()
        
        if not all([name, price_str, duration_str]):
            messagebox.showwarning("Предупреждение", "Заполните все основные поля.", parent=dialog)
            return
        
        try:
            price = float(price_str.replace(',', '.'))
            duration = int(duration_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат цены или длительности.", parent=dialog)
            return
        
        # Сохраняем услугу
        cursor.execute('INSERT INTO "Услуги" ("Название", "Цена", "Длительность") VALUES (?, ?, ?)',
                      (name, price, duration))
        service_id = cursor.lastrowid
        
        # Сохраняем расход материалов
        for mat_row, (combo, entry_qty, _) in material_widgets.items():
            material_name_unit = combo.get()
            if not material_name_unit:
                continue
            
            qty_str = entry_qty.get()
            if not qty_str:
                continue
            
            try:
                qty = float(qty_str.replace(',', '.'))
                if qty <= 0:
                    continue
            except ValueError:
                continue
            
            # Находим ID материала
            material_name = material_name_unit.split(' (')[0]
            material_id = None
            for m in materials:
                if m['Название_Товара'] == material_name:
                    material_id = m['ID']
                    break
            
            if material_id:
                cursor.execute('INSERT INTO "Расход_Материалов" ("ID_Услуги", "ID_Материала", "Количество") VALUES (?, ?, ?)',
                              (service_id, material_id, qty))
        
        app.conn.commit()
        messagebox.showinfo("Успех", "Услуга добавлена.", parent=dialog)
        dialog.destroy()
        app._display_entity_data("Услуги")
    
    ctk.CTkButton(dialog, text="Сохранить", command=save, fg_color="green").grid(row=row, column=0, columnspan=2, padx=10, pady=10)


def open_add_employee_dialog(app):
    """Диалог добавления сотрудника с выбором услуг (чекбоксы)"""
    dialog = ctk.CTkToplevel(app)
    dialog.title("Добавить: Сотрудник")
    dialog.geometry("500x450")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    cursor = app.conn.cursor()

    # Поля: Имя, Должность (combobox с существующими должностями), Телефон
    ctk.CTkLabel(dialog, text="Имя:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

    # Подгружаем уникальные должности из существующих сотрудников для удобства
    cursor.execute('SELECT DISTINCT "Должность" FROM "Сотрудники" WHERE "Должность" IS NOT NULL AND "Должность" <> ""')
    existing_positions = [r[0] for r in cursor.fetchall()]
    ctk.CTkLabel(dialog, text="Должность:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
    combo_pos = ctk.CTkComboBox(dialog, values=existing_positions)
    combo_pos.grid(row=1, column=1, padx=10, pady=8, sticky="ew")

    ctk.CTkLabel(dialog, text="Телефон:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
    entry_phone = ctk.CTkEntry(dialog)
    entry_phone.grid(row=2, column=1, padx=10, pady=8, sticky="ew")

    # Список услуг с чекбоксами
    ctk.CTkLabel(dialog, text="Назначить услуги (выберите):", font=ctk.CTkFont(size=12, weight="bold")).grid(row=3, column=0, columnspan=2, padx=10, pady=(12, 4), sticky="w")

    services_frame = ctk.CTkScrollableFrame(dialog, height=220)
    services_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=4, sticky="ew")
    services_frame.grid_columnconfigure(0, weight=1)

    cursor.execute('SELECT ID, "Название" FROM "Услуги" ORDER BY "Название"')
    services = cursor.fetchall()
    service_vars = []  # list of (service_id, tk.IntVar)

    for i, s in enumerate(services):
        var = tk.IntVar()
        chk = ctk.CTkCheckBox(services_frame, text=s['Название'], variable=var)
        chk.grid(row=i, column=0, sticky="w", padx=8, pady=2)
        service_vars.append((s['ID'], var))

    def save():
        name = entry_name.get().strip()
        position = combo_pos.get().strip()
        phone = entry_phone.get().strip()

        if not name:
            messagebox.showwarning("Внимание", "Укажите имя сотрудника.", parent=dialog)
            return

        # Вставляем сотрудника
        cur = app.conn.cursor()
        cur.execute('INSERT INTO "Сотрудники" ("Имя", "Должность", "Телефон") VALUES (?, ?, ?)',
                    (name, position, phone))
        emp_id = cur.lastrowid

        # Вставляем связи сотрудник->услуга
        for sid, var in service_vars:
            try:
                if var.get():
                    cur.execute('INSERT INTO "Сотрудник_Услуги" ("ID_Сотрудника", "ID_Услуги") VALUES (?, ?)', (emp_id, sid))
            except Exception:
                continue

        app.conn.commit()
        messagebox.showinfo("Успех", "Сотрудник добавлен и назначены услуги (если выбраны).", parent=dialog)
        dialog.destroy()
        app._display_entity_data("Сотрудники")

    ctk.CTkButton(dialog, text="Сохранить", command=save, fg_color="green").grid(row=5, column=0, columnspan=2, padx=10, pady=12, sticky="ew")

def open_edit_service_dialog(app):
    """Диалог редактирования услуги с выбором материалов"""
    if app.selected_card is None:
        messagebox.showwarning("Предупреждение", "Выберите услугу.")
        return
    
    service_id = app.selected_card.record_id
    cursor = app.conn.cursor()
    cursor.execute('SELECT * FROM "Услуги" WHERE ID = ?', (service_id,))
    service = cursor.fetchone()
    
    if not service:
        return
    
    dialog = ctk.CTkToplevel(app)
    dialog.title(f"Изменить: {service['Название']}")
    dialog.geometry("600x500")
    center_dialog(app, dialog)
    dialog.transient(app)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)
    
    row = 0
    
    # Название
    ctk.CTkLabel(dialog, text="Название:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.insert(0, str(service['Название']))
    entry_name.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1
    
    # Цена
    ctk.CTkLabel(dialog, text="Цена:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry_price = ctk.CTkEntry(dialog)
    entry_price.insert(0, str(service['Цена']))
    entry_price.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1
    
    # Длительность
    ctk.CTkLabel(dialog, text="Длительность (мин):").grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry_duration = ctk.CTkEntry(dialog)
    entry_duration.insert(0, str(service['Длительность']))
    entry_duration.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
    row += 1
    
    # Заголовок для материалов
    ctk.CTkLabel(dialog, text="Расход материалов:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=row, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
    row += 1
    
    # Фрейм для списка материалов
    materials_frame = ctk.CTkScrollableFrame(dialog, height=200)
    materials_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
    materials_frame.grid_columnconfigure(1, weight=1)
    row += 1
    
    # Получаем список материалов со склада
    cursor.execute('SELECT ID, "Название_Товара", "Единица_измерения" FROM "Склад" ORDER BY "Название_Товара"')
    materials = cursor.fetchall()
    
    # Получаем существующие расходы материалов для этой услуги
    cursor.execute('SELECT "ID_Материала", "Количество" FROM "Расход_Материалов" WHERE "ID_Услуги" = ?', (service_id,))
    existing_materials = {row['ID_Материала']: row['Количество'] for row in cursor.fetchall()}
    
    material_widgets = {}  # ID материала -> (combo, entry, btn)
    
    # Заполняем существующие материалы
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
        
        def remove_row(mat_id=mat_row):
            combo_material.grid_remove()
            entry_qty.grid_remove()
            btn_remove.grid_remove()
            material_widgets.pop(mat_id, None)
        
        btn_remove = ctk.CTkButton(materials_frame, text="✖", width=30, fg_color="red", command=remove_row)
        btn_remove.grid(row=mat_row, column=2, padx=5, pady=2)
        
        material_widgets[mat_row] = (combo_material, entry_qty, btn_remove, mat_id)
    
    # Кнопка добавления материала
    def add_material_row():
        mat_row = len(material_widgets)
        material_names = [f"{m['Название_Товара']} ({m['Единица_измерения']})" for m in materials]
        if not material_names:
            messagebox.showwarning("Предупреждение", "Нет материалов на складе.", parent=dialog)
            return
        
        combo_material = ctk.CTkComboBox(materials_frame, values=material_names, width=250)
        combo_material.grid(row=mat_row, column=0, padx=5, pady=2, sticky="ew")
        
        entry_qty = ctk.CTkEntry(materials_frame, width=100, placeholder_text="0.0")
        entry_qty.grid(row=mat_row, column=1, padx=5, pady=2, sticky="ew")
        
        def remove_row(mat_id=mat_row):
            combo_material.grid_remove()
            entry_qty.grid_remove()
            btn_remove.grid_remove()
            material_widgets.pop(mat_id, None)
        
        btn_remove = ctk.CTkButton(materials_frame, text="✖", width=30, fg_color="red", command=remove_row)
        btn_remove.grid(row=mat_row, column=2, padx=5, pady=2)
        
        material_widgets[mat_row] = (combo_material, entry_qty, btn_remove, None)
    
    btn_add_material = ctk.CTkButton(dialog, text="➕ Добавить материал", command=add_material_row)
    btn_add_material.grid(row=row, column=0, columnspan=2, padx=10, pady=5)
    row += 1
    
    def save():
        name = entry_name.get()
        price_str = entry_price.get()
        duration_str = entry_duration.get()
        
        if not all([name, price_str, duration_str]):
            messagebox.showwarning("Предупреждение", "Заполните все основные поля.", parent=dialog)
            return
        
        try:
            price = float(price_str.replace(',', '.'))
            duration = int(duration_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат цены или длительности.", parent=dialog)
            return
        
        # Обновляем услугу
        cursor.execute('UPDATE "Услуги" SET "Название"=?, "Цена"=?, "Длительность"=? WHERE ID=?',
                      (name, price, duration, service_id))
        
        # Удаляем старые расходы материалов
        cursor.execute('DELETE FROM "Расход_Материалов" WHERE "ID_Услуги"=?', (service_id,))
        
        # Добавляем новые расходы материалов
        for mat_row, widgets in material_widgets.items():
            if len(widgets) == 4:
                combo, entry_qty, _, old_mat_id = widgets
            else:
                combo, entry_qty, _ = widgets
                old_mat_id = None
            material_name_unit = combo.get()
            if not material_name_unit:
                continue
            
            qty_str = entry_qty.get()
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
                cursor.execute('INSERT INTO "Расход_Материалов" ("ID_Услуги", "ID_Материала", "Количество") VALUES (?, ?, ?)',
                              (service_id, material_id, qty))
        
        app.conn.commit()
        messagebox.showinfo("Успех", "Услуга обновлена.", parent=dialog)
        dialog.destroy()
        app._display_entity_data("Услуги")
    
    ctk.CTkButton(dialog, text="Сохранить", command=save, fg_color="green").grid(row=row, column=0, columnspan=2, padx=10, pady=10)


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
    
    # Название товара
    ctk.CTkLabel(dialog, text="Название товара:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
    entry_name = ctk.CTkEntry(dialog)
    entry_name.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1
    
    # Количество
    ctk.CTkLabel(dialog, text="Количество:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
    entry_qty = ctk.CTkEntry(dialog)
    entry_qty.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1
    
    # Единица измерения
    ctk.CTkLabel(dialog, text="Единица измерения:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
    entry_unit = ctk.CTkEntry(dialog, placeholder_text="шт, литр, кг, упаковка и т.д.")
    entry_unit.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1
    
    # Цена за единицу
    ctk.CTkLabel(dialog, text="Цена за единицу:").grid(row=row, column=0, padx=10, pady=10, sticky="w")
    entry_price = ctk.CTkEntry(dialog, placeholder_text="Например: 150.50")
    entry_price.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
    row += 1
    
    def save():
        name = entry_name.get()
        qty_str = entry_qty.get()
        unit = entry_unit.get()
        price_str = entry_price.get()
        
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
        # Добавляем материал на склад
        cursor.execute('INSERT INTO "Склад" ("Название_Товара", "Количество", "Единица_измерения", "Цена_за_единицу") VALUES (?, ?, ?, ?)',
                      (name, qty, unit, price))
        
        # Создаем финансовую запись - расход на закупку
        total_cost = qty * price
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        cursor.execute('INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                      ('Расход', total_cost, today_str, f'Закупка материала: {name} ({qty} {unit})'))
        
        # Добавляем запись в историю склада
        item_id = cursor.lastrowid
        cursor.execute('INSERT INTO "История_Склада" ("ID_Товара", "Дата", "Тип", "Количество", "Причина") VALUES (?, ?, ?, ?, ?)',
                      (item_id, today_str, 'Приход', qty, f'Первоначальное поступление (Цена: {price} за {unit})'))
        
        app.conn.commit()
        messagebox.showinfo("Успех", f"Материал добавлен. Создан расход в финансах: {total_cost:.2f} руб.", parent=dialog)
        dialog.destroy()
        app._display_entity_data("Склад")
    
    ctk.CTkButton(dialog, text="Сохранить", command=save, fg_color="green").grid(row=row, column=0, columnspan=2, padx=10, pady=20, sticky="ew")


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
    # Универсальная генерация формы для остальных сущностей (в том числе Клиенты)
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

