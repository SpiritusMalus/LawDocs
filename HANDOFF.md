# LawDocs — Handoff

## Проект
B2C AI-юрист: пользователь заполняет форму → получает готовую претензию (Word + PDF) + инструкцию → 500 ₽.  
Репо: `d:\Projects\LawDocs\` (backend — FastAPI, frontend — Next.js 16)

## Что уже сделано (полностью готово)

### Инфраструктура
- VPS Timeweb: `186.246.4.164`, Ubuntu 24, Ubuntu 24
- Docker Compose prod: `backend`, `frontend`, `postgres`, `nginx` — все запущены ✅
- **Nginx reverse proxy** в Docker:
  - Прослушивает `0.0.0.0:80` и `0.0.0.0:443`
  - Проксирует `/api/*` → `backend:8000/api/v1/`
  - Остальное → `frontend:3000`
  - Конфиги в `nginx/nginx.conf` и `nginx/conf.d/default.conf`
- Cloudflare: DNS активен, SSL mode = **Flexible**, домен **law-docs.ru** работает ✅
- **Исходящие SMTP порты открыты** (587, 465) на VPS ✅

### Backend (FastAPI)
- Magic link auth (POST `/api/v1/auth/magic-link`, GET `/api/v1/auth/verify`)
- JWT в httpOnly cookie, 7 дней
- 7 ситуаций в YAML registry с legal_refs (ссылки на КонсультантПлюс)
- Генерация pretenziya: docxtpl → docx + pdf
- Генерация instruction: fpdf2 с кликабельными ссылками на законы
- Webhook ЮКасса (payment.succeeded → generating → done)
- Email: magic link + document_ready (с вложениями) + document_failed
- Alembic миграции: documents.instruction_pdf_key добавлен

### Frontend (Next.js 16)
- Лендинг, страница ситуаций, wizard, order status, dashboard
- Страница `/login` — вход по email (magic link) ✅ **работает в production**
- Кнопка "Войти" в хедере ✅
- API route `/api/auth/magic-link` — проксирует запрос на бэк ✅
- API route `/auth/verify` — верификация токена, установка JWT cookie ✅
- Скачивание: docx, pdf, instruction (3 кнопки на странице заказа)

## Что НЕ сделано / нужно сделать

### ✅ Решено (больше не блокеры)
- ✅ **Nginx reverse proxy** — добавлен в Docker Compose, конфиги готовы
- ✅ **SMTP (Gmail)** — работает, magic link письма отправляются успешно
  - Порты 587/465 открыты на VPS firewall
  - SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_STARTTLS=true
  - Добавлен timeout (10s) в backend/app/services/email.py
- ✅ **Frontend login** — работает в production
  - Исправлена обработка 204 No Content ответа
  - Исправлены редиректы авторизации на правильный домен
  - Письма отправляются, верификация работает

### Срочно (Блокеры функциональности)

1. **GigaChat API** — без него LLM заглушка, документы не генерируются:
   ```
   GIGACHAT_AUTH_KEY=...      (готовый Base64 из консоли разработчика)
   ```
   **Статус:** требует ключей из Сбера.

2. **ЮКасса** — после регистрации ИП:
   ```
   YOOKASSA_SHOP_ID=...
   YOOKASSA_SECRET_KEY=...
   ```
   Webhook URL для ЮКасса: `https://law-docs.ru/api/v1/webhooks/yookassa`
   **Статус:** ждёт регистрации ИП и лицензирования.

### Позже
- SSH доступ к серверу сломан (FlClashX прокси блокирует). Пока работаем через Timeweb web console. Лечится добавлением `186.246.4.164` в bypass-правила прокси.
- Страница "Не нашли ситуацию?" — сейчас ведёт на mailto:, обсуждается лучшее решение.
- Личный кабинет доступен на `/dashboard` после входа через magic link.

## Ключевые файлы

| Файл | Что делает |
|---|---|
| `docker-compose.prod.yml` | Prod compose (backend, frontend, postgres, nginx) |
| `nginx/nginx.conf` | Основная конфигурация nginx (gzip, логирование, etc) |
| `nginx/conf.d/default.conf` | Проксирование: `/api/*` → backend, остальное → frontend |
| `backend/.env` | Все секреты прода (SMTP, GigaChat, ЮКасса) |
| `backend/app/core/config.py` | Конфиг Settings (читает .env) |
| `backend/app/services/email.py` | SMTP клиент (aiosmtplib) для письма с 10s timeout |
| `backend/app/api/v1/auth.py` | Endpoints: `POST /magic-link`, `GET /verify` |
| `backend/app/api/v1/webhooks.py` | ЮКасса webhook → генерация документов |
| `backend/app/services/docgen.py` | Генерация docx/pdf/instruction |
| `backend/app/services/llm.py` | GigaChat: fill_template + fill_instruction |
| `backend/app/situations/` | YAML конфиги 7 ситуаций |
| `frontend/app/login/page.tsx` | Форма входа, обработка 204 No Content |
| `frontend/app/auth/verify/route.ts` | Верификация токена, установка JWT cookie, редирект |
| `frontend/app/api/auth/magic-link/route.ts` | API route проксирует на backend |
| `frontend/components/layout/header.tsx` | Хедер с кнопкой "Войти" |

## Локальная разработка

```bash
# Backend
cd backend
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (отдельный терминал)
cd frontend
npm install
npm run dev
# http://localhost:3000
```

Для БД локально можно использовать Docker:
```bash
docker run --name lawdocs-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=lawdocs -p 5432:5432 -d postgres:16
```

## Команды на сервере (через Timeweb web console)

```bash
# Статус контейнеров
cd /opt/lawdocs && docker compose -f docker-compose.prod.yml ps

# Просмотр последних коммитов
git log --oneline -5

# Git pull + redeploy фронта
git pull origin main
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend

# Перезапуск бэкенда (после изменения .env)
docker compose -f docker-compose.prod.yml restart backend

# Логи бэкенда (для отладки SMTP, GigaChat, etc)
docker compose -f docker-compose.prod.yml logs backend --tail=50

# Логи фронта
docker compose -f docker-compose.prod.yml logs frontend --tail=50

# Редактирование .env
nano backend/.env
```
