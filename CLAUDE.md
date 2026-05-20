# LawDocs

## 🔴 CRITICAL: SESSION START RITUAL (АВТОМАТИЧЕСКИЙ)

Я автоматически выполняю это при начале сессии (не нужна твоя команда).

**ТЫ МОЖЕШЬ ИСПОЛЬЗОВАТЬ КОМАНДЫ-ТРИГГЕРЫ:**

Пиши в чат и я буду понимать:

```
"начинаем" / "старт"     → Читаю handoff, показываю статус+бэклог
"статус?"                 → Текущий статус (без работы)
"продолжаем"              → Продолжу незаконченную работу
"бэклог" / "список"       → Полный backlog что осталось
"что осталось?"           → Что не доделано в этой сессии
"проверь" / "validate"    → Validation перед close
"готово" / "закрыть"      → Close session + create handoff
"помощь" / "?"            → Показать все команды
"правила"                 → 5 главных правил сессии
"модель"                  → Какая модель выбрана и почему
"план"                    → План этой сессии
```

Полный список и примеры: [[TRIGGER_COMMANDS]]

---

**КАК ЭТО РАБОТАЕТ:**

1. **Ты:** "начинаем"
2. **Я:** [читаю handoff_N, показываю статус, бэклог, рекомендации]
3. **Ты:** "Issue #20" (выбираешь что делать)
4. **Я:** [выполняю ritual, показываю 5 правил, модель, план]
5. **Ты:** "начинай"
6. **Я:** [работаю]

---

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
