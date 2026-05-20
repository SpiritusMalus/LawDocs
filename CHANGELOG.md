# Changelog

All notable changes to LawDocs are documented in this file.

## [0.0.1.0] - 2026-05-20

### Security
- **Fix XSS vulnerability** — replaced sessionStorage-based admin secret with httpOnly cookie (4-hour TTL, sameSite=strict). Secrets are no longer accessible to JavaScript, protecting against XSS exploitation.
- **Add CSRF protection for admin mutations** — /api/admin/* POST/PATCH/DELETE now require Origin header, preventing cross-site request forgery from older browsers that omit Origin headers.

### Fixed
- **UUID validation in admin reviews API** — added isValidUuid check before proxying admin requests to backend
- **Race condition in review visibility toggle** — added pessimistic locking (.with_for_update) to prevent concurrent toggle race conditions
- **Profile update logging** — update_me endpoint now logs when user profile changes
- **Validator duplication** — consolidated strip_whitespace validator to shared backend/app/core/validators.py (also removed forgotten html.escape from users.py)

## [0.27.0.0] - 2026-05-17

### Added
- Пять новых шаблонов по итогам ресерча массовых правовых ситуаций (9111.ru, pravoved.ru, статистика Роспотребнадзора):
  - **dtp_osago** (`transport/`) — досудебная претензия в страховую по ОСАГО за просрочку или занижение выплаты. Ссылки: ФЗ-40 ст. 12 и 16.1 (неустойка 1%/день), ФЗ-123 (финансовый уполномоченный до суда), ЗоЗПП ст. 13 (штраф 50%).
  - **auto_repair** (`consumer/`) — претензия в автосервис за некачественный ремонт, задержку возврата авто или завышение цены. ЗоЗПП ст. 28 (3%/день) и ст. 29, ГК РФ ст. 709, 722.
  - **debt_collector** (`legal/`) — жалоба в ФССП на коллекторов: ночные звонки, угрозы, звонки третьим лицам. ФЗ-230, КоАП ст. 14.57 (штраф до 500 000 руб.).
  - **carsharing** (`consumer/`) — претензия каршерингу (Яндекс.Драйв, Делимобиль и др.) за необоснованно предъявленный ущерб или неправомерное списание. ГК РФ ст. 401, 620, ЗоЗПП ст. 14.
  - **gym_refund** (`consumer/`) — претензия фитнес-клубу за отказ вернуть деньги за неиспользованный абонемент. ЗоЗПП ст. 32 (право отказаться в любое время), ГК РФ ст. 782, ЗоЗПП ст. 31 (10 дней на возврат).

### Changed
- `services/llm.py` — пять новых ситуаций добавлены в `_SITUATION_TYPES` для корректной генерации инструкций.

Итого активных шаблонов: **25** (было 20).

## [0.26.0.0] - 2026-05-17

### Added
- Три новых шаблона для споров с застройщиком по ДДУ (Федеральный закон № 214-ФЗ):
  - **ddu_delay** — претензия за просрочку передачи квартиры. Python-калькулятор вычисляет дни просрочки и сумму неустойки (1/150 ставки ЦБ × цена × дни) до вызова LLM — пользователь получает документ с готовыми расчётами.
  - **ddu_defects** — претензия за строительные недостатки. Ссылки на 5-летнюю гарантию (ст. 7 ФЗ-214) и права потребителя (ст. 29 ЗоЗПП).
  - **ddu_termination** — уведомление о расторжении ДДУ и требование возврата денег с процентами. Python-калькулятор считает итоговую сумму возврата (цена + 1/150 ставки за каждый день использования).
- `services/calculators.py` — модуль детерминированных расчётов. Словарь `SITUATION_CALCULATORS` позволяет добавлять новые калькуляторы одной строкой без изменений в остальном коде.

### Changed
- `services/generation.py` — перед вызовом LLM теперь применяется калькулятор (если есть для данной ситуации), `form_data` обогащается `calculated_*` полями.
- `services/llm.py` — три новых ДДУ-ситуации добавлены в `_SITUATION_TYPES` для корректной генерации инструкций.

Итого активных шаблонов: **20** (было 17).
