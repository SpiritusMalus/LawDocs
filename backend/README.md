# LawDocs — Backend

FastAPI бэкенд для Phase 2 (после валидации спроса). Сейчас — скелет, не используется в проде.

## Требования

- **Python** 3.11 или новее
- **PostgreSQL** 16

---

## Локальный запуск

```bash
# 1. Перейти в папку бэкенда
cd backend

# 2. Создать виртуальную среду
python -m venv .venv

# 3. Активировать
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 4. Установить зависимости
pip install -r requirements.txt

# 5. Создать файл с переменными окружения
cp .env.example .env
# Заполнить минимум: SECRET_KEY и DATABASE_URL

# 6. Применить миграции (нужен запущенный Postgres)
alembic upgrade head

# 7. Запустить сервер
uvicorn app.main:app --reload
```

Swagger UI откроется на **<http://127.0.0.1:8000/docs>**

---

## Переменные окружения

Минимум для запуска:

| Переменная | Описание |
| --- | --- |
| `SECRET_KEY` | Случайная строка для JWT. Сгенерировать: `openssl rand -hex 32` |
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost:5432/lawdocs` |

Остальные переменные (GigaChat, ЮKassa, SMTP, S3) нужны только в продакшене — без них сервер запустится, соответствующие сервисы будут работать в режиме заглушки.

---

## Миграции базы данных

```bash
# Создать новую миграцию (после изменения моделей)
alembic revision --autogenerate -m "описание изменений"

# Применить все миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

---

## Структура проекта

```text
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, роуты
│   ├── core/
│   │   ├── config.py           # все настройки через pydantic-settings
│   │   ├── database.py         # async SQLAlchemy engine + Base
│   │   └── security.py         # JWT + magic link токен
│   ├── models/
│   │   ├── user.py             # User (email, magic link)
│   │   ├── order.py            # Order (ситуация, статус, ЮKassa)
│   │   └── document.py         # Document (S3 ключи)
│   ├── schemas/
│   │   ├── user.py             # MagicLinkRequest, UserOut
│   │   ├── order.py            # OrderCreate, OrderOut, PaymentOut
│   │   └── document.py         # DocumentOut
│   ├── api/
│   │   ├── deps.py             # get_db, get_current_user
│   │   └── v1/
│   │       ├── auth.py         # POST /magic-link, GET /verify, POST /logout
│   │       ├── orders.py       # POST /orders, GET /orders/{id}
│   │       ├── documents.py    # GET /documents/{order_id}
│   │       └── webhooks.py     # POST /webhooks/yookassa
│   ├── services/
│   │   ├── llm.py              # GigaChat + Claude fallback
│   │   ├── docgen.py           # python-docx → PDF + S3 upload
│   │   ├── payment.py          # ЮKassa API
│   │   └── email.py            # magic link + уведомление о документе
│   └── templates/              # .docx шаблоны от юриста (пусто до Phase 2)
└── alembic/                    # миграции
```

---

## Флоу Phase 2

```text
Пользователь проходит wizard-форму
        ↓
POST /orders → создаём заказ в БД
        ↓
Редирект на ЮKassa для оплаты
        ↓
ЮKassa вызывает POST /webhooks/yookassa
        ↓
LLM (GigaChat) заполняет шаблон документа
        ↓
python-docx собирает .docx → PDF
        ↓
Файлы загружаются в S3
        ↓
Email пользователю со ссылкой на скачивание
```
