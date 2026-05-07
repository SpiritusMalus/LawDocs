# Заглушки (Stubs)

Все заглушки, которые нужно заменить перед production-запуском.

## 1. ЮKassa — `backend/app/services/payment.py`

| Условие активации | `settings.YOOKASSA_SHOP_ID` пуст |
|---|---|
| Поведение | Возвращает `payment_id = "dev_{order_id}"` и `confirmation_url = http://localhost:3000/dev/payment?order_id=...` |
| Что заменить | Зарегистрировать магазин на ЮKassa, добавить `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` в `.env` |

## 2. Email (magic link + уведомление) — `backend/app/services/email.py`

| Условие активации | `settings.SMTP_HOST` пуст |
|---|---|
| Поведение | Пишет `[EMAIL stub] To: ... Subject: ...` в лог, письмо не отправляется |
| Что заменить | Завести почту (Яндекс 360 или любой SMTP), добавить `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` в `.env` |

## 3. Хранилище документов — `backend/app/services/docgen.py`

| Условие | Всегда включено (не заглушка) |
|---|---|
| Поведение | Файлы сохраняются на диск в `DOCUMENTS_DIR/{order_id}/` (Docker volume `lawdocs_documents`) |
| Масштабирование | При росте — подключить NFS-том или S3-совместимое хранилище как замену DOCUMENTS_DIR |

## 4. Dev-платёж — `frontend/app/dev/payment/`

| Условие активации | `process.env.NODE_ENV !== "production"` |
|---|---|
| Поведение | Страница симулирует оплату, отправляя POST `/api/v1/webhooks/yookassa` с `payment_id = dev_{order_id}` |
| Что заменить | Страница автоматически недоступна в production (`notFound()` при `NODE_ENV=production`) |

## Чеклист перед production

- [ ] Зарегистрировать ИП и подключить ЮKassa
- [ ] Настроить SMTP (Яндекс 360: smtp.yandex.ru:465)
- [ ] Сгенерировать `SECRET_KEY` через `openssl rand -hex 32`
- [ ] Поменять `APP_ENV=production` в `.env`
- [ ] Настроить ЮKassa webhook URL: `https://lawdocs.ru/api/v1/webhooks/yookassa`
- [ ] Убедиться, что Docker volume `lawdocs_documents` подключён к правильному хосту / бэкапится
