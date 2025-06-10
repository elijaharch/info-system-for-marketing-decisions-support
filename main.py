import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import scipy.stats as stats
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt


# БАЗА ДАННЫХ
# ---------------------------------------------
def init_db():
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            category TEXT,
            region TEXT,
            is_repeat_client INTEGER DEFAULT 0,
            source TEXT DEFAULT 'не указано',
            is_referral INTEGER DEFAULT 0,
            ad_channel TEXT DEFAULT 'не указано'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            service_id INTEGER,
            date TEXT,
            discount_applied REAL DEFAULT 0.0,
            final_price REAL DEFAULT 0.0,
            is_completed INTEGER DEFAULT 0,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(service_id) REFERENCES services(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ad_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            spend REAL,
            revenue REAL,
            date TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS survey_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            question TEXT,
            answer TEXT,
            date TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    """)
    conn.commit()
    conn.close()

# Запуск и сообщение об инициализации базы
init_db()
st.set_page_config(page_title="ИС маркетинга", layout="wide")
st.title("ИСППР ООО \u00abАргумент СТ\u00bb")


# --- Загрузка стандартных услуг ---
def load_default_services():
    default_services = [
        ("Создание контента с нуля", "300"),
        ("Обработка материала заказчика", "200"),
        ("Актуализация и сопровождение", "800"),
        ("Индивидуальная консультация (устно)", "4000"),
        ("Индивидуальная консультация (письменно)", "3000"),
        ("Создание лонгрида", "200"),
        ("Практико-ориентированное задание", "500"),
        ("Вставка видео + вопросы", "300"),
        ("Вопросы для размышления", "75"),
        ("Материалы для самостоятельного изучения + вопросы", "300"),
        ("PowerPoint (без эффектов)", "500"),
        ("PowerPoint (с эффектами)", "800"),
        ("Дизайн курса в iSpring Suite (.SCORM)", "3500")
    ]
    if len(get_services()) == 0:
        for title, price in default_services:
            add_service(title, price)

# --- Универсальная функция удаления записи ---
def delete_record(table_name, record_id):
    allowed_tables = {"clients", "services", "orders", "ad_stats"}
    if table_name not in allowed_tables:
        st.error(f"Удаление из таблицы {table_name} запрещено")
        return
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

# --- Работа с клиентами ---
def add_client(name, email, category, region, source, is_referral, ad_channel):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO clients (name, email, category, region, source, is_referral, ad_channel)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, email, category, region, source, is_referral, ad_channel))
    conn.commit()
    conn.close()

def get_clients():
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("SELECT * FROM clients")
    data = c.fetchall()
    conn.close()
    return data

def get_clients_df():
    data = get_clients()
    return pd.DataFrame(data, columns=[
        "ID", "ФИО/Название", "Email", "Категория", "Регион",
        "Повторный клиент", "Источник привлечения", "По рекомендации", "Канал рекламы"
    ])


# --- Работа с услугами ---
def add_service(title, price):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("INSERT INTO services (title, price) VALUES (?, ?)", (title, price))
    conn.commit()
    conn.close()

def get_services():
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("SELECT * FROM services")
    data = c.fetchall()
    conn.close()
    return data

def get_services_df():
    data = get_services()
    return pd.DataFrame(data, columns=["ID", "Название услуги", "Стоимость"])


# --- Работа с заявками ---
def add_order(client_id, service_id, client):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("SELECT price FROM services WHERE id = ?", (service_id,))
    price_str = c.fetchone()[0]

    try:
        price = float(price_str)
    except:
        price = 0.0

    discount = 10.0 if client[5] == 1 else 0.0
    final_price = price * (1 - discount / 100)

    c.execute('''
        INSERT INTO orders (client_id, service_id, date, discount_applied, final_price)
        VALUES (?, ?, ?, ?, ?)
    ''', (client_id, service_id, datetime.now().strftime("%Y-%m-%d"), discount, final_price))
    c.execute("UPDATE clients SET is_repeat_client = 1 WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()

def get_orders_df():
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute('''
        SELECT o.id, c.name, s.title, o.date, o.discount_applied, o.final_price, o.is_completed
        FROM orders o
        JOIN clients c ON o.client_id = c.id
        JOIN services s ON o.service_id = s.id
        ORDER BY o.date DESC
    ''')
    data = c.fetchall()
    conn.close()
    return pd.DataFrame(data, columns=["ID", "Клиент", "Услуга", "Дата заявки", "Скидка (%)", "Итоговая сумма (₽)", "Выполнено"])

def mark_order_completed(order_id):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("UPDATE orders SET is_completed = 1 WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()


# --- Получить клиента по id заявки ---
def get_client_by_order_id(order_id):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute('''
        SELECT cl.*
        FROM orders o
        JOIN clients cl ON o.client_id = cl.id
        WHERE o.id = ?
    ''', (order_id,))
    client = c.fetchone()
    conn.close()
    return client


# --- Рекомендации и аналитика ---
def recommend_service(client):
    category = client[3].strip().lower() if client[3] else ""
    region = client[4].strip().lower() if client[4] else ""
    is_repeat = client[5] if len(client) > 5 else 0

    if region == "москва" and category == "физическое лицо":
        return "Индивидуальная консультация (письменно)"
    elif region == "регионы" and category == "юридическое лицо":
        return "Обработка материалов заказчика"
    elif is_repeat:
        return "Скидка 10% на услуги сопровождения"
    return "Создание контента с нуля"

def get_client_by_order_id(order_id):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute('''
        SELECT cl.*
        FROM orders o
        JOIN clients cl ON o.client_id = cl.id
        WHERE o.id = ?
    ''', (order_id,))
    client = c.fetchone()
    conn.close()
    return client

# --- Реклама ---
def add_ad_stat(channel, spend, revenue, date):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO ad_stats (channel, spend, revenue, date)
        VALUES (?, ?, ?, ?)
    ''', (channel, spend, revenue, date))
    conn.commit()
    conn.close()

def get_ad_stats_df():
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("SELECT channel, spend, revenue, date FROM ad_stats ORDER BY date DESC")
    data = c.fetchall()
    conn.close()
    df = pd.DataFrame(data, columns=["Канал", "Затраты (₽)", "Доход (₽)", "Дата"])
    df["Эффективность (ЗР/ДП)"] = df["Затраты (₽)"] / df["Доход (₽)"]
    return df

def increase_ad_revenue(channel, amount):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("SELECT id, revenue FROM ad_stats WHERE channel = ? ORDER BY date DESC LIMIT 1", (channel,))
    row = c.fetchone()
    if row:
        record_id, revenue = row
        new_revenue = (revenue or 0) + amount
        c.execute("UPDATE ad_stats SET revenue = ? WHERE id = ?", (new_revenue, record_id))
    else:
        c.execute("INSERT INTO ad_stats (channel, spend, revenue, date) VALUES (?, ?, ?, ?)",
                  (channel, 0, amount, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_ad_channels():
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT channel FROM ad_stats")
    channels = [row[0] for row in c.fetchall()]
    conn.close()
    return channels

def add_survey_answer(client_id, question, answer):
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO survey_results (client_id, question, answer, date)
        VALUES (?, ?, ?, ?)
    """, (client_id, question, answer, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_survey_results_df():
    conn = sqlite3.connect("marketing.db")
    c = conn.cursor()
    c.execute("""
        SELECT c.name, s.question, s.answer, s.date
        FROM survey_results s
        JOIN clients c ON s.client_id = c.id
        ORDER BY s.date DESC
    """)
    data = c.fetchall()
    conn.close()
    return pd.DataFrame(data, columns=["Клиент", "Вопрос", "Ответ", "Дата"])


# --- Инициализация ---
init_db()
load_default_services()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "👥 Клиенты", "📚 Услуги", "📝 Заявки", "📈 Аналитика", "📣 Эффективность рекламы", "📋 Опросы", "📊 Статистика"
])

# --- Вкладка "Клиенты" ---
with tab1:
    st.header("Добавить клиента")
    name = st.text_input("Клиент")
    email = st.text_input("Email")
    category = st.selectbox("Категория", ["Физическое лицо", "Юридическое лицо"])
    region = st.selectbox("Регион", ["Москва", "Регионы"])
    source = st.selectbox("Источник привлечения", ["не указано", "Реклама", "Соцсети", "Сайт", "Рекомендация"])

    ad_channel = "не указано"
    if source == "Реклама":
        channels = get_ad_channels()
        if channels:
            ad_channel = st.selectbox("Канал рекламы", channels)
        else:
            st.info("Нет доступных рекламных каналов")

    is_referral = st.checkbox("Приведен по рекомендации?")

    if st.button("Добавить клиента", key="add_client_btn"):
        if not name.strip() or not email.strip():
            st.error("Пожалуйста, заполните поля 'Клиент' и 'Email'")
        else:
            add_client(name.strip(), email.strip(), category, region, source, int(is_referral), ad_channel)
            st.success("✅ Клиент добавлен")

    st.subheader("Список клиентов")
    clients_df = get_clients_df()

    def highlight_repeat(row):
        return ['background-color: #221f2e' if row['Повторный клиент'] == 1 else '' for _ in row]

    st.dataframe(clients_df.style.apply(highlight_repeat, axis=1), use_container_width=True)


# --- Вкладка "Услуги" ---
with tab2:
    st.header("Добавить услугу")
    with st.form("add_service_form"):
        title = st.text_input("Название услуги")
        price = st.text_input("Стоимость (можно 'по договоренности')")
        if st.form_submit_button("Добавить услугу"):
            add_service(title, price)
            st.success("✅ Услуга добавлена")

    st.subheader("Каталог услуг")
    services_df = get_services_df()
    st.dataframe(services_df, use_container_width=True)

# --- Вкладка Заявки ---
with tab3:
    st.header("Создать заявку")
    clients = get_clients()
    services = get_services()

    if not clients:
        st.warning("Невозможно создать заявку, так как нет клиентов.")
    elif not services:
        st.warning("Невозможно создать заявку, так как нет услуг.")
    else:
        client_map = {f"{c[1]} ({c[3]}, {c[4]})": c for c in clients}
        client_choice = st.selectbox("Клиент", list(client_map.keys()))
        client = client_map[client_choice]

        st.info(f"🧠 Рекомендация: {recommend_service(client)}")

        service_map = {s[1]: s[0] for s in services}
        service_choice = st.selectbox("Услуга", list(service_map.keys()))

        if st.button("Создать заявку", key="create_order_btn"):
            add_order(client[0], service_map[service_choice], client)
            st.success("✅ Заявка создана")

    st.subheader("Список заявок")
    orders_df = get_orders_df()
    if not orders_df.empty:
        for idx, row in orders_df.iterrows():
            col1, col2, col3 = st.columns([6, 2, 2])
            with col1:
                st.write(f"📝 **{row['Клиент']}** — {row['Услуга']} ({row['Дата заявки']})")
            with col2:
                st.write(f"💰 {row['Итоговая сумма (₽)']} ₽")
            with col3:
                if not row["Выполнено"]:
                    if st.button("✅ Отметить выполненной", key=f"complete_{row['ID']}"):
                        mark_order_completed(row["ID"])
                        client = get_client_by_order_id(row["ID"])
                        if client and client[6] == "Реклама" and client[8] != "не указано":
                            increase_ad_revenue(client[8], row["Итоговая сумма (₽)"])
                        st.success("Заявка выполнена, доход обновлён.")
    else:
        st.info("Заявки отсутствуют.")


# --- Вкладка Аналитика ---
with tab4:
    st.header("Общая аналитика")

    clients = get_clients()
    orders_df = get_orders_df()

    moscow = len([c for c in clients if c[4] == "Москва"])
    regions = len([c for c in clients if c[4] == "Регионы"])
    repeat = len([c for c in clients if len(c) > 5 and c[5] == 1])
    sources = [c[6] for c in clients if len(c) > 6]
    source_stats = {s: sources.count(s) for s in set(sources)}

    st.metric("👥 Всего клиентов", len(clients))
    st.metric("📝 Всего заявок", len(orders_df))
    st.metric("🏙️ Клиенты из Москвы", moscow)
    st.metric("🌍 Клиенты из регионов", regions)
    st.metric("🔁 Повторные клиенты", repeat)

    st.subheader("Источники привлечения клиентов")
    st.bar_chart(source_stats)


# --- Вкладка Эффективность рекламы ---
with tab5:
    st.header("Эффективность рекламных каналов")

    with st.form("ad_eff_form"):
        channel = st.text_input("Канал рекламы", placeholder="например, Instagram, VK, Директ")
        spend = st.number_input("Затраты на рекламу (₽)", min_value=0.0)
        revenue = st.number_input("Доход с рекламы (₽)", min_value=0.01)
        date = st.date_input("Дата кампании", value=datetime.now())
        if st.form_submit_button("Добавить кампанию"):
            add_ad_stat(channel, spend, revenue, str(date))
            st.success("✅ Кампания добавлена")

    ad_stats_df = get_ad_stats_df()
    st.subheader("Сводка по кампаниям")
    st.dataframe(ad_stats_df, use_container_width=True)

    if not ad_stats_df.empty:
        st.subheader("Средняя эффективность по каналам")
        chart_data = ad_stats_df.groupby("Канал").mean(numeric_only=True)["Эффективность (ЗР/ДП)"]
        st.bar_chart(chart_data)

with tab6:
    st.header("Проведение опросов")

    clients = get_clients()
    if not clients:
        st.warning("Нет клиентов для проведения опроса.")
    else:
        client_map = {f"{c[1]} ({c[3]}, {c[4]})": c for c in clients}

        client_choice = st.selectbox(
            "Клиент",
            list(client_map.keys()),
            key="survey_client_selectbox"  # <- вот он
        )
        client = client_map[client_choice]

        st.subheader("Вопросы для опроса")

        questions = [
            "Насколько вы удовлетворены качеством услуг? (1-5)",
            "Как вы узнали о нас?",
            "Готовы ли вы рекомендовать нас другим?",
        ]

        answers = {}
        for question in questions:
            answers[question] = st.text_input(f"{question}")

        if st.button("Сохранить ответы"):
            for q, a in answers.items():
                if a.strip():  # сохраняем только заполненные
                    add_survey_answer(client[0], q, a.strip())
            st.success("✅ Ответы сохранены")

    st.subheader("📊 Результаты опросов")
    survey_df = get_survey_results_df()
    if survey_df.empty:
        st.info("Опросов пока нет.")
    else:
        # Преобразуем таблицу:
        pivot_df = survey_df.pivot_table(
            index=["Клиент"],  # Одна строка — один клиент
            columns="Вопрос",
            values="Ответ",
            aggfunc="first"  # если несколько раз ответил — берём первый ответ
        ).reset_index()

        # Показываем красиво:
        st.dataframe(pivot_df, use_container_width=True)

with tab7:
    st.header("📊 Статистическая обработка данных")

    ad_stats_df = get_ad_stats_df()

    if ad_stats_df.empty:
        st.info("Нет данных по рекламным кампаниям для анализа.")
    else:
        st.write("Данные по рекламным кампаниям:")
        st.dataframe(ad_stats_df[["Канал", "Затраты (₽)", "Доход (₽)"]], use_container_width=True)

        # Извлекаем данные для анализа
        x = ad_stats_df["Затраты (₽)"].values
        y = ad_stats_df["Доход (₽)"].values

        # Корреляция Пирсона
        pearson_corr, pearson_p = stats.pearsonr(x, y)
        # Корреляция Спирмена
        spearman_corr, spearman_p = stats.spearmanr(x, y)

        st.subheader("📈 Корреляционный анализ")
        st.write(f"**Коэффициент корреляции Пирсона:** {pearson_corr:.3f} (p-value = {pearson_p:.3f})")
        st.write(f"**Коэффициент корреляции Спирмена:** {spearman_corr:.3f} (p-value = {spearman_p:.3f})")

        # Простейший регрессионный анализ
        X = x.reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)

        st.subheader("📉 Регрессионный анализ")
        st.write(f"**Уравнение регрессии:** Доход = {model.coef_[0]:.2f} * Затраты + {model.intercept_:.2f}")
        st.write(f"**R² (коэффициент детерминации):** {model.score(X, y):.3f}")

        # Визуализация
        st.subheader("📊 Визуализация регрессии")
        fig, ax = plt.subplots()
        ax.scatter(x, y, label="Фактические данные", color='blue')
        ax.plot(x, y_pred, color='red', label="Линия регрессии")
        ax.set_xlabel("Затраты (₽)")
        ax.set_ylabel("Доход (₽)")
        ax.set_title("Зависимость дохода от затрат")
        ax.legend()
        st.pyplot(fig)
