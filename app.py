# ---------------------------------------------
# Импорт необходимых библиотек и классов
# ---------------------------------------------
from fastapi import FastAPI, Request, Form           # FastAPI и инструменты для работы с запросами и формами
from fastapi.templating import Jinja2Templates       # Шаблонизатор Jinja2 для FastAPI
from fastapi.responses import HTMLResponse           # Класс-ответ для возврата HTML
from datetime import datetime, date
from babel.dates import format_date
# ---------------------------------------------
# Инициализация приложения и указание папки с шаблонами
# ---------------------------------------------
app = FastAPI()  # Создаем экземпляр FastAPI
templates = Jinja2Templates(directory="templates")  # Папка, где лежат HTML-шаблоны
today = date.today()
formatted = format_date(today, format='long', locale='ru_RU')
# ---------------------------------------------
# Вспомогательные функции для финансовых расчётов
# ---------------------------------------------
def amortization_schedule(principal: float, annual_rate: float, years: int, start_year: int = 2025, start_month: int = 3):
    """
    Возвращает список словарей с графиком погашения кредита по годам:
      [
        {
          'year': 1,
          'payment': ...,         # сумма платежей за год
          'interest': ...,        # сумма процентов за год
          'principal_paid': ...,  # сумма гашения тела кредита за год
          'balance': ...          # остаток долга в конце года
        },
        ...
      ]
    """
    r = annual_rate / 100 / 12
    n = years * 12
    annuity = principal * r / (1 - (1 + r) ** -n)

    balance = principal
    schedule = []
    monthly_details = []

    current_month = start_month
    current_year = start_year

    for year in range(1, years + 1):
        interest_year = 0.0
        principal_year = 0.0
        payments = []

        for m in range(12):
            interest_month = balance * r
            principal_month = annuity - interest_month
            balance -= principal_month
            interest_year += interest_month
            principal_year += principal_month

            if year == 1:  # только первый год помесячно
                month_name = format_date(datetime(current_year, current_month, 1), format="LLLL", locale="ru_RU").capitalize()
                payments.append({
                    'month': f"{month_name} {current_year}",
                    'payment': round(annuity, 2),
                    'interest': round(interest_month, 2),
                    'principal': round(principal_month, 2),
                    'balance': round(balance if balance > 0 else 0.0, 2)
                })

            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        schedule.append({
            'year': year,
            'payment': round(annuity * 12, 2),
            'interest': round(interest_year, 2),
            'principal_paid': round(principal_year, 2),
            'balance': round(balance if balance > 0 else 0.0, 2)
        })

        if year == 1:
            monthly_details = payments

    return schedule, monthly_details



def annuity_payment(principal: float, annual_rate: float, years: int) -> float:
    """
    Рассчитывает ежемесячный аннуитетный платёж по кредиту.
    :param principal: сумма кредита (руб.)
    :param annual_rate: годовая ставка (%)
    :param years: срок кредита (лет)
    :return: ежемесячный платёж (руб.)
    """
    r = annual_rate / 100 / 12  # месячная ставка
    n = years * 12              # общее число платежей
    return principal * r / (1 - (1 + r) ** -n)


def accumulate_deposit(monthly: float, annual_rate: float, years: int) -> float:
    """
    Считает итоговую сумму накоплений при ежемесячном пополнении вклада.
    :param monthly: сумма взноса в месяц (руб.)
    :param annual_rate: годовая ставка (%)
    :param years: срок накопления (лет)
    :return: итоговая сумма накоплений (руб.)
    """
    r = annual_rate / 100 / 12
    n = years * 12
    return monthly * (((1 + r) ** n - 1) / r)


def adjust_inflation(amount: float, years: float, inflation: float) -> float:
    """
    Приводит будущую сумму к текущей стоимости с учётом инфляции.
    :param amount: будущая сумма (руб.)
    :param years: период дисконтирования (лет)
    :param inflation: годовая инфляция (%)
    :return: дисконтированная стоимость (руб.)
    """
    return amount / ((1 + inflation / 100) ** years)

# ---------------------------------------------
# Обработка GET-запроса – отображение формы
# ---------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def show_form(request: Request):
    """
    Возвращает HTML-страницу form.html для ввода параметров:
      - salary: доход в месяц (₽)
      - loan_amount: сумма кредита (₽)
      - loan_term_years: срок кредита (лет)
      - inflation_rate: инфляция (%)
      - deposit_share_pct: % зарплаты на вклад
      - deposit_delay_years: годы копления
    """
    return templates.TemplateResponse(
        "form.html",
        {"request": request}
    )

# ---------------------------------------------
# Обработка POST-запроса – расчёт и отчёт
# ---------------------------------------------
@app.post("/расчёт_ипотеки", response_class=HTMLResponse)
async def generate_report(
    request: Request,
    salary: float = Form(..., gt=0),                   # доход в месяц (₽)
    loan_amount: float = Form(..., gt=0),               # сумма кредита (₽)
    loan_term_years: int = Form(..., gt=1),             # срок кредита (лет)
    inflation_rate: float = Form(..., ge=0),            # инфляция (%)
    deposit_share_pct: int = Form(..., ge=0, le=100),   # % зарплаты на вклад
    deposit_delay_years: int = Form(..., ge=0)          # годы копления перед ипотекой
):
    """
    Рассчитывает два сценария по каждому банку:
    A) ипотека сразу
    B) вклад долей зарплаты + ипотека на остаток
    Добавляет ПСК и два графика погашения: до и после вклада.
    """
    deposit_share = deposit_share_pct / 100

    banks = {
        'Сбербанк':    (8.0, 4.0),
        'Альфа-Банк':  (9.0, 5.0),
        'ВТБ':         (9.5, 4.5),
        'Тинькофф':    (10.0, 5.5),
        'ГазпромБанк': (8.2, 5.0),
    }

    rows = []
    schedules_now = {}
    schedules_later = {}
    monthly_schedules = {}

    # Параметры начала ипотеки
    start_year = 2025
    start_month = 3

    for name, (mort_rate, dep_rate) in banks.items():
        # Сценарий A – ипотека сразу
        pay_now = annuity_payment(loan_amount, mort_rate, loan_term_years)
        nominal_now = pay_now * loan_term_years * 12
        real_now = adjust_inflation(nominal_now, loan_term_years, inflation_rate)
        full_cost_now = (nominal_now - loan_amount) / loan_amount * 100
        # Сценарий B – вклад + ипотека
        monthly_contrib = salary * deposit_share
        savings = accumulate_deposit(monthly_contrib, dep_rate, deposit_delay_years)
        remaining = max(0, loan_amount - savings)
        # График погашения для полной суммы
        schedule_now, monthly_now = amortization_schedule(loan_amount, mort_rate, loan_term_years, start_year, start_month)
        schedules_now[name] = schedule_now
        # График погашения для остатка
        schedule_later, monthly_later = amortization_schedule(remaining, mort_rate, loan_term_years, start_year + deposit_delay_years, start_month)
        schedules_later[name] = schedule_later
        pay_later = annuity_payment(remaining, mort_rate, loan_term_years) if remaining > 0 else 0
        nominal_later = pay_later * loan_term_years * 12
        real_later = adjust_inflation(nominal_later, deposit_delay_years + loan_term_years / 2, inflation_rate)
        full_cost_later = (nominal_later + savings - loan_amount) / loan_amount * 100 if remaining > 0 else 0

        monthly_schedules[name] = {
            "now": monthly_now,
            "later": monthly_later
        }
        rows.append({
            'bank': name,
            'pay_now': pay_now,
            'real_now': real_now,
            'pay_later': pay_later,
            'real_later': real_later,
            'nominal_now': nominal_now,
            'full_cost_now': full_cost_now,
            'nominal_later': nominal_later,
            'full_cost_later': full_cost_later
        })

    
    return templates.TemplateResponse(
        "report.html",
        {
            'request': request,
            'salary': f"{salary:,.0f}",
            'loan_amount': f"{loan_amount:,.0f}",
            'loan_term_years': loan_term_years,
            'inflation_rate': inflation_rate,
            'deposit_share_pct': deposit_share_pct,
            'deposit_delay_years': deposit_delay_years,
            'rows': rows,
            'schedules_now': schedules_now,
            'schedules_later': schedules_later,
            'monthly_schedules': monthly_schedules
        }
    )
# ---------------------------------------------
# Запуск: uvicorn app:app --reload
# ---------------------------------------------