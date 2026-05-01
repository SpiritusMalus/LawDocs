# PROJECT_STATUS

> Живой статус проекта LawDocs. Обновляй по мере значимых изменений.
> Дата последнего обновления: 2026-05-01.

## Где мы сейчас

**Фаза 1 — валидация спроса.** Цель ближайшего месяца: получить 20+ платящих юзеров
с CAC <500 ₽. Если получится — строим MVP. Если нет — закрываем эксперимент.

Готовый артефакт: лендинг `LawDocs/frontend/` (Next.js 16). Заявки идут в Telegram-бот,
обработка ручная: связались → выставили счёт через Тинькофф самозанятого → юрист
написал документ → отправили клиенту на email.

## Что сделано

### Фронтенд (LawDocs/frontend)

- Next.js 16.2 + React 19 + Tailwind v4 + base-ui/react + shadcn `base-nova`
- Лендинг из 7 секций: Hero, Situations (7 карточек), HowItWorks, WhyNotChatGPT,
  Pricing, FAQ (с base-ui Accordion), LeadForm (с server action)
- Footer с дисклеймером про ИИ и юрстатус
- Header sticky + мобильное меню (гамбургер)
- Страницы: `/`, `/thanks`, `/legal/offer`, `/legal/privacy`, `/_not-found`
- SEO-страницы: `/situations/[slug]` — 7 статических страниц под каждую ситуацию
  (shop, marketplace, bank, employer, insurance, utility, airline).
  Каждая: H1, lead-текст, список документов, законодательная база, FAQ, форма заявки.
  JSON-LD: BreadcrumbList + FAQPage. Карточки на главной теперь ведут на `/situations/*`.
- SEO: `robots.ts`, `sitemap.ts`, FAQ JSON-LD schema.org/FAQPage
- OG-image: `app/opengraph-image.tsx` (1200×630, генерится через ImageResponse)
- Фавикон `app/icon.svg`
- Yandex.Metrika — опционально через `NEXT_PUBLIC_YM_COUNTER_ID`
- Системный шрифт-стек (Google Fonts отключён — лишняя зависимость на фазе 1)

### Server Action (lib/actions/submit-lead.ts)

- Валидация: имя, контакт (email или телефон по regex), описание ≥20 символов,
  согласие на ПДн обязательно
- Whitelist для `situationId` (только из `SITUATIONS` или `other`)
- Rate limit: 5 заявок в час с одного IP (in-memory Map, prune по таймеру)
- Honeypot-поле `website` — silent success
- HTML-escape всех пользовательских значений перед отправкой в Telegram (parse_mode: HTML)
- IP клиента берётся из `x-forwarded-for` / `x-real-ip` через `headers()`
- Если `TELEGRAM_*` env-переменные не заданы — лог в stdout, форма не падает

### Security

Прошёл код-ревью, найденное закрыто:
- ✅ Rate limiting на `submitLead`
- ✅ Whitelist `situationId`
- ✅ JSON-LD: escape `<`, `>`, `&`, U+2028, U+2029 чтобы нельзя было вырваться из `<script>`
- ✅ Валидация `NEXT_PUBLIC_YM_COUNTER_ID` (только цифры, иначе скрипт не инжектится)
- ✅ Telegram-токен не попадает в логи / клиент / response
- ✅ CSRF — handled Next.js Server Actions автоматически (Origin check)
- ✅ Нет SSRF (URL fetch'а — фиксированный)

Защиту через CSP-заголовки оставил на потом, для фазы 1 не критично.

### Doc/Memory

- `CLAUDE.md` в корне — общий контекст проекта для будущих сессий Claude
- `frontend/AGENTS.md` — напоминание про Next 16 breaking changes
- `frontend/README.md` — quick start
- `frontend/.env.example` — переменные окружения
- `PROJECT_STATUS.md` (этот файл) — живой статус

## Что НЕ сделано (по плану)

Фаза 1 не должна включать:
- ❌ Бэкенд (FastAPI) — Phase 2 после валидации
- ❌ ЛК пользователя
- ❌ Wizard-форма пошаговая
- ❌ ЮKassa и онлайн-оплата
- ❌ БД, Redis, очереди
- ❌ Реальные шаблоны документов (`.docx` от юриста)
- ❌ LLM-интеграция (GigaChat / Claude)

## Открытые задачи (off-code, требуют участия)

| # | Задача | Кто | Срочность |
|---|--------|-----|-----------|
| 1 | Найти юриста-партнёра (15–25% доли, vesting 4 года) | человек | блокер |
| 2 | Зарегистрировать Тинькофф самозанятого, получить QR | человек | до запуска трафика |
| 3 | Купить домен `lawdocs.ru` (или альтернативу) | человек | до запуска |
| 4 | Создать Telegram-бот через @BotFather, настроить env | человек | до деплоя |
| 5 | Создать счётчик в Яндекс.Метрике | человек | до деплоя |
| 6 | Подать уведомление в Роскомнадзор как оператор ПДн | человек | до запуска платных |
| 7 | Финальная редакция оферты и политики ПДн от юриста | юрист | до запуска платных |
| 8 | Деплой на Vercel + Cloudflare (DNS, CDN) | человек | для запуска трафика |
| 9 | Настроить Яндекс.Директ кампанию (~30k ₽) | человек | для трафика |
| 10 | Telegram-посевы в каналах потребительской тематики (~20k ₽) | человек | для трафика |

## Ключевые файлы

```
LawDocs/
├── CLAUDE.md                       # контекст проекта (читается каждый раз)
├── PROJECT_STATUS.md               # этот файл
├── .gitignore                      # Python + Node
└── frontend/
    ├── README.md                   # инструкции локального запуска
    ├── AGENTS.md                   # напоминание про Next 16
    ├── .env.example
    ├── package.json
    ├── app/
    │   ├── layout.tsx              # корневой лейаут, метаданные, YM
    │   ├── page.tsx                # главная (все секции)
    │   ├── globals.css             # дизайн-токены + tailwind
    │   ├── icon.svg                # фавикон
    │   ├── opengraph-image.tsx     # OG для соц. шаринга
    │   ├── robots.ts
    │   ├── sitemap.ts
    │   ├── not-found.tsx
    │   ├── thanks/page.tsx
    │   └── legal/{offer,privacy}/page.tsx
    ├── components/
    │   ├── ui/                     # button, input, label, textarea
    │   ├── layout/header.tsx
    │   └── landing/                # 8 секций + faq-jsonld
    └── lib/
        ├── utils.ts
        ├── situations.ts           # справочник 7 ситуаций
        ├── faq.ts                  # справочник FAQ
        ├── rate-limit.ts           # in-memory rate limiter
        └── actions/submit-lead.ts  # server action для формы
```

## Метрики, на которые смотрим (после запуска трафика)

- CPC, CTR лендинга (Метрика → Директ)
- Конверсия лендинг → форма (Yandex.Metrika цель)
- Конверсия форма → платящий (ручной счёт по Telegram-заявкам)
- CAC = (бюджет на трафик) / (платящие) — должен быть <500 ₽
- Какие ситуации чаще выбирают (для расширения каталога шаблонов в фазе 2)
