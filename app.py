import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import re
import urllib.request
from PIL import Image, ImageTk
import io
import random
from datetime import datetime, timedelta
import webbrowser  # Гарантируем наличие импорта для открытия веб-ссылок

# Имя файла базы данных
DB_NAME = 'кондитерская.db'

class PinkiePieApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ПинкиПай - Управление кондитерской")
        self.root.geometry("1200x750")
        self.root.minsize(1000, 650)

        # Проверка наличия БД
        if not os.path.exists(DB_NAME):
            messagebox.showerror("Ошибка", f"База данных {DB_NAME} не найдена!\nСначала запустите main.py для её создания.")
            root.destroy()
            return

        # Инициализируем/проверяем таблицу продаж
        self.init_sales_table_if_needed()

        # Верхняя панель с кнопками
        btn_frame = tk.Frame(root, bg="#FFB6C1", pady=10)
        btn_frame.pack(fill=tk.X)

        btn_style = {"font": ("Arial", 12, "bold"), "bg": "#FF69B4", "fg": "white", "activebackground": "#FF1493", "relief": tk.RAISED, "bd": 2}
        
        # Кнопки навигации
        tk.Button(btn_frame, text="🍰 Позиции", command=self.show_positions, **btn_style).pack(side=tk.LEFT, padx=20)
        tk.Button(btn_frame, text="📊 Отчеты", command=self.show_reports, **btn_style).pack(side=tk.LEFT, padx=20)
        tk.Button(btn_frame, text="ℹ️ О приложении", command=self.show_about, **btn_style).pack(side=tk.LEFT, padx=20)

        # Контейнер для фреймов
        self.container = tk.Frame(root)
        self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Инициализация фреймов
        self.positions_frame = self.create_positions_frame()
        self.reports_frame = self.create_reports_frame()
        self.about_frame = self.create_about_frame()

        self.show_about() # По умолчанию открываем вкладку "О приложении"

    def get_db_connection(self):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

    def init_sales_table_if_needed(self):
        """Проверяет наличие таблицы продаж. Если её нет — создаёт и наполняет демонстрационными данными."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже какая-то таблица продаж
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sales', 'orders', 'продажи')")
        existing = cursor.fetchone()
        
        if not existing:
            # Создаем стандартную таблицу продаж, если ее нет
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT,
                    quantity INTEGER,
                    sale_date TEXT,
                    price REAL,
                    FOREIGN KEY(product_id) REFERENCES products(id)
                )
            """)
            conn.commit()
            
        # Находим активное имя таблицы продаж
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sales', 'orders', 'продажи')")
        active_table = cursor.fetchone()
        if active_table:
            table_name = active_table['name']
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            # Если таблица пуста, сгенерируем демонстрационные данные
            if count == 0:
                cursor.execute("SELECT id, price FROM products")
                products = cursor.fetchall()
                if products:
                    now = datetime.now()
                    mock_sales = []
                    for _ in range(150):
                        p = random.choice(products)
                        p_id = p['id']
                        p_price = p['price']
                        qty = random.randint(1, 5)
                        
                        day_bucket = random.choices(['today', 'week', 'month', 'year'], weights=[15, 25, 35, 25], k=1)[0]
                        if day_bucket == 'today':
                            rand_days = 0
                        elif day_bucket == 'week':
                            rand_days = random.randint(1, 6)
                        elif day_bucket == 'month':
                            rand_days = random.randint(7, 29)
                        else:
                            rand_days = random.randint(30, 360)
                            
                        sale_time = now - timedelta(days=rand_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))
                        sale_date_str = sale_time.strftime('%Y-%m-%d %H:%M:%S')
                        
                        mock_sales.append((p_id, qty, sale_date_str, p_price))
                    
                    # Проверяем колонки в активной таблице для корректной записи
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [r['name'].lower() for r in cursor.fetchall()]
                    
                    p_col = next((c for c in columns if c in ['product_id', 'id_product', 'product', 'товар_id', 'товар']), 'product_id')
                    q_col = next((c for c in columns if c in ['quantity', 'qty', 'count', 'кол', 'количество']), 'quantity')
                    d_col = next((c for c in columns if c in ['sale_date', 'date', 'timestamp', 'created_at', 'дата']), 'sale_date')
                    pr_col = next((c for c in columns if c in ['price', 'cost', 'цена', 'сумма']), 'price')
                    
                    insert_sql = f"INSERT INTO {table_name} ({p_col}, {q_col}, {d_col}, {pr_col}) VALUES (?, ?, ?, ?)"
                    cursor.executemany(insert_sql, mock_sales)
                    conn.commit()
        conn.close()

    def fetch_sales_data(self):
        """Динамически находит таблицу продаж и извлекает информацию о покупках."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r['name'] for r in cursor.fetchall()]
        
        table_name = None
        for name in ['sales', 'orders', 'продажи', 'sales_history']:
            if name in tables:
                table_name = name
                break
                
        if not table_name:
            conn.close()
            return []
            
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [r['name'] for r in cursor.fetchall()]
        
        p_id_col = next((c for c in columns if c.lower() in ['product_id', 'id_product', 'product', 'товар_id', 'товар']), None)
        qty_col = next((c for c in columns if c.lower() in ['quantity', 'qty', 'count', 'кол', 'количество']), None)
        date_col = next((c for c in columns if c.lower() in ['sale_date', 'date', 'timestamp', 'created_at', 'дата']), None)
        price_col = next((c for c in columns if c.lower() in ['price', 'cost', 'цена', 'сумма']), None)
        
        if p_id_col and qty_col and date_col:
            if price_col:
                sql = f"SELECT {p_id_col} AS product_id, {qty_col} AS quantity, {date_col} AS sale_date, {price_col} AS price FROM {table_name}"
            else:
                sql = f"""
                    SELECT s.{p_id_col} AS product_id, s.{qty_col} AS quantity, s.{date_col} AS sale_date, p.price AS price 
                    FROM {table_name} s
                    LEFT JOIN products p ON s.{p_id_col} = p.id
                """
            try:
                cursor.execute(sql)
                rows = [dict(r) for r in cursor.fetchall()]
                conn.close()
                return rows
            except Exception as e:
                print(f"Ошибка чтения таблицы продаж: {e}")
                
        conn.close()
        return []

    # ================= ОЧИСТКА И ПЕРЕКЛЮЧЕНИЕ ФРЕЙМОВ =================
    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.pack_forget()

    def show_positions(self):
        self.clear_container()
        self.positions_frame.pack(fill=tk.BOTH, expand=True)
        self.refresh_products()

    def show_reports(self):
        self.clear_container()
        self.reports_frame.pack(fill=tk.BOTH, expand=True)

    def show_about(self):
        self.clear_container()
        self.about_frame.pack(fill=tk.BOTH, expand=True)

    # ================= ФРЕЙМ 1: ПОЗИЦИИ (CRUD) =================
    def create_positions_frame(self):
        frame = tk.Frame(self.container)

        # Панель фильтрации и сортировки
        filter_sort_frame = tk.Frame(frame, bg="#FFF0F5", pady=5, relief=tk.GROOVE, bd=1)
        filter_sort_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(filter_sort_frame, text="Категория:", bg="#FFF0F5", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.filter_var = tk.StringVar(value="Все")
        categories = ["Все", "Торты", "Пирожные и капкейки", "Печенье, пряники и вафли", "Конфеты, шоколад и прочее"]
        self.filter_combo = ttk.Combobox(filter_sort_frame, textvariable=self.filter_var, values=categories, state="readonly", width=25)
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda event: self.refresh_products())

        tk.Label(filter_sort_frame, text="Сортировка:", bg="#FFF0F5", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=15)
        self.sort_var = tk.StringVar(value="ID (возр.)")
        
        # Расширенный список вариантов сортировки (все варианты двусторонние)
        sort_options = [
            "ID (возр.)", "ID (убыв.)",
            "Название (возр.)", "Название (убыв.)",
            "Категория (возр.)", "Категория (убыв.)",
            "Цена (возр.)", "Цена (убыв.)", 
            "Остаток (возр.)", "Остаток (убыв.)",
            "Вес (возр.)", "Вес (убыв.)",
            "Скидка (возр.)", "Скидка (убыв.)",
            "Ингредиенты (возр.)", "Ингредиенты (убыв.)",
            "Пищ. ценность (возр.)", "Пищ. ценность (убыв.)"
        ]
        self.sort_combo = ttk.Combobox(filter_sort_frame, textvariable=self.sort_var, values=sort_options, state="readonly", width=23)
        self.sort_combo.pack(side=tk.LEFT, padx=5)
        self.sort_combo.bind("<<ComboboxSelected>>", lambda event: self.refresh_products())

        tk.Button(filter_sort_frame, text="Применить", bg="#FF69B4", fg="white", command=self.refresh_products, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=15)

        # Таблица
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "name", "category", "price", "weight", "ingredients", "stock", "nutrition", "discount")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        # Настройка заголовков столбцов с поддержкой двусторонней сортировки
        self.tree.heading("id", text="ID ↕", command=lambda: self.sort_by_header("ID"))
        self.tree.heading("name", text="Название ↕", command=lambda: self.sort_by_header("Название"))
        self.tree.heading("category", text="Категория ↕", command=lambda: self.sort_by_header("Категория"))
        self.tree.heading("price", text="Цена ↕", command=lambda: self.sort_by_header("Цена"))
        self.tree.heading("weight", text="Вес(г) ↕", command=lambda: self.sort_by_header("Вес"))
        self.tree.heading("ingredients", text="Ингредиенты ↕", command=lambda: self.sort_by_header("Ингредиенты"))
        self.tree.heading("stock", text="Остаток ↕", command=lambda: self.sort_by_header("Остаток"))
        self.tree.heading("nutrition", text="Пищ. ценность ↕", command=lambda: self.sort_by_header("Пищ. ценность"))
        self.tree.heading("discount", text="Скидка ↕", command=lambda: self.sort_by_header("Скидка"))

        self.tree.column("id", width=60, anchor=tk.CENTER)
        self.tree.column("name", width=180)
        self.tree.column("category", width=130, anchor=tk.CENTER)
        self.tree.column("price", width=80, anchor=tk.E)
        self.tree.column("weight", width=60, anchor=tk.CENTER)
        self.tree.column("ingredients", width=220)
        self.tree.column("stock", width=60, anchor=tk.CENTER)
        self.tree.column("nutrition", width=140)
        self.tree.column("discount", width=60, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<Double-1>', self.on_tree_double_click)

        # Панель управления
        ctrl_frame = tk.LabelFrame(frame, text="Управление товаром", font=("Arial", 10, "bold"), pady=10)
        ctrl_frame.pack(fill=tk.X, pady=10)

        labels = ["Название:", "Цена:", "Вес(г):", "Ингредиенты:", "Остаток:", "Пищ. ценность:", "Скидка(%):", "Категория:"]
        self.entries = {}
        
        for i, label_text in enumerate(labels):
            row = i // 4
            col = (i % 4) * 2
            tk.Label(ctrl_frame, text=label_text).grid(row=row, column=col, padx=5, pady=2, sticky=tk.W)
            
            if label_text == "Категория:":
                entry = ttk.Combobox(ctrl_frame, values=categories[1:], state="readonly", width=22)
            else:
                entry = tk.Entry(ctrl_frame, width=25)
                
            entry.grid(row=row, column=col+1, padx=5, pady=2)
            key = label_text.replace(":", "").replace("(%)", "").strip().lower()
            if key == "пищ. ценность": key = "nutrition"
            if key == "категория": key = "category"
            self.entries[key] = entry

        btn_crud_frame = tk.Frame(ctrl_frame)
        btn_crud_frame.grid(row=2, column=0, columnspan=8, pady=10)

        tk.Button(btn_crud_frame, text="Добавить", bg="#90EE90", command=self.add_product, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_crud_frame, text="Изменить", bg="#87CEFA", command=self.update_product, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_crud_frame, text="Удалить", bg="#FFA07A", command=self.delete_product, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_crud_frame, text="Очистить поля", command=self.clear_entries, width=12).pack(side=tk.LEFT, padx=5)

        return frame

    def generate_next_id(self, category):
        prefix_map = {
            "Торты": "Т",
            "Пирожные и капкейки": "ПК",
            "Печенье, пряники и вафли": "ПП",
            "Конфеты, шоколад и прочее": "КШ"
        }
        prefix = prefix_map.get(category, "Х")

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM products WHERE id LIKE ?", (f"{prefix}-%",))
        rows = cursor.fetchall()
        conn.close()

        max_num = 0
        for row in rows:
            try:
                num = int(row['id'].split('-')[1])
                if num > max_num: max_num = num
            except:
                pass
        return f"{prefix}-{max_num + 1:03d}"

    def sort_by_header(self, column_name):
        """Инвертирует направление сортировки при повторном клике на заголовок любого столбца"""
        current_sort = self.sort_var.get()
        if column_name == "ID":
            self.sort_var.set("ID (убыв.)" if current_sort == "ID (возр.)" else "ID (возр.)")
        elif column_name == "Название":
            self.sort_var.set("Название (убыв.)" if current_sort == "Название (возр.)" else "Название (возр.)")
        elif column_name == "Категория":
            self.sort_var.set("Категория (убыв.)" if current_sort == "Категория (возр.)" else "Категория (возр.)")
        elif column_name == "Ингредиенты":
            self.sort_var.set("Ингредиенты (убыв.)" if current_sort == "Ингредиенты (возр.)" else "Ингредиенты (возр.)")
        elif column_name == "Пищ. ценность":
            self.sort_var.set("Пищ. ценность (убыв.)" if current_sort == "Пищ. ценность (возр.)" else "Пищ. ценность (возр.)")
        elif column_name == "Цена":
            self.sort_var.set("Цена (убыв.)" if current_sort == "Цена (возр.)" else "Цена (возр.)")
        elif column_name == "Остаток":
            self.sort_var.set("Остаток (убыв.)" if current_sort == "Остаток (возр.)" else "Остаток (возр.)")
        elif column_name == "Вес":
            self.sort_var.set("Вес (убыв.)" if current_sort == "Вес (возр.)" else "Вес (возр.)")
        elif column_name == "Скидка":
            self.sort_var.set("Скидка (убыв.)" if current_sort == "Скидка (возр.)" else "Скидка (возр.)")
        
        self.refresh_products()

    def refresh_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        query = "SELECT * FROM products"
        params = []

        # Фильтрация
        cat = self.filter_var.get()
        if cat != "Все":
            query += " WHERE category=?"
            params.append(cat)

        # Сортировка (все варианты теперь поддерживают ASC и DESC)
        sort = self.sort_var.get()
        if sort == "ID (возр.)": query += " ORDER BY id ASC"
        elif sort == "ID (убыв.)": query += " ORDER BY id DESC"
        elif sort == "Название (возр.)": query += " ORDER BY name ASC"
        elif sort == "Название (убыв.)": query += " ORDER BY name DESC"
        elif sort == "Категория (возр.)": query += " ORDER BY category ASC"
        elif sort == "Категория (убыв.)": query += " ORDER BY category DESC"
        elif sort == "Ингредиенты (возр.)": query += " ORDER BY ingredients ASC"
        elif sort == "Ингредиенты (убыв.)": query += " ORDER BY ingredients DESC"
        elif sort == "Пищ. ценность (возр.)": query += " ORDER BY nutrition ASC"
        elif sort == "Пищ. ценность (убыв.)": query += " ORDER BY nutrition DESC"
        elif sort == "Цена (возр.)": query += " ORDER BY CAST(price AS REAL) ASC"
        elif sort == "Цена (убыв.)": query += " ORDER BY CAST(price AS REAL) DESC"
        elif sort == "Остаток (возр.)": query += " ORDER BY CAST(stock AS INTEGER) ASC"
        elif sort == "Остаток (убыв.)": query += " ORDER BY CAST(stock AS INTEGER) DESC"
        elif sort == "Вес (возр.)": query += " ORDER BY CAST(weight AS INTEGER) ASC"
        elif sort == "Вес (убыв.)": query += " ORDER BY CAST(weight AS INTEGER) DESC"
        elif sort == "Скидка (возр.)": query += " ORDER BY CAST(discount AS REAL) ASC"
        elif sort == "Скидка (убыв.)": query += " ORDER BY CAST(discount AS REAL) DESC"

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            price_str = f"{row['price']:.2f}"
            discount_str = f"{row['discount']*100:.0f}%"
            self.tree.insert("", tk.END, values=(row['id'], row['name'], row['category'], price_str, row['weight'], row['ingredients'], row['stock'], row['nutrition'], discount_str))
        conn.close()

    def clear_entries(self):
        for entry in self.entries.values():
            if isinstance(entry, ttk.Combobox):
                entry.set('')
            else:
                entry.delete(0, tk.END)

    def get_entry_values(self):
        try:
            discount_val = float(self.entries['скидка'].get() or 0.0) / 100.0
            category = self.entries['category'].get()
            if not category:
                raise ValueError("Категория не выбрана")

            return {
                "name": self.entries['название'].get(),
                "price": float(self.entries['цена'].get()),
                "weight": int(self.entries['вес(г)'].get()),
                "ingredients": self.entries['ингредиенты'].get(),
                "stock": int(self.entries['остаток'].get()),
                "nutrition": self.entries['nutrition'].get(),
                "discount": discount_val,
                "category": category
            }
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", f"Проверьте правильность числовых полей и выбор категории.\nПодробности: {e}")
            return None

    def add_product(self):
        vals = self.get_entry_values()
        if not vals: return

        new_id = self.generate_next_id(vals['category'])

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO products (id, name, category, price, weight, ingredients, stock, nutrition, discount) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (new_id, vals['name'], vals['category'], vals['price'], vals['weight'], vals['ingredients'], vals['stock'], vals['nutrition'], vals['discount']))
        conn.commit()
        conn.close()
        self.refresh_products()
        self.clear_entries()

    def on_tree_double_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return  # Игнорируем двойные клики по заголовкам или пустому месту под таблицей
        
        values = self.tree.item(row_id, 'values')
        if not values:
            return

        keys = ["название", "категория", "цена", "вес(г)", "ингредиенты", "остаток", "nutrition", "скидка"]
        self.clear_entries()
        for key, val in zip(keys, values[1:]):
            if key == "категория":
                self.entries[key].set(val)
            elif key == "скидка":
                clean_val = str(val).replace('%', '')
                self.entries[key].insert(0, clean_val)
            else:
                self.entries[key].insert(0, val)

    def update_product(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Внимание", "Выберите товар в таблице для изменения (кликните по нему)")
            return
        
        vals = self.get_entry_values()
        if not vals: return

        item_id = self.tree.item(selected_item[0], 'values')[0]

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""UPDATE products SET name=?, category=?, price=?, weight=?, ingredients=?, stock=?, nutrition=?, discount=?
                          WHERE id=?""",
                       (vals['name'], vals['category'], vals['price'], vals['weight'], vals['ingredients'], vals['stock'], vals['nutrition'], vals['discount'], item_id))
        conn.commit()
        conn.close()
        self.refresh_products()
        self.clear_entries()

    def delete_product(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Внимание", "Выберите товар в таблице для удаления")
            return
        
        item_id = self.tree.item(selected_item[0], 'values')[0]
        if messagebox.askyesno("Подтверждение", f"Удалить товар с ID {item_id}?"):
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id=?", (item_id,))
            conn.commit()
            conn.close()
            self.refresh_products()
            self.clear_entries()

    # ================= ФРЕЙМ 2: ОТЧЕТЫ =================
    def create_reports_frame(self):
        frame = tk.Frame(self.container)

        top_r_frame = tk.Frame(frame)
        top_r_frame.pack(fill=tk.X, pady=5)

        tk.Label(top_r_frame, text="Выберите отчет:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        
        self.report_var = tk.StringVar()
        
        self.report_menu_btn = tk.Menubutton(
            top_r_frame, 
            text="Выберите подкатегорию...", 
            indicatoron=True, 
            borderwidth=1, 
            relief=tk.RAISED, 
            bg="white", 
            width=50, 
            anchor="w",
            font=("Arial", 10)
        )
        self.report_menu_btn.pack(side=tk.LEFT, padx=5)
        
        self.report_menu = tk.Menu(self.report_menu_btn, tearoff=0)
        self.report_menu_btn.configure(menu=self.report_menu)
        
        # Созданы разделы меню
        analytics_menu = tk.Menu(self.report_menu, tearoff=0)
        time_menu = tk.Menu(self.report_menu, tearoff=0) # Раздел временных отчетов
        price_menu = tk.Menu(self.report_menu, tearoff=0)
        stock_menu = tk.Menu(self.report_menu, tearoff=0)
        features_menu = tk.Menu(self.report_menu, tearoff=0)
        
        self.report_menu.add_cascade(label="📈 Аналитика", menu=analytics_menu)
        self.report_menu.add_cascade(label="📅 Продажи по периодам", menu=time_menu)
        self.report_menu.add_cascade(label="💰 Цены и Стоимость", menu=price_menu)
        self.report_menu.add_cascade(label="📦 Запасы и Склад", menu=stock_menu)
        self.report_menu.add_cascade(label="🍏 Характеристики товаров", menu=features_menu)
        
        # Наполнение разделов
        analytics_reports = [
            "1. ABC-анализ (по потенциальной выручке)",
            "2. XYZ-анализ (по стабильности остатков)",
            "3. KPI: Товары для распродажи (скидка > 0)"
        ]
        for r in analytics_reports:
            analytics_menu.add_command(label=r, command=lambda val=r: self.select_report(val))

        # Раздельные временные отчеты
        time_reports = [
            "13. Продажи за день",
            "14. Продажи за неделю",
            "15. Продажи за месяц",
            "16. Продажи за год"
        ]
        for r in time_reports:
            time_menu.add_command(label=r, command=lambda val=r: self.select_report(val))
            
        price_reports = [
            "4. Самая прибыльная позиция (цена*остаток)",
            "5. Самый дорогой товар",
            "6. Самый дешевый товар",
            "9. Итоговая стоимость всех товаров на складе",
            "12. Товары без скидки"
        ]
        for r in price_reports:
            price_menu.add_command(label=r, command=lambda val=r: self.select_report(val))
            
        stock_reports = [
            "7. Топ-5 самых запасоемких товаров",
            "8. Критический остаток (меньше 10 шт)"
        ]
        for r in stock_reports:
            stock_menu.add_command(label=r, command=lambda val=r: self.select_report(val))
            
        features_reports = [
            "10. Самые калорийные товары (Топ-5)",
            "11. Легкие товары (до 100 грамм)"
        ]
        for r in features_reports:
            features_menu.add_command(label=r, command=lambda val=r: self.select_report(val))

        default_report = "1. ABC-анализ (по потенциальной выручке)"
        self.report_var.set(default_report)
        self.report_menu_btn.config(text=default_report)

        tk.Button(top_r_frame, text="Сформировать", bg="#90EE90", command=self.generate_report, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(top_r_frame, text="Сохранить в файл", bg="#87CEFA", command=self.save_report, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)

        self.report_text = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 11))
        self.report_text.pack(fill=tk.BOTH, expand=True, pady=10)

        return frame

    def select_report(self, report_name):
        self.report_var.set(report_name)
        self.report_menu_btn.config(text=report_name)
        self.generate_report()

    def fetch_data_for_report(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_price_tiers(self, data):
        """Рассчитывает ценовые категории: Дешёвый, Средний, Дорогой"""
        if not data: return {}
        prices = sorted([r['price'] for r in data])
        p33 = prices[len(prices)//3]
        p66 = prices[2*len(prices)//3]

        tiers = {}
        for r in data:
            if r['price'] <= p33: tiers[r['name']] = "(Дешёвый)"
            elif r['price'] <= p66: tiers[r['name']] = "(Средний)"
            else: tiers[r['name']] = "(Дорогой)"
        return tiers

    def generate_report(self):
        choice = self.report_var.get()
        data = self.fetch_data_for_report()
        result = ""
        
        tiers = self.get_price_tiers(data)

        if "1. ABC" in choice:
            calc_data = [{'name': r['name'], 'rev': r['price'] * r['stock']} for r in data]
            calc_data.sort(key=lambda x: x['rev'], reverse=True)
            total_rev = sum(i['rev'] for i in calc_data)
            
            result = "--- ABC-АНАЛИЗ (по потенциальной выручке) ---\n"
            result += f"{'Товар':<50} | {'Выручка':<15} | Доля | Класс\n"
            result += "-" * 85 + "\n"
            
            cum_pct = 0
            for item in calc_data:
                pct = (item['rev'] / total_rev) * 100 if total_rev > 0 else 0
                cum_pct += pct
                cls = 'A' if cum_pct <= 80 else ('B' if cum_pct <= 95 else 'C')
                name_with_tier = f"{item['name']} {tiers.get(item['name'], '')}"
                result += f"{name_with_tier[:50]:<50} | {item['rev']:<15.2f} | {pct:4.1f}% | {cls}\n"

        elif "2. XYZ" in choice:
            result = "--- XYZ-АНАЛИЗ (по уровню остатков) ---\n"
            result += f"{'Товар':<50} | {'Остаток':<10} | Класс\n"
            result += "-" * 70 + "\n"
            
            for r in sorted(data, key=lambda x: x['stock'], reverse=True):
                cls = 'X' if r['stock'] > 30 else ('Y' if r['stock'] >= 10 else 'Z')
                name_with_tier = f"{r['name']} {tiers.get(r['name'], '')}"
                result += f"{name_with_tier[:50]:<50} | {r['stock']:<10} | {cls}\n"

        elif "3. KPI" in choice:
            result = "--- KPI: ТОВАРЫ ДЛЯ РАСПРОДАЖИ (Скидка > 0) ---\n"
            result += f"{'Товар':<50} | {'Цена':<10} | {'Скидка':<10}\n"
            result += "-" * 75 + "\n"
            for r in data:
                if r['discount'] > 0:
                    name_with_tier = f"{r['name']} {tiers.get(r['name'], '')}"
                    result += f"{name_with_tier[:50]:<50} | {r['price']:<10.2f} | {r['discount']*100:.0f}%\n"

        elif "4. Самая прибыльная" in choice:
            best = max(data, key=lambda x: x['price'] * x['stock'])
            rev = best['price'] * best['stock']
            result = "--- САМАЯ ПРИБЫЛЬНАЯ ПОЗИЦИЯ (Цена * Остаток) ---\n\n"
            result += f"Товар: {best['name']} {tiers.get(best['name'], '')}\nПотенциальная выручка: {rev:.2f} руб.\nОстаток: {best['stock']} шт.\nЦена: {best['price']:.2f} руб."

        elif "5. Самый дорогой" in choice:
            best = max(data, key=lambda x: x['price'])
            result = "--- САМЫЙ ДОРОГОЙ ТОВАР ---\n\n"
            result += f"Товар: {best['name']} {tiers.get(best['name'], '')}\nЦена: {best['price']:.2f} руб."

        elif "6. Самый дешевый" in choice:
            best = min(data, key=lambda x: x['price'])
            result = "--- САМЫЙ ДОРОГОЙ ТОВАР ---\n\n"
            result += f"Товар: {best['name']} {tiers.get(best['name'], '')}\nЦена: {best['price']:.2f} руб."

        elif "7. Top-5 самых запасоемких" in choice:
            top5 = sorted(data, key=lambda x: x['stock'], reverse=True)[:5]
            result = "--- ТОП-5 САМЫХ ЗАПАСОЕМКИХ ТОВАРОВ ---\n"
            result += f"{'Товар':<50} | {'Остаток':<10}\n"
            result += "-" * 65 + "\n"
            for r in top5:
                name_with_tier = f"{r['name']} {tiers.get(r['name'], '')}"
                result += f"{name_with_tier[:50]:<50} | {r['stock']:<10}\n"

        elif "8. Критический остаток" in choice:
            crit = [r for r in data if r['stock'] < 10]
            result = "--- ТОВАРЫ С КРИТИЧЕСКИМ ОСТАТКОМ (< 10 шт) ---\n"
            result += f"{'Товар':<50} | {'Остаток':<10}\n"
            result += "-" * 65 + "\n"
            for r in crit:
                name_with_tier = f"{r['name']} {tiers.get(r['name'], '')}"
                result += f"{name_with_tier[:50]:<50} | {r['stock']:<10}\n"

        elif "9. Итоговая стоимость" in choice:
            total = sum(r['price'] * r['stock'] for r in data)
            result = "--- ИТОГОВАЯ СТОИМОСТЬ ВСЕХ ТОВАРОВ НА СКЛАДЕ ---\n\n"
            result += f"Сумма: {total:,.2f} руб.\nКоличество наименований: {len(data)} шт."

        elif "10. Самые калорийные" in choice:
            def get_cal(nutr):
                match = re.search(r'(\d+)\s*ккал', nutr)
                return int(match.group(1)) if match else 0
                
            top5 = sorted(data, key=lambda x: get_cal(x['nutrition']), reverse=True)[:5]
            result = "--- САМЫЕ КАЛОРИЙНЫЕ ТОВАРЫ (Топ-5) ---\n"
            result += f"{'Товар':<50} | {'Ккал':<10}\n"
            result += "-" * 65 + "\n"
            for r in top5:
                name_with_tier = f"{r['name']} {tiers.get(r['name'], '')}"
                result += f"{name_with_tier[:50]:<50} | {get_cal(r['nutrition']):<10}\n"

        elif "11. Легкие товары" in choice:
            light = [r for r in data if r['weight'] < 100]
            result = "--- ЛЕГКИЕ ТОВАРЫ (до 100 грамм) ---\n"
            result += f"{'Товар':<50} | {'Вес(г)':<10}\n"
            result += "-" * 65 + "\n"
            for r in light:
                name_with_tier = f"{r['name']} {tiers.get(r['name'], '')}"
                result += f"{name_with_tier[:50]:<50} | {r['weight']:<10}\n"

        elif "12. Товары без скидки" in choice:
            no_disc = [r for r in data if r['discount'] == 0.0]
            result = "--- ТОВАРЫ БЕЗ СКИДКИ ---\n"
            result += f"Найдено: {len(no_disc)} товаров\n\n"
            for r in no_disc:
                name_with_tier = f"{r['name']} {tiers.get(r['name'], '')}"
                result += f"- {name_with_tier} (Цена: {r['price']:.2f})\n"

        elif "Продажи за" in choice:
            sales = self.fetch_sales_data()
            now = datetime.now()
            
            # Настройка заголовка и временного фильтра
            if "день" in choice:
                title = "ЗА ДЕНЬ"
                start_date = datetime(now.year, now.month, now.day)
            elif "неделю" in choice:
                title = "ЗА НЕДЕЛЮ (ПОСЛЕДНИЕ 7 ДНЕЙ)"
                start_date = now - timedelta(days=7)
            elif "месяц" in choice:
                title = "ЗА МЕСЯЦ (ПОСЛЕДНИЕ 30 ДНЕЙ)"
                start_date = now - timedelta(days=30)
            elif "год" in choice:
                title = "ЗА ГОД (ПОСЛЕДНИЕ 365 ДНЕЙ)"
                start_date = now - timedelta(days=365)
                
            result = f"--- ОТЧЕТ О ПРОДАЖАХ {title} ---\n"
            result += f"Временной диапазон: с {start_date.strftime('%d.%m.%Y %H:%M')} по {now.strftime('%d.%m.%Y %H:%M')}\n"
            result += "-" * 75 + "\n"
            
            if not sales:
                result += "Нет данных о продажах. Таблица пуста."
            else:
                total_revenue = 0.0
                total_qty = 0
                product_stats = {} # product_id -> {'qty': int, 'rev': float}
                
                # Получаем названия продуктов
                conn = self.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, name FROM products")
                product_names = {r['id']: r['name'] for r in cursor.fetchall()}
                conn.close()
                
                # Фильтруем и накапливаем продажи за выбранный период
                for sale in sales:
                    date_str = sale.get('sale_date', '')
                    parsed_date = None
                    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d.%m.%Y %H:%M:%S', '%d.%m.%Y'):
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if not parsed_date:
                        continue
                        
                    if parsed_date >= start_date:
                        qty = sale.get('quantity', 0)
                        price = sale.get('price', 0.0)
                        p_id = sale.get('product_id', '')
                        rev = price * qty
                        
                        total_revenue += rev
                        total_qty += qty
                        
                        if p_id not in product_stats:
                            product_stats[p_id] = {'qty': 0, 'rev': 0.0}
                        product_stats[p_id]['qty'] += qty
                        product_stats[p_id]['rev'] += rev

                result += f"Общая выручка: {total_revenue:,.2f} руб.\n"
                result += f"Всего продано позиций (штук): {total_qty}\n"
                if total_qty > 0:
                    result += f"Средняя стоимость проданной единицы: {total_revenue / total_qty:.2f} руб.\n"
                result += "\n"
                
                # Построчная детализация по продуктам
                result += f"{'Наименование товара':<40} | {'Продано (шт)':<15} | {'Выручка (руб)':<15}\n"
                result += "-" * 75 + "\n"
                
                sorted_products = sorted(product_stats.items(), key=lambda x: x[1]['rev'], reverse=True)
                for p_id, stats in sorted_products:
                    p_name = product_names.get(p_id, p_id)
                    result += f"{p_name[:40]:<40} | {stats['qty']:<15} | {stats['rev']:<15.2f}\n"
                    
                if not sorted_products:
                    result += "За выбранный период времени продаж не обнаружено.\n"

        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(tk.END, result)

    def save_report(self):
        content = self.report_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Внимание", "Сначала сформируйте отчет!")
            return

        filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Успех", "Отчет успешно сохранен!")

    # ================= ФРЕЙМ 3: О ПРИЛОЖЕНИИ =================
    def create_about_frame(self):
        frame = tk.Frame(self.container)
        
        center_frame = tk.Frame(frame)
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        image_url = "https://i.pinimg.com/originals/31/8f/3a/318f3aa14c31bfc1b6c1853eec632f7f.png?nii=t"
        try:
            with urllib.request.urlopen(image_url) as url_response:
                raw_data = url_response.read()
            
            img = Image.open(io.BytesIO(raw_data))
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            
            self.about_image = ImageTk.PhotoImage(img)
            
            img_label = tk.Label(center_frame, image=self.about_image, bg=frame.cget('bg'))
            img_label.pack(pady=10)
        except Exception as e:
            print(f"Не удалось загрузить картинку: {e}")

        tk.Label(center_frame, text="ПинкиПай", font=("Arial", 24, "bold"), fg="#FF1493").pack(pady=10)
        tk.Label(center_frame, text="Система управления кондитерской базой данных", font=("Arial", 14)).pack(pady=5)
        
        tk.Frame(center_frame, height=2, bg="black", width=300).pack(pady=20)
        
        tk.Label(center_frame, text="Версия: 2.0.0", font=("Arial", 12)).pack(pady=5)
        tk.Label(center_frame, text="Разработчик: Кирсанов Д.Ю.", font=("Arial", 12)).pack(pady=5)
        
        github_link = "https://github.com/kub2888/PinkePie"
        github_lbl = tk.Label(center_frame, text=f"GitHub: {github_link}", font=("Arial", 12), fg="blue", cursor="hand2")
        github_lbl.pack(pady=5)
        github_lbl.bind("<Button-1>", lambda e: webbrowser.open_new(github_link))
        
        tk.Label(center_frame, text="Приложение для CRUD-операций и аналитики\nтоваров кондитерской", font=("Arial", 11), justify=tk.CENTER).pack(pady=20)

        return frame

if __name__ == "__main__":
    root = tk.Tk()
    app = PinkiePieApp(root)
    root.mainloop()