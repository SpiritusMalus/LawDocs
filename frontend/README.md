# LawDocs — Frontend

Next.js 16 приложение: лендинг для валидации спроса (Phase 1) и в будущем — wizard-форма для генерации документов (Phase 2).

## Требования

- **Node.js** 18.17 или новее ([скачать](https://nodejs.org))
- **npm** 9+ (идёт вместе с Node.js)

Проверить версии:

```bash
node -v
npm -v
```

---

## Локальный запуск

```bash
# 1. Перейти в папку фронтенда
cd frontend

# 2. Установить зависимости
npm install

# 3. Создать файл с переменными окружения
cp .env.example .env.local

# 4. Запустить dev-сервер
npm run dev
```

Откроется на **<http://localhost:3000>**

> Без заполненных `TELEGRAM_*` форма работает — заявки пишутся в консоль. Для полноценной работы заполни переменные ниже.

---

## Переменные окружения

Все секреты хранятся в `.env.local` — этот файл **не попадает в git**.

| Переменная | Обязательная | Описание |
| --- | :---: | --- |
| `TELEGRAM_BOT_TOKEN` | — | Токен бота от @BotFather. Без него заявки пишутся в stdout |
| `TELEGRAM_CHAT_ID` | — | ID чата куда бот шлёт уведомления. Получить: написать боту `/start`, открыть `https://api.telegram.org/bot<TOKEN>/getUpdates`, взять `result[0].message.chat.id` |
| `NEXT_PUBLIC_SITE_URL` | — | Полный URL сайта (например `https://lawdocs.ru`). Используется в sitemap и OG-тегах. По умолчанию `https://lawdocs.ru` |
| `NEXT_PUBLIC_YM_COUNTER_ID` | — | Числовой ID счётчика Яндекс.Метрики. Если пусто — Метрика не подключается |

---

## Сборка для продакшена

```bash
npm run build   # собрать
npm run start   # запустить собранную версию
```

---

## Структура проекта

```text
frontend/
├── app/
│   ├── layout.tsx                  # корневой лейаут + Яндекс.Метрика
│   ├── page.tsx                    # главная страница (лендинг)
│   ├── globals.css                 # дизайн-токены + Tailwind v4
│   ├── opengraph-image.tsx         # OG-картинка главной
│   ├── robots.ts                   # robots.txt
│   ├── sitemap.ts                  # sitemap.xml
│   ├── thanks/page.tsx             # страница «спасибо» после заявки
│   ├── situations/
│   │   ├── page.tsx                # хаб /situations — все ситуации
│   │   └── [slug]/
│   │       ├── page.tsx            # SEO-страница под каждую ситуацию
│   │       └── opengraph-image.tsx # OG-картинка для каждой ситуации
│   └── legal/
│       ├── offer/page.tsx          # договор-оферта (черновик)
│       └── privacy/page.tsx        # политика ПДн (черновик)
├── components/
│   ├── ui/                         # button, input, label, textarea
│   ├── layout/header.tsx           # шапка с мобильным меню
│   ├── analytics/ym-goal.tsx       # клиентский компонент для reachGoal
│   └── landing/                    # секции лендинга и форм
│       ├── hero.tsx
│       ├── situations.tsx
│       ├── how-it-works.tsx
│       ├── why-not-chatgpt.tsx
│       ├── pricing.tsx
│       ├── faq.tsx
│       ├── faq-jsonld.tsx
│       ├── lead-form.tsx           # форма заявки (главная)
│       ├── situation-lead-form.tsx # форма заявки (страницы ситуаций)
│       └── footer.tsx
└── lib/
    ├── utils.ts                    # cn()
    ├── situations.ts               # справочник 7 ситуаций
    ├── situation-pages.ts          # SEO-данные для страниц ситуаций
    ├── faq.ts                      # вопросы FAQ
    ├── rate-limit.ts               # in-memory rate limiter
    └── actions/submit-lead.ts      # Server Action: валидация + Telegram
```

---

## Как устроен проект (Phase 1)

Заявки обрабатываются **вручную**:

```text
Пользователь заполняет форму
        ↓
Server Action валидирует данные
        ↓
Telegram-бот присылает уведомление
        ↓
Связываемся с клиентом вручную
        ↓
Выставляем счёт через Тинькофф (QR)
        ↓
Юрист пишет документ → отправляем на email
```

**Цель Phase 1:** 20+ платящих с CAC < 500 ₽ за месяц.
Если получается → строим Phase 2 (wizard + ЮKassa + GigaChat + FastAPI).
Если нет → закрываем эксперимент с минимальными потерями.
