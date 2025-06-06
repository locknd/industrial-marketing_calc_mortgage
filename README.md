# Калькулятор ипотеки с учётом вклада и инфляции

## О проекте

Этот проект — веб-приложение на FastAPI, которое помогает пользователям рассчитать два сценария ипотечного кредитования с учётом накоплений на депозит и инфляции. Приложение сравнивает несколько банков и показывает детальные графики погашения кредита.

---

## Основные возможности

- Расчёт аннуитетного платежа по ипотеке.
- Учет инфляции для оценки реальной стоимости выплат.
- Модель накопления вклада на часть суммы ипотеки с учетом процентов.
- Сравнение условий пяти популярных банков (Сбербанк, Альфа-Банк, ВТБ, Тинькофф, ГазпромБанк).
- Подробные графики платежей с разбивкой по месяцам и годам.

## Проверка работы калькулятора

- Введите свои данные: доход, сумму кредита, срок, инфляцию, процент от зарплаты на вклад, годы накопления.
- Нажмите кнопку расчёта.
- Просмотрите сравнение предложений банков и детальные графики платежей.

## Использование

  1. Ипотека берётся сразу.
  2. Cначала копятся деньги на депозит, затем берётся ипотека на остаток.

---

## Технологии

- Python 3.12
- FastAPI — для создания веб-сервера
- Jinja2 — для шаблонов HTML
- Babel — для форматирования дат на русском языке
- Uvicorn — ASGI-сервер

---