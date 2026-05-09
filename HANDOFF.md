# LawDocs — Handoff

## Проект
B2C AI-юрист: пользователь заполняет форму → получает готовую претензию (Word + PDF) + инструкцию → 500 ₽.  
Репо: `d:\Projects\LawDocs\` (backend — FastAPI, frontend — Next.js 16)

## Что уже сделано (полностью готово)

### Инфраструктура
- VPS Timeweb: `186.246.4.164`, Ubuntu 24
- Docker Compose prod: `backend`, `frontend`, `postgres` — все запущены
- Nginx reverse proxy → `127.0.0.1:3000`
- Cloudflare: DNS активен, SSL mode = **Flexible**, домен **law-docs.ru** работает ✅

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
- Страница `/login` — вход по email (magic link) ✅ (готова локально, требует деплоя на сервер)
- Кнопка "Войти" в хедере ✅ (готова локально, требует деплоя на сервер)
- API route `/api/auth/magic-link` — проксирует запрос на бэк ✅
- Скачивание: docx, pdf, instruction (3 кнопки на странице заказа)

## Что НЕ сделано / нужно сделать

### Срочно (Блокеры функциональности)

1. **Деплой фронта на VPS** — `/login` и кнопка "Войти" требуют обновления контейнера:
   ```bash
   cd /opt/lawdocs && git pull origin main
   docker compose -f docker-compose.prod.yml build frontend
   docker compose -f docker-compose.prod.yml up -d frontend
   ```
   **Статус:** коммиты в гите (95ffdb8), требуется pull + rebuild на VPS.

2. **SMTP (Gmail)** — без него magic link и письма не работают:
   - На локальной машине: включить 2FA в Gmail аккаунте
   - Создать App Password: https://myaccount.google.com/apppasswords
   - На VPS в `/opt/lawdocs/backend/.env` заменить:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=твой_email@gmail.com
   SMTP_PASSWORD=xxxxxxxxxxxxxxxx
   SMTP_TLS=false
   SMTP_STARTTLS=true
   EMAIL_FROM=твой_email@gmail.com
   ```
   - Перезапустить бэк: `docker compose -f docker-compose.prod.yml restart backend`
   **Статус:** готово к настройке, ждёт App Password от Google.

3. **GigaChat API** — без него LLM заглушка, документы не генерируются:
   ```
   GIGACHAT_AUTH_KEY=...      (готовый Base64 из консоли разработчика)
   ```
   **Статус:** требует ключей из Сбера.

4. **ЮКасса** — после регистрации ИП:
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
| `/opt/lawdocs/backend/.env` | Все секреты прода (SMTP, GigaChat, ЮКасса) |
| `/opt/lawdocs/docker-compose.prod.yml` | Prod compose (backend, frontend, postgres, nginx) |
| `/etc/nginx/sites-available/lawdocs` | Nginx конфиг (reverse proxy на фронт) |
| `backend/app/core/config.py` | Конфиг Settings (читает .env) |
| `backend/app/services/email.py` | SMTP клиент (aiosmtplib) для письма |
| `backend/app/api/v1/auth.py` | Endpoints: `/magic-link`, `/verify` |
| `backend/app/api/v1/webhooks.py` | ЮКасса webhook → генерация документов |
| `backend/app/services/docgen.py` | Генерация docx/pdf/instruction |
| `backend/app/services/llm.py` | GigaChat: fill_template + fill_instruction |
| `backend/app/situations/` | YAML конфиги 7 ситуаций |
| `frontend/app/login/page.tsx` | Страница входа (форма email) |
| `frontend/app/api/auth/magic-link/route.ts` | API route проксирует на бэк |
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
