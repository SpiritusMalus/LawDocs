# LawDocs

B2C-сервис: AI-помощник превращает бытовую проблему в готовый юридический документ за 500 ₽.
Претензии в магазин, банк, работодателю, страховой, УК, авиакомпанию — 7 типовых ситуаций.

## Быстрый старт (Docker)

```bash
cp backend/.env.example backend/.env
# Отредактируйте backend/.env: SECRET_KEY, DATABASE_URL, и т.д.

cp frontend/.env.example frontend/.env.local
# Добавьте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID

docker compose up --build
```

Сервисы:
- Фронт: http://localhost:3000
- Бэкенд API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs (только в development)

## Локальная разработка (без Docker)

**Фронт:**
```bash
cd frontend
npm install
cp .env.example .env.local   # заполнить TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
npm run dev                   # http://localhost:3000
```

**Бэкенд** (нужен Postgres 16):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # заполнить SECRET_KEY, DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload  # http://localhost:8000
```

## Структура проекта

```
LawDocs/
├── frontend/               # Next.js 16 (App Router)
│   ├── app/
│   │   ├── (landing)/      # Главная страница
│   │   ├── situations/     # SEO-страницы ситуаций
│   │   ├── wizard/         # Форма оформления документа
│   │   ├── orders/[id]/    # Статус заказа (Phase 2)
│   │   ├── auth/           # Magic link auth (Phase 2)
│   │   └── api/            # Прокси-роуты к бэкенду
│   ├── components/
│   └── lib/
├── backend/                # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/v1/         # orders, auth, documents, webhooks
│   │   ├── models/         # SQLAlchemy ORM
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # llm, docgen, payment, email
│   │   └── core/           # config, database, security
│   └── alembic/            # Миграции
├── docker-compose.yml
├── nginx.conf
├── STUBS.md                # Список заглушек для production
└── DEPLOY.md               # Инструкция по деплою на VPS
```

## Режимы работы

| Переменная | Значение | Поведение |
|---|---|---|
| `BACKEND_URL` не задан | Phase 1 | Wizard → Telegram, ручная обработка |
| `BACKEND_URL=http://backend:8000` | Phase 2 | Wizard → FastAPI → magic link → оплата → документ |

## Заглушки

Подробности в [STUBS.md](STUBS.md). В dev-режиме:
- ЮKassa → `/dev/payment` (симуляция)
- SMTP → лог в stdout
- S3 → файлы не сохраняются

## Стек

- **Frontend**: Next.js 16.2, React 19, Tailwind v4, shadcn/base-nova
- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, asyncpg
- **LLM**: GigaChat (основной) + Claude (fallback)
- **Платежи**: ЮKassa
- **Auth**: Magic link → JWT в httpOnly cookie
