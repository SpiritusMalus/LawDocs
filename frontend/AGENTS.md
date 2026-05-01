<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

Версия: Next.js 16.2 + React 19. API, конвенции и структура файлов могут отличаться
от данных тренировки. Перед написанием кода читай актуальные доки в
`node_modules/next/dist/docs/`. Особое внимание:

- Server Functions / Server Actions (`app/01-getting-started/07-mutating-data.md`)
- Route Handlers (`app/01-getting-started/15-route-handlers.md`)
- Caching и `dynamic = 'force-dynamic'` (`app/01-getting-started/08-caching.md`)
- Metadata API (`app/01-getting-started/14-metadata-and-og-images.md`)
<!-- END:nextjs-agent-rules -->

## Конвенции этого проекта

- Тексты — на русском, кроме идентификаторов в коде.
- Цена/валюта формат: `500 ₽` (с неразрывным пробелом `&nbsp;` в JSX, где уместно).
- shadcn стиль `base-nova`, цветовая база `neutral`, акцент `oklch(0.546 0.245 262.881)` (синий).
- Иконки — `lucide-react`.
- Утилиты классов — через `cn()` из `@/lib/utils`.
- Server Actions — в `lib/actions/*.ts` с `"use server"` в начале файла.
- Клиентские компоненты — отмечать `"use client"` явно. По умолчанию всё серверное.
