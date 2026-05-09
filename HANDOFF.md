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
- Страница `/login` — вход по email (magic link) ✅ (только что создана, ещё не задеплоена)
- Кнопка "Войти" в хедере ✅ (только что добавлена, ещё не задеплоена)
- Скачивание: docx, pdf, instruction (3 кнопки на странице заказа)

## Что НЕ сделано / нужно сделать

### Срочно
1. **Задеплоить последние изменения** (страница /login, кнопка Войти, фикс nav):
   ```bash
   cd /opt/lawdocs && git pull && docker compose -f docker-compose.prod.yml build frontend && docker compose -f docker-compose.prod.yml up -d frontend
   ```

2. **SMTP** — без него magic link и письма не работают. В `/opt/lawdocs/backend/.env`:
   ```
   SMTP_HOST=smtp.mailtrap.io       # или другой провайдер
   SMTP_PORT=587
   SMTP_USER=...
   SMTP_PASSWORD=...
   SMTP_STARTTLS=true
   EMAIL_FROM=noreply@law-docs.ru
   ```
   После → `docker compose -f docker-compose.prod.yml restart backend`

3. **GigaChat API** — без него LLM заглушка, документы не генерируются. В `.env`:
   ```
   GIGACHAT_CLIENT_ID=...
   GIGACHAT_CLIENT_SECRET=...
   ```

4. **ЮКасса** — после регистрации ИП. В `.env`:
   ```
   YOOKASSA_SHOP_ID=...
   YOOKASSA_SECRET_KEY=...
   ```
   Webhook URL для ЮКасса: `https://law-docs.ru/api/v1/webhooks/yookassa`

### Позже
- SSH доступ к серверу сломан (FlClashX прокси блокирует). Пока работаем через Timeweb web console. Лечится добавлением `186.246.4.164` в bypass-правила прокси.
- Страница "Не нашли ситуацию?" — сейчас ведёт на mailto:, обсуждается лучшее решение.
- Личный кабинет доступен на `/dashboard` после входа через magic link.

## Ключевые файлы

| Файл | Что делает |
|---|---|
| `/opt/lawdocs/backend/.env` | Все секреты прода |
| `/opt/lawdocs/docker-compose.prod.yml` | Prod compose |
| `/etc/nginx/sites-available/lawdocs` | Nginx конфиг |
| `backend/app/api/v1/webhooks.py` | Webhook ЮКасса → генерация |
| `backend/app/services/docgen.py` | Генерация docx/pdf/instruction |
| `backend/app/services/llm.py` | GigaChat: fill_template + fill_instruction |
| `backend/app/situations/` | YAML конфиги 7 ситуаций |
| `frontend/app/login/page.tsx` | Страница входа (magic link) |
| `frontend/components/layout/header.tsx` | Хедер с кнопкой Войти |

## Команды на сервере (через Timeweb web console)

```bash
# Статус контейнеров
cd /opt/lawdocs && docker compose -f docker-compose.prod.yml ps

# Перезапуск бэкенда (после изменения .env)
docker compose -f docker-compose.prod.yml restart backend

# Логи бэкенда
docker compose -f docker-compose.prod.yml logs backend --tail=50

# Полный редеплой фронта
docker compose -f docker-compose.prod.yml build frontend && docker compose -f docker-compose.prod.yml up -d frontend
```
