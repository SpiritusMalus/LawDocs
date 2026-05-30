# Добавление новой ситуации

Архитектура data-driven: основная работа — YAML конфиг + две записи на фронте.
Всё остальное (API, sitemap, роуты, визард) подключается автоматически.

---

## Чек-лист

### 1. Бэкенд — конфиг ситуации
**Файл:** `backend/app/situations/configs/{category}/{situation_id}.yaml`

- [ ] Создать файл в нужной категории (папка = категория)
- [ ] Заполнить обязательные поля:
  - `id` — snake_case, уникальный (проверить `dc exec backend python -c "from app.situations.registry import registry; print(registry.ids())"`)
  - `category` — одна из существующих папок в `configs/`
  - `title`, `blurb`, `examples`
  - `document_type` — обычно `pretenziya`
  - `system_prompt` — инструкция для LLM (что писать, стиль, ограничения)
  - `wizard_steps` — минимум 2 шага; шаг с контактами добавится автоматически
  - `header_fields` — что идёт в шапку документа (адресат, отправитель, телефон)
  - `legal_refs` — ссылки на законы
- [ ] Проверить что реестр загружает файл без ошибок:
  ```bash
  dc exec backend python -c "from app.situations.registry import registry; print(registry.get('{situation_id}').title)"
  ```

### 2. Бэкенд — калькулятор (только если нужны расчёты)
**Файл:** `backend/app/services/calculators.py`

- [ ] Добавить функцию `calculate_{situation_id}(form_data: dict) -> dict`
  - Функция добавляет `calculated_*` ключи в `form_data`
  - Пример: `calculated_penalty_amount`, `calculated_days_overdue`
- [ ] Добавить в словарь: `SITUATION_CALCULATORS["{situation_id}"] = calculate_{situation_id}`
- [ ] В конфиге использовать `[calculated_*]` плейсхолдеры в `python_template`

### 3. Фронтенд — список ситуаций
**Файл:** `frontend/lib/situations.ts`

- [ ] Добавить `"{situation_id}"` в Union type `SituationId`
- [ ] Добавить объект в массив `SITUATIONS[]`:
  ```typescript
  {
    id: "{situation_id}",
    title: "Название (совпадает с title из YAML)",
    blurb: "Краткое описание",
    examples: "Пример 1, пример 2",
    category: "purchases" | "money" | "housing" | "transport" | "services",
    // featured: true,  // добавить если нужно попасть в топ-3 на главной
  }
  ```

### 4. Фронтенд — SEO-страница
**Файл:** `frontend/lib/situation-pages.ts`

- [ ] Добавить объект в массив `SITUATION_PAGES[]`:
  ```typescript
  {
    slug: "{situation_id}",  // совпадает с id из YAML
    seoTitle: "Претензия... — образец 2025 | LawDocs",
    seoDescription: "155-160 символов для поисковиков",
    h1: "Заголовок страницы",
    leadIn: "Вводный абзац — контекст проблемы, почему это законно",
    legalBasis: [
      { article: "ЗоЗПП, ст. 18", description: "Права при..." },
      // минимум 2-3 статьи
    ],
    deliverables: [
      { title: "Претензия", desc: "Что именно получит пользователь" },
      { title: "Инструкция по подаче", desc: "Куда и как" },
    ],
    sendTo: "Куда направить документ (адрес, способ)",
    faq: [
      { q: "Вопрос?", a: "Ответ (2-3 предложения)" },
      // минимум 4 вопроса
    ],
    // sampleFile: "/samples/obrazec_{situation_id}.pdf",  // если есть образец
  }
  ```
- [ ] Убедиться что `slug` совпадает с `id` из YAML

### 5. Тесты
**Файл:** `backend/tests/test_registry.py`

- [ ] Добавить `"{situation_id}"` в `EXPECTED_IDS`
- [ ] Обновить счётчик: `assert len(registry) == N+1`

**Файл:** `backend/tests/test_situations_api.py`

- [ ] Добавить `"{situation_id}"` в `@pytest.mark.parametrize` у `test_detail_has_contact_step`
- [ ] Обновить счётчики в `test_list_situations_returns_all()` и `test_health_includes_situations_count()`

- [ ] Прогнать тесты:
  ```bash
  dc exec backend pytest tests/test_registry.py tests/test_situations_api.py -v
  ```

### 6. Образец PDF (опционально)
- [ ] Сгенерировать тестовый документ через визард
- [ ] Положить в `frontend/public/samples/obrazec_{situation_id}.pdf`
- [ ] Прописать `sampleFile` в `situation-pages.ts`

---

## Что НЕ нужно менять

| Файл | Причина |
|---|---|
| `backend/app/situations/registry.py` | Автозагрузка через `rglob("*.yaml")` |
| `backend/app/api/v1/situations.py` | API работает с любым ID из реестра |
| `frontend/app/situations/page.tsx` | Грид берёт из `SITUATIONS[]` |
| `frontend/app/wizard/[situation]/page.tsx` | Читает шаги с бэка динамически |
| `frontend/app/sitemap.ts` | Генерируется из `SITUATION_PAGES[]` |
| `frontend/app/situations/[slug]/page.tsx` | `generateStaticParams` берёт из `SITUATION_PAGES[]` |

---

## Порядок

1. YAML конфиг → проверить загрузку реестра
2. Калькулятор (если нужен)
3. `situations.ts` + `situation-pages.ts`
4. Тесты → `pytest`
5. Образец PDF (если есть)
6. Коммит на feature-ветке, пуш — деплой делает User
