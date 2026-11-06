# Leovit Corporate Portal

Корпоративный портал компании Leovit.

## Технологии

- Python 3.13
- Django 5.2 LTS
- PostgreSQL 18
- Bootstrap 5
- Nginx + Gunicorn

## Разделы

- `/` — главная страница и дайджесты
- `/tickets/` — сервис заявок
- `/forms/` — формы
- `/contacts/` — телефонный справочник
- `/access/` — ссылки на корпоративные ресурсы

## Разработка

Разработка ведётся в ветке `develop`.

Ветка `main` содержит проверенную версию
для production.

## Локальный запуск

1. Создать виртуальное окружение Python 3.13.
2. Установить зависимости.
3. Создать `.env` на основе `.env.example`.
4. Создать базу PostgreSQL `leovit_portal`.
5. Создать пользователя БД `leovit_portal_user`.
6. Выполнить миграции.
7. Запустить сервер.

Команды:

```powershell
python -m pip install -r requirements/development.txt
python manage.py migrate
python manage.py runserver