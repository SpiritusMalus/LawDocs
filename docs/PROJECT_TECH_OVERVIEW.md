# LawDocs — Технический обзор проекта

## 1. Что такое проект

**LawDocs** — B2C SaaS-платформа, которая превращает бытовые правовые проблемы в профессионально оформленные юридические документы (претензии, жалобы, апелляции) за ~5 минут и 199 рублей. Пользователь проходит мастер-форму (wizard), отвечает на вопросы о своей ситуации, оплачивает, и система генерирует документ через GigaChat (с Claude-fallback), форматирует в .docx + PDF, шифрует E2EE-ключом пользователя и загружает в Яндекс Object Storage. Целевая аудитория — россияне в конфликтах с магазинами, банками, работодателями, страховщиками, ЖКХ и авиакомпаниями.

---

## 2. Стек технологий

| Слой | Технология | Версия |
|---|---|---|
| Backend | FastAPI + Uvicorn | 0.128.8 |
| ORM | SQLAlchemy (async) + asyncpg | — |
| Миграции | Alembic | — |
| База данных | PostgreSQL | 16-alpine |
| Frontend | Next.js + React | 16.2.6 / 19.2.4 |
| Стили | Tailwind CSS | 4 |
| UI-компоненты | Base UI (@base-ui/react) | 1.4.1 |
| Шрифты | Manrope Variable | — |
| Крипто (клиент) | TweetNaCl + Web Crypto API | 1.0.3 |
| Крипто (сервер) | PyNaCl + cryptography (Fernet) | — |
| LLM (основной) | GigaChat (Сбер) | API |
| LLM (fallback) | Claude 3.5 Sonnet (via OpenAI SDK) | API |
| Документы | python-docx + WeasyPrint | — |
| Платёжная система | ЮKassa | API |
| Файловое хранилище | Яндекс Object Storage (S3-совместимый) | — |
| Email | aiosmtplib | — |
| Rate limiting | slowapi | — |
| Reverse proxy | Nginx | — |
| Контейнеризация | Docker + Docker Compose | — |
| Мониторинг | Telegram-алерты | — |
| Аналитика | Яндекс Метрика | — |
| Тесты (frontend) | Playwright (e2e) + Vitest (unit) | — |
| Тесты (backend) | pytest | — |

---

## 3. Архитектура высокого уровня

```
                        ┌─────────────────────────────────────────────────┐
                        │                  law-docs.ru                     │
                        │                    Nginx                         │
                        │   /api/auth/ (rate-limited) → frontend:3000      │
                        │   /api/v1/webhooks/ → backend:8000 (real IP)     │
                        │   / → frontend:3000                              │
                        └───────────┬──────────────────┬───────────────────┘
                                    │                  │
                         ┌──────────▼──────┐  ┌────────▼────────┐
                         │   Frontend      │  │   Backend        │
                         │   Next.js 16    │  │   FastAPI 0.128  │
                         │   React 19      │  │   Uvicorn        │
                         │   port 3000     │  │   port 8000      │
                         └──────────┬──────┘  └────────┬────────┘
                                    │                  │
                          cookies   │         JWT auth │
                          (httpOnly)│                  │
                                    │         ┌────────▼────────┐
                                    │         │   PostgreSQL 16  │
                                    │         │   Async asyncpg  │
                                    │         └─────────────────┘
                                    │
                    ┌───────────────┴────────────────────┐
                    │         Внешние сервисы             │
                    ├──────────────────────────────────────┤
                    │  GigaChat API  (генерация текста)    │
                    │  Claude API    (fallback LLM)        │
                    │  ЮKassa API    (оплата)              │
                    │  Яндекс S3     (хранение файлов)     │
                    │  SMTP          (магические ссылки)   │
                    │  Telegram Bot  (алерты)              │
                    └──────────────────────────────────────┘
```

---

## 4. База данных

### Таблица `users`
| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | Идентификатор |
| email | str UNIQUE | Email пользователя |
| name | str \| None | Имя |
| completed_orders_count | int | Кол-во завершённых заказов |
| magic_token | str \| None | Хэш магической ссылки (SHA256) |
| magic_token_expires_at | datetime \| None | Срок действия токена |
| email_hash | str UNIQUE | SHA256(email) для zero-knowledge поиска |
| email_encrypted | bytes \| None | NaCl-зашифрованный email |
| name_encrypted | bytes \| None | NaCl-зашифрованное имя |
| password_hash | str \| None | Argon2 (задел на будущее) |
| public_key | str \| None | NaCl публичный ключ пользователя (base64) |
| private_key_backup_encrypted | str \| None | AES-GCM зашифрованный бэкап приватного ключа |
| consent_timestamp | datetime \| None | Время согласия на обработку ПДн |
| consent_ip | str \| None | IP при согласии |
| consent_version | str \| None | Версия политики |
| processing_restricted | bool | GDPR: ограничение обработки |
| processing_restricted_at | datetime \| None | Когда ограничили |
| created_at | datetime | Время создания |

### Таблица `orders`
| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | Идентификатор |
| user_id | UUID FK(users) | Владелец |
| situation_id | str | ID ситуации (из YAML) |
| status | enum | draft → pending_payment → paid → generating → done \| failed \| refunded |
| amount | int | Стоимость в копейках (19900 = 199 руб) |
| yookassa_payment_id | str \| None | ID платежа в ЮKassa |
| payment_url | str \| None | URL формы оплаты ЮKassa |
| form_data | dict (EncryptedJSON) | Ответы пользователя, зашифрованные Fernet |
| auto_retry_count | int | Кол-во автоматических повторов генерации |
| created_at | datetime | Время создания |
| paid_at | datetime \| None | Время оплаты |

### Таблица `documents`
| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | Идентификатор |
| order_id | UUID FK UNIQUE | Заказ (один документ на заказ) |
| docx_key | str | Путь в S3 для .docx |
| pdf_key | str | Путь в S3 для .pdf |
| instruction_pdf_key | str \| None | Путь в S3 для инструкции |
| user_encrypted | bool | Зашифрован ли файл публичным ключом пользователя |
| generated_at | datetime | Время генерации |

### Таблица `order_reviews`
| Поле | Тип | Описание |
|---|---|---|
| id | UUID PK | Идентификатор |
| order_id | UUID FK UNIQUE | Заказ (один отзыв на заказ) |
| user_id | UUID FK \| None | Пользователь (nullable для GDPR-удаления) |
| situation_id | str | ID ситуации (индекс) |
| rating | int | Оценка 1–5 |
| text | str | Текст отзыва (50–1000 символов) |
| name | str \| None | Имя автора |
| city | str \| None | Город |
| completed_orders_count | int | Кол-во заказов на момент отзыва |
| is_hidden | bool | Скрыт ли модератором |
| created_at | datetime | Время создания |

### Таблица `audit_log`
| Поле | Тип | Описание |
|---|---|---|
| id | int PK autoincrement | Идентификатор |
| user_id | str | ID пользователя |
| action | str | Действие (индекс) |
| data_type | str | Тип данных |
| timestamp | datetime | Время (индекс) |
| ip_address | str \| None | IP-адрес |
| details | JSON | Доп. данные |

---

## 5. Флоу пользователя E2E

```
1. LANDING (law-docs.ru)
   └─ Пользователь выбирает ситуацию (retail / banking / employment / ...)

2. WIZARD (/wizard/[situation])
   ├─ Мастер-форма из YAML-конфига ситуации (2-4 шага)
   ├─ Последний шаг — контактные данные (email, телефон, ФИО)
   └─ POST /api/v1/orders/init
         ├─ Если авторизован → заказ создан, статус: pending_payment
         └─ Если не авторизован → создаётся пользователь, отправляется magic link

3. MAGIC LINK (email)
   ├─ GET /api/v1/auth/verify?token=...&order=...
   ├─ Устанавливается httpOnly cookie с JWT
   └─ Редирект на страницу заказа

4. E2EE SETUP (опционально, /setup-e2ee)
   ├─ Браузер генерирует NaCl keypair (TweetNaCl)
   ├─ Приватный ключ → localStorage
   ├─ Пользователь создаёт пароль → AES-GCM бэкап приватного ключа
   └─ POST /api/v1/auth/setup-e2ee → публичный ключ + зашифрованный бэкап → сервер

5. ОПЛАТА (/orders/[id])
   ├─ POST /api/v1/orders/{id}/pay
   ├─ Создаётся платёж в ЮKassa
   └─ Редирект на форму оплаты ЮKassa

6. WEBHOOK (background)
   ├─ POST /api/v1/webhooks/yookassa (от ЮKassa, IP-валидация)
   ├─ Статус заказа: paid → generating
   └─ asyncio.create_task(run_document_generation())

7. ГЕНЕРАЦИЯ ДОКУМЕНТА (backend, async)
   ├─ Fetch order + form_data (расшифровывается Fernet)
   ├─ Применяются калькуляторы (неустойка, проценты, ключевая ставка)
   ├─ LLM (GigaChat → Claude fallback) заполняет шаблон
   ├─ python-docx → .docx
   ├─ WeasyPrint → .pdf
   ├─ Опционально: PDF с инструкцией
   ├─ E2EE: если есть public_key → файлы шифруются NaCl+AES-GCM
   └─ Загрузка в Яндекс S3

8. УВЕДОМЛЕНИЕ
   └─ Email пользователю (document ready / failed)

9. СКАЧИВАНИЕ (/orders/[id])
   ├─ GET /api/v1/documents/{id}/download-info/{fmt}
   │    └─ Presigned URL + флаг is_encrypted
   ├─ Если is_encrypted=true:
   │    ├─ Браузер скачивает зашифрованные байты
   │    ├─ Извлекает NaCl box (104 байта заголовка)
   │    ├─ Расшифровывает приватным ключом из localStorage
   │    └─ Отдаёт пользователю plaintext файл
   └─ Если is_encrypted=false:
        └─ Прямой редирект на presigned URL
```

---

## 6. Ключевые модули и их ответственность

| Модуль | Файл | Ответственность |
|---|---|---|
| Config | `backend/app/core/config.py` | Все переменные окружения через Pydantic Settings |
| Auth | `backend/app/api/v1/auth.py` + `auth_service.py` | Magic link, JWT, E2EE setup, recovery |
| Orders | `backend/app/api/v1/orders.py` | Создание, оплата, retry |
| Documents | `backend/app/api/v1/documents.py` | Presigned URLs, флаг шифрования |
| Webhook | `backend/app/api/v1/webhooks.py` | ЮKassa callback → запуск генерации |
| Generation | `backend/app/services/generation.py` | Полный pipeline генерации документа |
| LLM | `backend/app/services/llm.py` | GigaChat + Claude fallback |
| Docgen | `backend/app/services/docgen.py` | python-docx + WeasyPrint |
| Payment | `backend/app/services/payment.py` | ЮKassa API (создание, возврат) |
| E2EE Server | `backend/app/services/e2ee_service.py` + `e2ee_file.py` | Серверная часть шифрования файлов |
| E2EE Client | `frontend/lib/e2ee-client.ts` | TweetNaCl + AES-GCM в браузере |
| Storage | `backend/app/services/storage.py` | Яндекс S3 presigned URLs |
| Situations | `backend/app/situations/registry.py` | Загрузка и кэш YAML-конфигов |
| Calculators | `backend/app/services/calculators.py` | Неустойки, проценты, МРОТ, ставка ЦБ |
| Audit | `backend/app/services/audit_logger.py` | Compliance logging (152-ФЗ) |
| Background tasks | `backend/app/main.py` | Cleanup, auto-retry, law monitor, retention |
| Wizard | `frontend/components/wizard/` | Мультишаговая форма (из YAML-конфига) |
| Dashboard | `frontend/components/dashboard/DashboardPoller` | Polling статуса заказа |

---

## 7. API эндпоинты

### Auth (`/api/v1/auth/`)
| Метод | Путь | Auth | Rate | Описание |
|---|---|---|---|---|
| GET | `/auth/me` | JWT | — | Текущий пользователь |
| GET | `/auth/me/contact` | JWT | — | Контакт из последнего заказа |
| POST | `/auth/magic-link` | — | 5/min | Отправить magic link |
| GET | `/auth/verify` | — | 20/min | Верифицировать токен → JWT cookie |
| POST | `/auth/setup-e2ee` | JWT | — | Сохранить публичный ключ + бэкап |
| POST | `/auth/recover-access` | — | 5/min | Recovery: вернуть зашифрованный бэкап |

### Orders (`/api/v1/orders/`)
| Метод | Путь | Auth | Rate | Описание |
|---|---|---|---|---|
| GET | `/orders` | JWT | — | Список заказов (max 50) |
| POST | `/orders/init` | опц. | 10/min | Создать заказ из wizard |
| GET | `/orders/{id}` | JWT | 30/min | Статус заказа |
| POST | `/orders/{id}/pay` | JWT | — | Создать платёж ЮKassa |
| POST | `/orders/{id}/retry` | JWT | 3/min | Повторить генерацию |

### Documents (`/api/v1/documents/`)
| Метод | Путь | Auth | Описание |
|---|---|---|---|
| GET | `/documents/{id}/download/instruction` | JWT | Presigned URL инструкции |
| GET | `/documents/{id}/download/{fmt}` | JWT | Presigned URL (docx/pdf) |
| GET | `/documents/{id}/download-info/{fmt}` | JWT | URL + флаг is_encrypted |

### Webhooks
| Метод | Путь | Rate | Описание |
|---|---|---|---|
| POST | `/webhooks/yookassa` | 60/min | ЮKassa callback (IP-валидация) |

### Situations
| Метод | Путь | Описание |
|---|---|---|
| GET | `/situations` | Список всех ситуаций |
| GET | `/situations/{id}` | Детали ситуации |

### Reviews
| Метод | Путь | Auth | Rate | Описание |
|---|---|---|---|---|
| POST | `/reviews/admin/token` | x-admin-secret | 5/min | Получить admin token |
| POST | `/reviews` | JWT | 2/min | Оставить отзыв |
| GET | `/reviews/my` | JWT | — | Мой отзыв для заказа |
| GET | `/reviews` | — | — | Публичные отзывы (пагинация) |
| GET | `/reviews/admin` | admin token | — | Все отзывы (модерация) |
| PATCH | `/reviews/{id}/visibility` | admin token | — | Скрыть/показать отзыв |

### Users
| Метод | Путь | Auth | Описание |
|---|---|---|---|
| GET | `/users/me` | JWT | Профиль |
| PATCH | `/users/me` | JWT | Обновить имя |
| GET | `/users/me/data-export` | JWT | GDPR: экспорт данных |
| POST | `/users/me/restrict-processing` | JWT | GDPR: ограничить обработку |
| DELETE | `/users/me/restrict-processing` | JWT | GDPR: снять ограничение |
| DELETE | `/users/me` | JWT | GDPR: удалить аккаунт |

### System
| Метод | Путь | Описание |
|---|---|---|
| GET | `/stats/documents-count` | Публичный счётчик документов |
| GET | `/health` | Health check (DB + situations count) |

---

## 8. Безопасность

### Аутентификация
- **Magic Link**: 15-минутные токены, хранятся как SHA256-хэш, одноразовые
- **JWT**: 60-минутные access tokens, httpOnly cookie (защита от XSS)
- **Sliding session**: токен обновляется при < 30 мин до истечения

### Шифрование данных
| Уровень | Механизм | Что защищает |
|---|---|---|
| Transport | HTTPS / TLS (Let's Encrypt) | Весь трафик |
| At rest (form_data) | Fernet AES-128-CBC + HMAC | Ответы пользователя в БД |
| E2EE (файлы) | NaCl box + AES-GCM-256 | Готовые документы в S3 |
| Backup private key | PBKDF2 (200k) + AES-GCM | Бэкап приватного ключа на сервере |
| Email (zero-knowledge) | SHA256 | Поиск пользователя без plaintext email |

### Zero-Knowledge E2EE
- Сервер хранит только публичный ключ и зашифрованный бэкап
- Приватный ключ — только в `localStorage` браузера
- Файлы расшифровываются исключительно в браузере
- Пароль от бэкапа никогда не покидает клиент

### Rate Limiting (slowapi)
- `/auth/magic-link`: 5 req/min
- `/auth/verify`: 20 req/min
- `/auth/recover-access`: 5 req/min
- `/orders/init`: 10 req/min
- `/orders/{id}`: 30 req/min
- `/orders/{id}/retry`: 3 req/min
- `/webhooks/yookassa`: 60 req/min
- Nginx дополнительно: `/api/auth/` — 5 req/min, burst 3

### Webhook безопасность
- Валидация IP-адресов ЮKassa (whitelist CIDRs)
- Верификация платежа через ЮKassa API (не только по webhook-телу)
- Nginx: `X-Real-IP` пробрасывается для корректной проверки

### Соответствие законодательству
- **152-ФЗ**: form_data зашифрован, PII автоматически анонимизируется через 30 дней
- **GDPR**: право на удаление, право на ограничение обработки, экспорт данных
- **Retention**: автоудаление данных старше 3 лет

---

## 9. Инфраструктура

### Docker Compose (Development)
```
postgres:16-alpine   → port 5432
backend (FastAPI)    → port 8000
frontend (Next.js)   → port 3001→3000
pgadmin              → port 5050 (профиль dev)
```

### Docker Compose (Production)
```
postgres:16-alpine   → internal only
backend              → internal, 2 workers
frontend             → internal
backup               → cron 02:00 UTC, pg_dump → /backups/
nginx                → port 80, 443 (SSL termination)
```

### Nginx
- SSL: Let's Encrypt (law-docs.ru)
- Upstream: `frontend:3000`, `backend:8000`
- `/api/auth/` → frontend (rate-limited, 5/min, burst 3)
- `/api/v1/webhooks/` → backend (real IP forwarding для ЮKassa)
- `/ym-ru/`, `/ym-com/` → Яндекс Метрика proxy
- `/health` → backend (без логирования)
- `/` → frontend

### Резервные копии
- `scripts/backup.sh`: `pg_dump` ежедневно в 02:00 UTC
- Хранение в volume `lawdocs_backups`

### Фоновые задачи (backend/app/main.py)
| Задача | Период | Описание |
|---|---|---|
| `_cleanup_draft_orders` | каждый час | Удаляет драфты >24ч, анонимизирует PII >30д |
| `_auto_retry_loop` | каждые 15 мин | Повторяет генерацию для failed paid заказов (max 5) |
| `_law_monitor_loop` | 1-е число месяца, 09:00 UTC | Проверяет изменения в законодательстве |
| `_data_retention_loop` | ежедневно, 03:00 UTC | Удаляет данные старше 3 лет |

---

## 10. Известные особенности и архитектурные решения

### E2EE остаётся, несмотря на сложность
**Решение**: файлы документов шифруются публичным ключом пользователя; сервер не может их прочитать.  
**Почему**: требование 152-ФЗ и доверие пользователей — юридические документы содержат ПДн. Компромисс сложности реализации оправдан конкурентным преимуществом.

### GigaChat как основной LLM, Claude как fallback
**Решение**: GigaChat (Сбер) — основной, Claude 3.5 Sonnet — fallback при ошибке.  
**Почему**: GigaChat работает в российской юрисдикции (отсутствие рисков блокировки), лучше понимает русский правовой контекст. Claude используется как страховка надёжности.

### Magic Link вместо пароля
**Решение**: аутентификация только через email-ссылки, без паролей.  
**Почему**: целевая аудитория — обычные пользователи, не технари. Пароли создают трение и риск утечек. Magic link упрощает onboarding.

### YAML-конфиги ситуаций
**Решение**: каждая правовая ситуация описана в YAML (wizard, system_prompt, legal_refs, calculators).  
**Почему**: позволяет добавлять новые ситуации без изменения кода; product owner может редактировать YAML без программиста.

### form_data как EncryptedJSON (Fernet)
**Решение**: ответы wizard хранятся в одном зашифрованном JSON-поле, не в отдельных колонках.  
**Почему**: форма каждой ситуации уникальна; нормализация в таблицы потребовала бы схемы на каждую ситуацию. Fernet-шифрование удовлетворяет 152-ФЗ без усложнения схемы.

### Auto-retry и watchdog для генерации
**Решение**: при сбое генерации — автоматический retry каждые 15 мин, max 5 раз; при зависании >30 мин — автовозврат денег.  
**Почему**: LLM-запросы нестабильны (rate limits, timeouts). Пользователь не должен следить за статусом вручную.

### Яндекс Object Storage (S3-совместимый)
**Решение**: хранение документов в Яндекс Cloud, не на диске сервера.  
**Почему**: российская юрисдикция (152-ФЗ требует хранения ПДн в РФ), масштабируемость, presigned URLs для безопасной отдачи файлов без проксирования через backend.

### Sliding JWT session
**Решение**: JWT обновляется автоматически при менее чем 30 минутах до истечения.  
**Почему**: 60-минутные токены — компромисс между безопасностью и UX. Пользователь, активно работающий в сессии, не должен неожиданно разлогиниться.

### Presigned URLs вместо проксирования файлов
**Решение**: backend выдаёт presigned URL, браузер скачивает файл напрямую из S3.  
**Почему**: backend не становится узким местом при скачивании больших файлов; S3 обслуживает bandwidth самостоятельно.

---

## Changelog

- 2026-05-29 — Файл создан Claude Code. Проверены: структура директорий, все модели БД (13 миграций), все API-эндпоинты (34), E2EE-архитектура (клиент + сервер), docker-compose.yml + prod, nginx.conf, YAML-конфиги ситуаций, requirements.txt, package.json, фоновые задачи, механизмы безопасности.
