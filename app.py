# ---------------------------------------------
# Импорт необходимых библиотек и классов
# ---------------------------------------------
from fastapi import FastAPI, Request, Form           # FastAPI и инструменты для работы с запросами и формами
from fastapi.templating import Jinja2Templates       # Шаблонизатор Jinja2 для FastAPI
from fastapi.responses import HTMLResponse           # Класс-ответ для возврата HTML
from datetime import datetime, date
from babel.dates import format_date
from typing import List, Dict

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
def amortization_schedule(
    principal: float,
    annual_rate: float,
    years: int,
    start_year: int = 2025,
    start_month: int = 3
) -> (List[Dict], List[Dict]):
    """
    Возвращает два списка:
      1) schedule: список словарей с графиком погашения кредита по годам:
         [
           {
             'year': N,
             'payment': сумма платежей за год,
             'interest': сумма процентов за год,
             'principal_paid': сумма гашения тела кредита за год,
             'balance': остаток долга в конце года,
             'cumulative_paid': кумулятивная сумма выплат к концу года
           },
           ...
         ]
      2) monthly_details: список из 12 словарей (помесячный разбор первого года):
         {
           'month': "Месяц Год" (например, "Март 2025"),
           'payment': ежемесячный платёж,
           'interest': проценты за этот месяц,
           'principal': погашение тела за этот месяц,
           'balance': остаток долга после этого платежа,
           'cumulative_paid': кумулятивная сумма выплат к этому месяцу
         }
    """
    r_month = annual_rate / 100 / 12
    total_months = years * 12

    # Если процентная ставка или principal равны нулю, возвращаем пустые списки
    if principal <= 0 or annual_rate <= 0 or years <= 0:
        return [], []

    annuity = principal * r_month / (1 - (1 + r_month) ** -total_months)

    balance = principal
    schedule: List[Dict] = []
    monthly_details: List[Dict] = []
    cumulative_paid = 0.0

    current_month = start_month
    current_year = start_year

    for year in range(1, years + 1):
        interest_year = 0.0
        principal_year = 0.0
        payments_for_year = []

        for m in range(12):
            interest_month = balance * r_month
            principal_month = annuity - interest_month
            balance -= principal_month
            interest_year += interest_month
            principal_year += principal_month
            cumulative_paid += annuity

            if year == 1:  # только первый год помесячно
                month_name = format_date(
                    datetime(current_year, current_month, 1),
                    format="LLLL",
                    locale="ru_RU"
                ).capitalize()
                payments_for_year.append({
                    'month': f"{month_name} {current_year}",
                    'payment': round(annuity, 2),
                    'interest': round(interest_month, 2),
                    'principal': round(principal_month, 2),
                    'balance': round(balance if balance > 0 else 0.0, 2),
                    'cumulative_paid': round(cumulative_paid, 2)
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
            'balance': round(balance if balance > 0 else 0.0, 2),
            'cumulative_paid': round(cumulative_paid, 2)
        })

        if year == 1:
            monthly_details = payments_for_year.copy()

    return schedule, monthly_details


def annuity_payment(principal: float, annual_rate: float, years: int) -> float:
    """
    Рассчитывает ежемесячный аннуитетный платёж по кредиту.
    :param principal: сумма кредита (руб.)
    :param annual_rate: годовая ставка (%)
    :param years: срок кредита (лет)
    :return: ежемесячный платёж (руб.)
    """
    if principal <= 0 or annual_rate <= 0 or years <= 0:
        return 0.0
    r_month = annual_rate / 100 / 12  # месячная ставка
    n = years * 12                    # общее число платежей
    return principal * r_month / (1 - (1 + r_month) ** -n)


def accumulate_deposit(initial: float, annual_rate: float, years: int) -> float:
    """
    Считает итоговую сумму накоплений при единовременном вложении на депозит.
    :param initial: начальная сумма (руб.)
    :param annual_rate: годовая ставка (%)
    :param years: срок накопления (лет)
    :return: итоговая сумма накоплений (руб.)
    """
    if initial <= 0 or annual_rate <= 0 or years <= 0:
        return initial
    return initial * ((1 + annual_rate / 100) ** years)


def adjust_inflation(amount: float, years: float, inflation: float) -> float:
    """
    Приводит будущую сумму к текущей стоимости с учётом инфляции.
    :param amount: будущая сумма (руб.)
    :param years: период дисконтирования (лет)
    :param inflation: годовая инфляция (%)
    :return: дисконтированная стоимость (руб.)
    """
    if inflation <= 0 or years <= 0:
        return amount
    return amount / ((1 + inflation / 100) ** years)


# ---------------------------------------------
# Обработка GET-запроса – отображение формы
# ---------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def show_form(request: Request):
    """
    Возвращает HTML-страницу form.html для ввода параметров:
      - cost: стоимость жилья (₽)
      - initial_savings: начальная сумма сбережений (₽)
      - limit_payment: максимальный ежемесячный платёж (₽)
      - mortgage_rate: ставка по ипотеке (% годовых)
      - loan_term_years: срок кредита (лет)
      - save_years: сколько лет копить на вкладе (лет)
      - deposit_rate: ставка по вкладу (% годовых)
    """
    return templates.TemplateResponse("form.html", {"request": request})


# ---------------------------------------------
# Обработка POST-запроса – расчёт и отчёт
# ---------------------------------------------
@app.post("/расчёт_ипотеки", response_class=HTMLResponse)
async def generate_report(
    request: Request,
    cost: float = Form(..., gt=0),                # Стоимость жилья, ₽
    initial_savings: float = Form(..., ge=0),      # Начальная сумма сбережений, ₽
    limit_payment: float = Form(..., gt=0),        # Максимальный ежемесячный платёж, ₽
    mortgage_rate: float = Form(..., gt=0),        # Ставка по ипотеке, % годовых
    loan_term_years: int = Form(..., gt=0),        # Срок кредита, лет
    save_years: int = Form(..., ge=0),             # Сколько лет копить на вкладе, лет
    deposit_rate: float = Form(..., ge=0)          # Ставка по вкладу, % годовых
):
    """
    Логика:
      1) Рассчитываем, сколько будет накоплено: A1 = initial_savings * (1 + deposit_rate/100)^save_years
      2) principal = max(0, cost - A1) – сумму, которую берём в ипотеку.
      3) Ежемесячный аннуитетный платёж: fixed_monthly_payment = annuity_payment(principal, mortgage_rate, loan_term_years)
      4) Определяем флаг payment_exceeds, если платёж выше limit_payment.
      5) Строим график amortization_schedule(principal, mortgage_rate, loan_term_years).
      6) Считаем «Полную стоимость кредита»:
         - Без учёта вклада: берём principal0 = cost, вычисляем annuity0 и nominal0 = annuity0 * 12 * years0.
         - С учётом вклада: nominal1 = fixed_monthly_payment * 12 * loan_term_years.
    """
    # 1) Считаем накопления, если нужно
    if save_years > 0 and deposit_rate > 0:
        A1 = accumulate_deposit(initial_savings, deposit_rate, save_years)
    else:
        A1 = initial_savings

    # 2) Сколько осталось взять в ипотеку
    principal = max(0.0, cost - A1)

    # 3) Ежемесячный аннуитетный платёж
    fixed_monthly_payment = annuity_payment(principal, mortgage_rate, loan_term_years)

    # 4) Проверяем на превышение лимита
    payment_exceeds = (fixed_monthly_payment > limit_payment)

    # 5) Проверяем, нужен ли вообще кредит (если principal == 0)
    no_credit = (principal == 0.0)

    # Если кредит нужен, строим график погашения по остаточному principal
    if not no_credit:
        start_year = date.today().year
        start_month = date.today().month
        schedule, monthly_details = amortization_schedule(
            principal=principal,
            annual_rate=mortgage_rate,
            years=loan_term_years,
            start_year=start_year,
            start_month=start_month
        )
    else:
        schedule = []
        monthly_details = []

    # 6) Считаем «Полную стоимость кредита»
    # 6.1) Без учёта вклада (если бы principal0 = cost)
    fixed_payment_full = annuity_payment(cost, mortgage_rate, loan_term_years)
    nominal_full = fixed_payment_full * loan_term_years * 12
    # 6.2) С учётом вклада (по уже вычисленному principal)
    nominal_after_deposit = fixed_monthly_payment * loan_term_years * 12 if not no_credit else 0.0

    return templates.TemplateResponse("report.html", {
        "request": request,

        # Введённые параметры
        "cost": f"{cost:,.0f}",
        "initial_savings": f"{initial_savings:,.0f}",
        "save_years": save_years,
        "deposit_rate": deposit_rate,

        # Накоплено и остаток
        "A1": f"{A1:,.0f}",
        "principal": f"{principal:,.0f}",

        # Параметры кредита
        "mortgage_rate": mortgage_rate,
        "loan_term_years": loan_term_years,
        "limit_payment": f"{limit_payment:,.0f}",

        # Ежемесячный платёж и проверка лимита
        "fixed_monthly_payment": f"{fixed_monthly_payment:,.2f}",
        "payment_exceeds": payment_exceeds,

        # Полные стоимости кредита
        "nominal_full": f"{nominal_full:,.0f}",
        "nominal_after_deposit": f"{nominal_after_deposit:,.0f}",

        # Графики
        "monthly_details": monthly_details,
        "schedule": schedule,

        # Флаг «кредит не нужен»
        "no_credit": no_credit
    })
