# Деплой на Timeweb VPS

## Требования к серверу

- Ubuntu 22.04 LTS
- 2 vCPU, 2 GB RAM (минимум)
- Порты 80, 443 открыты
- Docker + Docker Compose установлены

## 1. Установка Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Переподключиться к серверу
docker --version
```

## 2. Клонирование репозитория

```bash
git clone https://github.com/SpiritusMalus/LawDocs.git /var/www/lawdocs
cd /var/www/lawdocs
```

## 3. Настройка переменных окружения

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Обязательно заполнить:
- `SECRET_KEY` — `openssl rand -hex 32`
- `DATABASE_URL` — `postgresql+asyncpg://lawdocs:STRONG_PASS@postgres:5432/lawdocs`
- `POSTGRES_PASSWORD` в `docker-compose.yml` (должен совпадать)
- `FRONTEND_URL=https://lawdocs.ru`
- `APP_ENV=production`
- `DOCUMENTS_DIR=/var/lawdocs/documents` (создаётся автоматически Docker volume)
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` — после настройки почты
- `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` — после регистрации в ЮKassa

```bash
cp frontend/.env.example frontend/.env.local
nano frontend/.env.local
```

Заполнить:
- `NEXT_PUBLIC_SITE_URL=https://lawdocs.ru`
- `NEXT_PUBLIC_YM_COUNTER_ID=` (после регистрации в Яндекс.Метрике)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (для Phase 1 fallback)

## 4. Установка Nginx

```bash
sudo apt install -y nginx
sudo cp /var/www/lawdocs/nginx.conf /etc/nginx/sites-available/lawdocs
sudo ln -s /etc/nginx/sites-available/lawdocs /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 5. SSL через Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d lawdocs.ru -d www.lawdocs.ru
# Автообновление уже настроено через systemd timer
```

## 6. Запуск контейнеров

```bash
cd /var/www/lawdocs
docker compose up -d --build
docker compose logs -f  # убедиться что всё запустилось
```

Проверить:
```bash
curl http://localhost:3000        # фронт
curl http://localhost:8000/health # бэкенд
```

## 7. Настройка ЮKassa webhook

В личном кабинете ЮKassa → Настройки → HTTP-уведомления:
```
URL: https://lawdocs.ru/api/v1/webhooks/yookassa
Событие: payment.succeeded
```

## pgAdmin (для дебага, только в dev)

```bash
docker compose --profile dev up -d pgadmin
# Открыть: http://localhost:5050
# Email: admin@lawdocs.local / пароль: pgadmin_dev_pass
# Добавить сервер: host=postgres, user=lawdocs, db=lawdocs
```

Не запускать pgAdmin в production — он открывает прямой доступ к БД.

## Обновление (CI/CD вручную)

```bash
cd /var/www/lawdocs
git pull origin main
docker compose up -d --build
```

## Мониторинг

```bash
docker compose ps             # статус сервисов
docker compose logs backend   # логи бэкенда
docker compose logs frontend  # логи фронта
docker compose logs postgres  # логи БД
```

## Бэкап базы данных

```bash
docker compose exec postgres pg_dump -U lawdocs lawdocs > backup_$(date +%Y%m%d).sql
```

## Бэкап документов (файлы пользователей)

```bash
# Скопировать volume на хост
docker run --rm \
  -v lawdocs_documents:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/documents_$(date +%Y%m%d).tar.gz -C /data .
```

Настройте cron для автоматического бэкапа:
```bash
0 3 * * * cd /var/www/lawdocs && docker run --rm -v lawdocs_documents:/data -v $(pwd)/backups:/backup alpine tar czf /backup/docs_$(date +\%Y\%m\%d).tar.gz -C /data . 2>/dev/null
```

## Ротация секретов

При компрометации `SECRET_KEY` все JWT инвалидируются — пользователям придётся заново перейти
по magic link. Для смены: обновить `backend/.env`, перезапустить `docker compose restart backend`.
