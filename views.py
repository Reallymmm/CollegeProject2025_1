import customtkinter as ctk
import datetime
import calendar
import tkinter as tk
from tkinter import messagebox


def get_monthly_finance_data(conn, target_date):
    """Получить финансовые данные за месяц"""
    year, month = target_date.year, target_date.month
    start_date = datetime.date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = datetime.date(year, month, last_day)

    cursor = conn.cursor()
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


def display_finance_report_view(app):
    """Отображение финансового отчета"""
    from dialogs import open_add_finance_dialog
    
    app.top_controls.grid_columnconfigure((0, 1, 2, 3), weight=0)
    app.top_controls.grid_columnconfigure(0, weight=1)
    app.top_controls.grid_columnconfigure(1, weight=2)
    app.top_controls.grid_columnconfigure(2, weight=1)
    app.top_controls.grid_columnconfigure(3, weight=1)

    ctk.CTkButton(app.top_controls, text="< Пред.", command=lambda: app.change_finance_month(-1)).grid(row=0,
                                                                                                         column=0,
                                                                                                         padx=5,
                                                                                                         sticky="w")
    month_name = app.finance_date.strftime("%B %Y").capitalize()
    ctk.CTkLabel(app.top_controls, text=month_name, font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=1,
                                                                                                    sticky="ew")
    ctk.CTkButton(app.top_controls, text="След. >", command=lambda: app.change_finance_month(1)).grid(row=0,
                                                                                                        column=3,
                                                                                                        padx=5,
                                                                                                        sticky="e")
    ctk.CTkButton(app.top_controls, text="➕ Добавить", fg_color="green",
                  command=lambda: open_add_finance_dialog(app)).grid(row=0, column=2, padx=5, sticky="ew")

    finance_data = get_monthly_finance_data(app.conn, app.finance_date)
    for widget in app.scrollable_cards_frame.winfo_children():
        widget.destroy()
    app.scrollable_cards_frame.configure(label_text=f"Финансы ({len(finance_data['transactions'])} операций)")

    summary_frame = ctk.CTkFrame(app.scrollable_cards_frame, fg_color="transparent")
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
        fr = ctk.CTkFrame(app.scrollable_cards_frame)
        fr.grid(row=i + 2, column=0, sticky="ew", padx=10, pady=2)
        ctk.CTkLabel(fr, text=trans['Дата']).pack(side="left", padx=10)
        color = "#32CD32" if trans['Тип'] == 'Доход' else "#FF4500"
        ctk.CTkLabel(fr, text=f"{trans['Сумма']:,.2f}", text_color=color).pack(side="left", padx=10)
        ctk.CTkLabel(fr, text=trans['Описание']).pack(side="left", padx=10)


def get_schedule_data(conn, calendar_date, get_employee_map_func):
    """Получить данные графика работы за месяц"""
    _, id_to_name = get_employee_map_func()
    start = calendar_date.replace(day=1)
    _, last = calendar.monthrange(start.year, start.month)
    end = start.replace(day=last)
    cur = conn.cursor()
    cur.execute('SELECT * FROM "График работы" WHERE Дата BETWEEN ? AND ?', (str(start), str(end)))
    data = {}
    for r in cur.fetchall():
        s = f"{id_to_name.get(r['ID_Сотрудника'], '?')}: {r['Время_Начала']}-{r['Время_Конца']}"
        data.setdefault(r['Дата'], []).append(s)
    return data


def display_calendar_view(app, entity_name, schedule_data):
    """Отображение календаря графика работы"""
    from dialogs import open_add_schedule_dialog
    
    for w in app.top_controls.winfo_children():
        w.destroy()
    app.top_controls.grid_columnconfigure(0, weight=1)
    app.top_controls.grid_columnconfigure(1, weight=2)
    app.top_controls.grid_columnconfigure(3, weight=1)
    ctk.CTkButton(app.top_controls, text="<", command=lambda: app.change_calendar_month(-1)).grid(row=0, column=0)
    ctk.CTkLabel(app.top_controls, text=app.calendar_date.strftime("%B %Y"), font=("Arial", 18, "bold")).grid(
        row=0, column=1)
    ctk.CTkButton(app.top_controls, text=">", command=lambda: app.change_calendar_month(1)).grid(row=0, column=3)
    ctk.CTkButton(app.top_controls, text="➕ Смена", command=lambda: open_add_schedule_dialog(app)).grid(row=0, column=2)

    for w in app.scrollable_cards_frame.winfo_children():
        w.destroy()
    cal_fr = ctk.CTkFrame(app.scrollable_cards_frame)
    cal_fr.pack(fill="both", expand=True)
    for i in range(7):
        cal_fr.columnconfigure(i, weight=1)
    cal = calendar.monthcalendar(app.calendar_date.year, app.calendar_date.month)
    for r, week in enumerate(cal):
        for c, d in enumerate(week):
            if d == 0:
                continue
            cell = ctk.CTkFrame(cal_fr, border_width=1)
            cell.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
            ctk.CTkLabel(cell, text=str(d), font=("Arial", 12, "bold")).pack(anchor="nw")
            ds = str(datetime.date(app.calendar_date.year, app.calendar_date.month, d))
            if ds in schedule_data:
                for shift in schedule_data[ds]:
                    ctk.CTkLabel(cell, text=shift, font=("Arial", 10)).pack()


def get_appointment_data(conn, date, get_employee_map_func):
    """Получить данные записей на дату"""
    _, id_to_name_emp = get_employee_map_func()
    cur = conn.cursor()
    cur.execute('SELECT ID, Имя FROM "Клиенты"')
    cl_map = {r['ID']: r['Имя'] for r in cur.fetchall()}
    cur.execute('SELECT * FROM "Записи" WHERE Дата=? ORDER BY Время', (str(date),))
    return [{'time': r['Время'],
             'details': f"Кл: {cl_map.get(r['ID_Клиента'], '?')}, Сотр: {id_to_name_emp.get(r['ID_Сотрудника'], '?')}",
             'id': r['ID']} for r in cur.fetchall()]


def display_schedule_view(app, appointments, date):
    """Отображение расписания на день"""
    for w in app.top_controls.winfo_children():
        w.destroy()
    app.top_controls.grid_columnconfigure(0, weight=1)
    app.top_controls.grid_columnconfigure(1, weight=2)
    app.top_controls.grid_columnconfigure(2, weight=0)
    # Выбор даты через календарь вместо перемещения стрелками
    ctk.CTkButton(app.top_controls, text="Выбрать дату", command=lambda: open_schedule_date_picker(app)).grid(row=0, column=0, padx=5, sticky="w")
    ctk.CTkLabel(app.top_controls, text=date.strftime("%d %B %Y"), font=("Arial", 18)).grid(row=0, column=1)

    for w in app.scrollable_cards_frame.winfo_children():
        w.destroy()
    sch_fr = ctk.CTkFrame(app.scrollable_cards_frame)
    sch_fr.pack(fill="both", expand=True)
    sch_fr.columnconfigure(1, weight=1)
    for i, h in enumerate(range(7, 23)):
        ts = f"{h:02d}:00"
        ctk.CTkLabel(sch_fr, text=ts).grid(row=i, column=0, padx=10)
        slot = ctk.CTkFrame(sch_fr, height=40, border_width=1)
        slot.grid(row=i, column=1, sticky="ew", pady=1)
        for app_item in appointments:
            if app_item['time'].startswith(f"{h:02d}"):
                ctk.CTkLabel(slot, text=f"[{app_item['time']}] {app_item['details']}", fg_color="#3A8FCD").pack(fill="x", pady=1)


def open_schedule_date_picker(app):
    """Открывает простое окно-календарь для выбора даты расписания."""
    top = tk.Toplevel(app)
    top.title("Выберите дату")
    top.transient(app)
    top.grab_set()

    # Текущая отображаемая месячная дата в пикере
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
        # Weekday headers
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
                    app.schedule_date = chosen
                    app._display_entity_data("Расписание")
                    top.destroy()

                btn = tk.Button(cal_fr, text=str(d), width=4, command=on_choose)
                # Highlight today's date
                if datetime.date.today() == datetime.date(month_date.year, month_date.month, d):
                    btn.config(relief='solid')
                btn.grid(row=r, column=c, padx=2, pady=2)

    # Навигация по месяцам внутри пикера
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


def complete_appointment(app, record_id):
    """Отметить запись как завершённую и записать прибыль в таблицу Финансы."""
    cur = app.conn.cursor()
    cur.execute('SELECT * FROM "Записи" WHERE ID = ?', (record_id,))
    rec = cur.fetchone()
    if not rec:
        messagebox.showerror("Ошибка", "Запись не найдена.")
        return

    service_id = rec['ID_Услуги']
    date = rec['Дата']

    service_price = 0.0
    service_name = ''
    if service_id:
        cur.execute('SELECT "Цена", "Название" FROM "Услуги" WHERE ID = ?', (service_id,))
        s = cur.fetchone()
        if s:
            try:
                service_price = float(s['Цена']) if s['Цена'] is not None else 0.0
            except:
                service_price = 0.0
            service_name = s['Название'] or ''

    # Учитываем только доход с записи (стоимость услуги).
    tipo = 'Доход'
    amount = service_price

    # Описание записи
    cur.execute('SELECT "Имя" FROM "Клиенты" WHERE ID = ?', (rec['ID_Клиента'],))
    client_row = cur.fetchone()
    client_name = client_row['Имя'] if client_row else ''
    description = f"Прибыль по записи #{record_id}: {service_name} ({client_name})"

    app.conn.execute('INSERT INTO "Финансы" ("Тип", "Сумма", "Дата", "Описание") VALUES (?, ?, ?, ?)',
                     (tipo, amount, date, description))
    app.conn.commit()

    messagebox.showinfo("Готово", f"Прибыль записана: {amount:.2f} ({tipo})")
    # Показать раздел Финансы, чтобы пользователь увидел запись
    app._display_entity_data("Финансы")


def display_entity_cards(app, entity_name, records, columns):
    """Отображение записей в виде карточек"""
    for widget in app.scrollable_cards_frame.winfo_children():
        widget.destroy()
    app.card_frames = []
    app.scrollable_cards_frame.grid_columnconfigure((0, 1, 2), weight=1)
    column_names = [name for name, _ in columns]

    for index, record in enumerate(records):
        row, col = index // 3, index % 3
        card = ctk.CTkFrame(app.scrollable_cards_frame, width=300, height=200, corner_radius=10,
                            fg_color=('#2a2d2e', '#212121'), border_width=2)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
        card.record_id = record['ID']
        card.bind("<Button-1>", lambda event, card=card: app._select_card(card))
        app.card_frames.append(card)
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
            if name.upper() == 'ID':
                continue

            value = str(record[name])
            display_label = name

            # Замена ID на Имена в Записях
            if entity_name == "Записи":
                if name == 'ID_Сотрудника':
                    display_label = "Сотрудник"
                    _, id_to_name_emp = app._get_employee_map()
                    value = id_to_name_emp.get(record[name], 'Неизвестно')
                elif name == 'ID_Клиента':
                    display_label = "Клиент"
                    cursor = app.conn.cursor()
                    cursor.execute('SELECT "Имя" FROM "Клиенты" WHERE ID = ?', (record[name],))
                    client_row = cursor.fetchone()
                    value = client_row['Имя'] if client_row else 'Неизвестно'
                elif name == 'ID_Услуги':
                    display_label = "Услуга"
                    cursor = app.conn.cursor()
                    cursor.execute('SELECT "Название" FROM "Услуги" WHERE ID = ?', (record[name],))
                    service_row = cursor.fetchone()
                    value = service_row['Название'] if service_row else 'Не указана'

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
            
            # Форматирование цены для склада
            if entity_name == "Склад" and name == "Цена_за_единицу":
                try:
                    price_val = float(value) if value else 0
                    value = f"{price_val:.2f} руб."
                    display_label = "Цена за единицу"
                except:
                    pass

            ctk.CTkLabel(card, text=f"{display_label}:", text_color="#aaaaaa").grid(row=data_rows, column=0,
                                                                                    padx=(10, 5), pady=2,
                                                                                    sticky="w")
            ctk.CTkLabel(card, text=value, font=ctk.CTkFont(weight="bold"), text_color=text_color).grid(
                row=data_rows, column=1, padx=(5, 10), pady=2, sticky="w")
            data_rows += 1
            if data_rows >= 6:
                break
        # Кнопка для завершения записи (создаёт финансовую запись о прибыли)
        if entity_name == "Записи":
            def _complete(rid=record['ID']):
                complete_appointment(app, rid)

            ctk.CTkButton(card, text="✅ Завершить", fg_color="#2ECC71", command=_complete).grid(
                row=data_rows, column=0, columnspan=2, padx=10, pady=(8, 6), sticky="ew")
            data_rows += 1
        
        # Для услуг - показываем расход материалов
        if entity_name == "Услуги":
            cursor = app.conn.cursor()
            cursor.execute('''
                SELECT s."Название_Товара", rm."Количество", s."Единица_измерения"
                FROM "Расход_Материалов" rm
                JOIN "Склад" s ON rm."ID_Материала" = s.ID
                WHERE rm."ID_Услуги" = ?
            ''', (record['ID'],))
            materials = cursor.fetchall()
            
            if materials:
                materials_text = ", ".join([f"{m['Название_Товара']} ({m['Количество']} {m['Единица_измерения']})" 
                                           for m in materials[:2]])  # Показываем максимум 2 материала
                if len(materials) > 2:
                    materials_text += f" (+{len(materials) - 2} еще)"
                
                ctk.CTkLabel(card, text="Материалы:", text_color="#aaaaaa", font=ctk.CTkFont(size=9)).grid(
                    row=data_rows, column=0, padx=(10, 5), pady=2, sticky="w")
                ctk.CTkLabel(card, text=materials_text, font=ctk.CTkFont(size=9), text_color="#888888").grid(
                    row=data_rows, column=1, padx=(5, 10), pady=2, sticky="w")

