# Disaster Recovery — LawDocs

Цель: пережить потерю данных (Postgres и/или S3) и не накопить осиротевших блобов.
Закрывает system-design §6 «DR: backup/restore + S3 lifecycle, согласованный с
data-retention».

Зоны ответственности: код/скрипты — Claude; запуск на проде, доступ к секретам,
расписание cron — User.

---

## 1. Что и где хранится
- **Postgres** — источник правды: заказы, пользователи, документы (метаданные + S3-ключи),
  отзывы, аудит, ключи E2EE, журнал платёжных событий. PII зашифрованы (Fernet).
- **Yandex Object Storage (S3)** — только бинарники: `docx_key`, `pdf_key`,
  `instruction_pdf_key`, `preview_keys[]`. Байты документов в БД не лежат.

Потеря Postgres = потеря ключей к S3 (блобы станут недоступны). Поэтому **бэкап БД
первичен**.

---

## 2. Бэкап Postgres
Скрипт: `backend/scripts/backup_db.sh` (pg_dump, custom format, ротация).

```bash
DATABASE_URL=postgresql://USER:PASS@HOST:5432/lawdocs \
  ./scripts/backup_db.sh /var/backups/lawdocs
```
- Хранит последние `BACKUP_KEEP` (по умолчанию 14) дампов.
- **Рекомендация:** cron ежедневно + выгрузка дампов в S3/другой регион (off-host),
  иначе потеря хоста = потеря бэкапов. Дамп содержит зашифрованные PII —
  Fernet-ключ (`FERNET_KEY`) хранить **отдельно** от дампов (иначе бэкап = открытые ПДн).

### Восстановление
Скрипт: `backend/scripts/restore_db.sh` (⚠️ деструктивный, `--clean`).
```bash
DATABASE_URL=postgresql://USER:PASS@HOST:5432/lawdocs \
  ./scripts/restore_db.sh /var/backups/lawdocs/lawdocs-YYYYmmdd-HHMMSS.dump
```
После восстановления: `alembic current` должен показывать тот же head, что и код.
Для расшифровки PII нужен исходный `FERNET_KEY`.

---

## 3. S3 lifecycle ↔ data-retention (чтобы не расходились)
**Активное удаление:** `_data_retention_loop` (в `app/main.py`, ежедневно 03:00 UTC)
удаляет заказы/документы старше **1095 дней (3 года)** и **сначала удаляет блобы из
S3** по ключам из `Document`, потом строки БД (иначе ключи теряются → вечные сироты).

**Backstop:** `backend/scripts/s3_lifecycle.py` ставит правило expiration на **1100
дней** (3 года + буфер). Loop удаляет первым; lifecycle подчищает то, что loop
пропустил (сбои удаления, объекты от иных путей), плюс обрывает зависшие multipart.

```bash
python -m scripts.s3_lifecycle          # применить (идемпотентно)
python -m scripts.s3_lifecycle --show   # показать текущее правило
```
Применить один раз после настройки бакета и при изменении окна retention.

> Инвариант согласованности: окно lifecycle (1100) ≥ окна retention в коде (1095).
> Если меняете `timedelta(days=3*365)` в `_data_retention_loop` — поправьте
> `_EXPIRE_DAYS` в `s3_lifecycle.py`, сохранив буфер.

---

## 4. Чек-лист восстановления (worst case)
1. Поднять Postgres, восстановить последний дамп (`restore_db.sh`).
2. Проверить `alembic current` == head; при отставании — `alembic upgrade head`.
3. Убедиться, что `FERNET_KEY`, S3- и YooKassa-секреты заданы в окружении.
4. Поднять backend; фоновые loop'ы (retry/reconcile/alerting) стартуют сами.
5. `_payment_reconcile_loop` сам подберёт оплаченные-но-незавершённые заказы и
   дотащит их до DONE (сверится с ЮKassa). Проверить алерты на stuck PAID.
6. S3: если бакет цел — ключи из восстановленной БД продолжат работать. Если бакет
   потерян — документы старых заказов недоступны; новые генерируются заново.
