# GitHub Issues to Create (from handoff_46/review.md)

Все формулировки и ссылки на строки — точные копии из review.md.

---

## 🔴 CRITICAL (уже исправлено ✅)

### ✅ Issue 1 (FIXED): Timing attack на ADMIN_SECRET
**Файл:** `backend/app/api/v1/reviews.py:20-22`
**Статус:** ✅ Коммит de2a5eb

require_admin сравнивает секрет через != (не constant-time). Уязвимо к timing attack на длинный ADMIN_SECRET.

**Исправление:** Использовать `secrets.compare_digest()`.

---

### ✅ Issue 2 (FIXED): Double HTML-escape в БД
**Файл:** `backend/app/api/v1/reviews.py:32-38 + reviews.py:97-99`
**Статус:** ✅ Коммит de2a5eb

html.escape применяется к text/name/city на входе, и потом записывается в БД. React уже эскейпит на выходе → данные хранятся двойно-эскейпленными: `<Иван>` → в БД `&lt;Иван&gt;` → пользователь видит `&lt;Иван&gt;` буквально. Хуже: при автосейве `current_user.name = body.name` (line 99) уже эскейпленное имя летит в профиль.

**Решение:** Убрать html.escape из валидаторов, доверять frontend-эскейпингу (React/Next escapes by default). Если PDF-генератор не эскейпит — отдельная проблема к docgen.

---

### ✅ Issue 3 (FIXED): _render_sig_block игнорирует sig_lines
**Файл:** `backend/app/services/docgen.py:143-162`
**Статус:** ✅ Коммит 36b48f2

`_render_sig_block(pdf, sig_lines, ...)` не использует параметр sig_lines — выводит хардкод DATE_TEXT/SIG_TEXT. Если шаблон содержит "С уважением, Иванов И.И. 12.05.2026" — это теряется.

**Решение:** Удалить параметр и зафиксировать в API ("блок подписи всегда бланковый").

---

### ✅ Issue 4 (FIXED): Page break для блока подписи
**Файл:** `backend/app/services/docgen.py:151`
**Статус:** ✅ Коммит 36b48f2

`if pdf.get_y() + 20 > pdf.h - pdf.b_margin: pdf.add_page()`. По CLAUDE.md «блок подписи нельзя резать переносом страницы», но 20мм зарезервировано только под текущую двух-строчную реализацию. Если когда-то начнёт рендерить sig_lines многострочно (фио + дата + место), 20 мм мало → ничего не предохраняет.

**Решение:** Завязать на `len(sig_lines)*line_h + buffer`.

---

## 🟡 MAJOR (остальное)

### Issue 5 (P1): XSS — ADMIN_SECRET в sessionStorage
**Файл:** `frontend/app/admin/reviews/page.tsx:32-56`
**Severity:** CRITICAL
**Тип:** Security

ADMIN_SECRET хранится в sessionStorage и летит в X-Admin-Secret через клиент. Любой XSS на этом домене → утечка мастер-ключа модерации. Дополнительно — нет защиты от CSRF (см. Issue 6).

**Решение:** Ввод секрета → server action → backend выдаёт httpOnly admin-cookie с коротким TTL (например, 15 мин). Дальше клиент шлёт только cookie, секрет никогда не доступен JS. Минимальный фикс: отделить admin от обычных сессий через cookie-based admin token.

---

### Issue 6 (P1): CSRF-защита пропускает /api/admin/*
**Файл:** `frontend/middleware.ts:17-24`
**Severity:** HIGH
**Тип:** Security

CSRF-защита пропускает запросы без Origin-заголовка для всех мутирующих методов. Комментарий объясняет это для server actions, но /api/admin/* тоже подпадает: атакующий с XSS или фишинг-страницы (старый браузер не отправляет Origin на некоторые fetch) обходит проверку.

**Решение:** Для /api/admin/* требовать Origin строго.

---

### ✅ Issue 7 (FIXED): Пагинация в /reviews/admin
**Файл:** `backend/app/api/v1/reviews.py:146-154`
**Статус:** ✅ Коммит de2a5eb

list_all_reviews_admin без пагинации. При росте до ~10k отзывов админка ляжет.

**Решение:** Добавить `?limit=100&offset=...`. Также: возвращает user_id (PII-связь) — для админа норм, но в логах/трейсах фильтровать.

---

### Issue 8 (P2): UUID валидация в admin reviews API
**Файл:** `frontend/app/api/admin/reviews/[id]/route.ts:13-19`
**Severity:** MEDIUM
**Тип:** Validation

id из URL не валидируется. Прокинется любой мусор в backend. Backend (reviews.py:163) тоже не валидирует UUID-формат. Низкий риск, но лучше добавить `isValidUuid(id)` (есть в lib/validators.ts) и 400 на невалидный.

---

### ✅ Issue 9 (FIXED): Page validation (negative values)
**Файл:** `backend/app/api/v1/reviews.py:121-143`
**Статус:** ✅ Коммит de2a5eb

page не валидируется (negative → negative offset → IndexError или странный результат). limit клампится, page — нет.

**Решение:** `page = max(page, 1)`.

---

### ✅ Issue 10 (FIXED): Email нормализация (lowercase)
**Файл:** `backend/app/api/v1/orders.py:78-89`
**Статус:** ✅ Коммит cd7da9d

Нет нормализации email (lowercase) перед select. Если `body.email = "User@x.ru"` и в БД `user@x.ru`, попадаем в branch `not user`, на flush `IntegrityError`, потом re-select по тому же кейсу → опять `scalar_one()` без записи → 500.

**Решение:** Привести `body.email` к `.lower()` единообразно (и в auth.py:76, auth.py:81).

---

### Issue 11 (P2): update_me не логирует и не валидирует
**Файл:** `backend/app/api/v1/users.py:39-48`
**Severity:** MEDIUM
**Тип:** Validation

update_me не логирует изменение профиля и не валидирует, что `body.name` действительно прислан. Если запрос пустой `{}`, name перезатрётся в None (так как `default=None`). Сейчас семантика: PATCH = SET, не MERGE. Не критично, но в коде `set_attrs_from_dict(exclude_unset=True)` сильно сократил бы сюрпризы для расширения формы.

---

### Issue 12 (P2): Race condition в toggle_review_visibility
**Файл:** `backend/app/api/v1/reviews.py:166-169`
**Severity:** MEDIUM
**Тип:** Concurrency

toggle_review_visibility: при двух одновременных кликах модератора возможна гонка (read-modify-write без with_for_update). Низкая вероятность для одного админа, но если их станет двое — лучше `.with_for_update()`.

---

### Issue 13 (P2): Дублирование валидатора strip_and_escape
**Файл:** `backend/app/api/v1/reviews.py:32` и `backend/app/api/v1/users.py:25`
**Severity:** LOW
**Тип:** Refactoring

Идентичный field_validator в 2 файлах (теперь strip_whitespace после html.escape removal).

**Решение:** Вынести в `app/core/validators.py` (одна функция). Импортировать в обе схемы.

---

### ✅ Issue 14 (FIXED): ADMIN_SECRET validator в production
**Файл:** `backend/app/core/config.py:66`
**Статус:** ✅ Коммит a5440e9

`ADMIN_SECRET: str = ""` с дефолтом. Если в проде забыли выставить env, require_admin корректно отвечает 403 (if not settings.ADMIN_SECRET), но шансов словить тихий misconfig в проде много.

**Решение:** Сделать field_validator: если `APP_ENV == "production"` и `ADMIN_SECRET == ""` → ValueError на старте.

---

## 🟢 MINOR (низкий приоритет)

### Issue 15 (P3): Мёртвый код — verify_magic_token
**Файл:** `backend/app/core/security.py:52-53`
**Severity:** LOW
**Тип:** Code cleanup

verify_magic_token — мёртвый код (везде используется прямое равенство хэшей).

**Решение:** Удалить функцию.

---

### Issue 16 (P3): Side effect в loadReviews
**Файл:** `frontend/app/admin/reviews/page.tsx:39-57`
**Severity:** LOW
**Тип:** Refactoring

loadReviews(s) сама ходит в `sessionStorage.setItem`. Side-effect внутри функции загрузки — мешает повторному использованию.

**Решение:** Вынести `setItem` в `handleLogin`. Ккпт loadReviews чистой (только load + return data).

---

### Issue 17 (P3): Доступность — aria-label на кнопке toggle
**Файл:** `frontend/app/admin/reviews/page.tsx:147`
**Severity:** LOW
**Тип:** Accessibility

Кнопка toggle без aria-label/aria-pressed.

**Решение:**
- Добавить `aria-label="Toggle review visibility"`
- Добавить `aria-pressed={!review.is_hidden}`

---

### Issue 18 (P3): Магические числа в docgen.py
**Файл:** `backend/app/services/docgen.py:139`
**Severity:** LOW
**Тип:** Refactoring

Магические 105.0 (RIGHT_COL_X) и 85.0 (RIGHT_COL_W) для правой колонки. Повторяются в `_render_sig_block`.

**Решение:** Завернуть в константы:
```python
RIGHT_COL_X = 105.0
RIGHT_COL_W = 85.0
```

---

### Issue 19 (P3): list(...) лишний
**Файл:** `backend/app/api/v1/reviews.py:154`
**Severity:** LOW
**Тип:** Code cleanup

`list(result.scalars().all())` — `.all()` уже даёт Sequence. `list(...)` лишний, но безвреден.

---

### Issue 20 (P3): Неэффективный lookup в create_review
**Файл:** `backend/app/api/v1/reviews.py:66-103`
**Severity:** LOW
**Тип:** Performance

create_review после успеха возвращает 201 + сериализацию через ReviewOut. Но `existing.scalar_one_or_none()` (line 82) делает второй query вместо IntegrityError на unique constraint order_id. На больших нагрузках лучше insert + catch IntegrityError, но при текущих RPS — норм.

---

---

## 📊 Summary

| Статус | Количество | Коммиты |
|--------|-----------|---------|
| ✅ Fixed (Critical/Major блокеры) | 7 | de2a5eb, 36b48f2, a5440e9, cd7da9d |
| 🟡 P1/P2 Issues (требуют создания) | 6 | #5, #6, #8, #11, #12, #13 |
| 🟢 P3 Issues (nice-to-have) | 7 | #15-#20 |

---

## ✅ Что готово к мержу

Все 4 коммита содержат исправления 7 блокирующих issues из review.md:
1. ✅ Timing attack (constant-time)
2. ✅ Double HTML-escape
3. ✅ sig_lines parameter
4. ✅ Page break calculation  
5. ✅ Pagination /reviews/admin
6. ✅ Email normalization
7. ✅ ADMIN_SECRET production validator
8. ✅ Page validation (negative offset fix)
