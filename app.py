import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# 1. Конфигурация страницы
st.set_page_config(
    page_title="Falcon Control Tower | Owner Mode",
    page_icon="📈",
    layout="wide"
)

# --- JAVASCRIPT ФИКС ДЛЯ TELEGRAM ---
components.html(
    """
    <script>
    const parent = window.parent.document;
    function stopTelegramSwipe(e) {
        if(e.target.closest('.stDataFrame') || e.target.closest('.stTable')) {
            e.stopPropagation();
        }
    }
    parent.addEventListener('touchstart', stopTelegramSwipe, {passive: false, capture: true});
    parent.addEventListener('touchmove', stopTelegramSwipe, {passive: false, capture: true});
    </script>
    """,
    height=0, width=0
)

# --- КОРПОРАТИВНЫЙ СТИЛЬ (OWNER DARK GOLD) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #0b2239; }
    [data-testid="stSidebar"] * { color: white !important; }
    .status-light {
        height: 15px; width: 15px; border-radius: 50%; display: inline-block; margin-right: 5px;
    }
    .red { background-color: #ff4b4b; }
    .yellow { background-color: #ffa500; }
    .green { background-color: #00c851; }
    
    /* Стилизация карточек */
    div[data-testid="stMetric"] {
        background-color: #1e3a5f;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #c41230;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Подключение к данным
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
except Exception as e:
    st.error(f"Ошибка данных: {e}")
    st.stop()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ "ЛАМПОЧЕК" ---
def get_money_light(row):
    if row['balance'] < -500000: return "🔴" # Большой долг
    if row['demurrage_free_days'] < 2: return "🟡" # Скоро штраф
    return "🟢"

def get_ops_light(row):
    if row['delay_days'] > 3: return "🔴"
    if row['delay_days'] > 0: return "🟡"
    return "🟢"

def get_retention_light(row):
    # Логика: если задержка или высокий затор — клиент может нервничать
    if row['border_congestion'] == "Высокий": return "🟡"
    return "🟢"

# 3. ХЕДЕР: Агрегированные показатели (Header)
st.title("🦅 Control Tower: Profit & Risk")
st.subheader("Сводный отчет по всей компании")

m1, m2, m3, m4 = st.columns(4)

# Пример расчетов (в реале берем суммы из колонок)
money_at_risk = df[df['balance'] < 0]['balance'].sum() * -1
leakage_monthly = 145000 # Допустим, сумма штрафов из таблицы
ltv_potential = df['customs_fee_forecast'].sum() * 0.2 # Пример маржи 20%

m1.metric("Money at Risk (Дебиторка)", f"{money_at_risk:,.0f} ₽", "-12% за неделю")
m2.metric("Leakage (Утечки мес.)", f"{leakage_monthly:,.0f} ₽", "Штрафы/Простои", delta_color="inverse")
m3.metric("LTV Potential (Прогноз)", f"{ltv_potential:,.0f} ₽", "Текущий поток")
m4.metric("Активных клиентов", len(df['client_name'].unique()))

st.markdown("---")

# 4. ГЛАВНАЯ ПАНЕЛЬ: Система "Светофор"
st.subheader("🚨 Мониторинг критических зон (по клиентам)")

# Создаем таблицу для собственника
summary_data = []
for client in df['client_name'].unique():
    c_df = df[df['client_name'] == client].iloc[0]
    
    summary_data.append({
        "Клиент": client,
        "Менеджер": c_df['manager_name'],
        "Финансы": get_money_light(c_df),
        "Операции": get_ops_light(c_df),
        "Лояльность": get_retention_light(c_df),
        "Безопасность": "🟢", # Сюда можно прикрутить проверку доков
        "Текущий баланс": f"{c_df['balance']:,.0f} ₽",
        "Shipment ID": c_df['shipment_id']
    })

owner_df = pd.DataFrame(summary_data)
st.table(owner_df) # Используем таблицу для наглядности "лампочек"

# 5. DRILL-DOWN: Детализация по клику
st.markdown("---")
st.subheader("🔍 Детальный разбор проблемной зоны")

selected_client_owner = st.selectbox("Выберите клиента для анализа рисков:", owner_df['Клиент'])
client_detail = df[df['client_name'] == selected_client_owner].iloc[0]

col_left, col_right = st.columns(2)

with col_left:
    st.info(f"**Анализ рисков для {selected_client_owner}**")
    if client_detail['balance'] < 0:
        st.error(f"⚠️ **Финансовый риск:** Задолженность {client_detail['balance']} ₽. Рекомендация: Остановить отгрузку до оплаты.")
    
    if client_detail['demurrage_free_days'] <= 3:
        st.warning(f"🕒 **Операционный риск:** Осталось {client_detail['demurrage_free_days']} дня бесплатного хранения. Убыток через 48 часов.")

with col_right:
    st.write(f"**Ответственный менеджер:** {client_detail['manager_name']}")
    st.button(f"📞 Связаться с менеджером по {selected_client_owner}")
    st.button(f"📧 Отправить уведомление клиенту о задолженности")

# 6. АНАЛИТИКА ЭФФЕКТИВНОСТИ (Нижний блок)
with st.expander("📊 Глобальная аналитика задержек и маржинальности"):
    # Пример графика зависимости задержек от границ
    delay_analysis = df.groupby('border_congestion')['delay_days'].mean().reset_index()
    st.bar_chart(delay_analysis, x='border_congestion', y='delay_days', color="#c41230")
    st.caption("Средняя задержка в зависимости от загруженности границ")
