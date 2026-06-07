// Единый источник редакции оферты для фронтенда. Бэкенд хранит ту же версию в
// app/core/consent.py (CONSENT_VERSION / CONSENT_DATE_HUMAN). Инвариант-тест
// backend/tests/test_consent_version.py следит, чтобы значения не разошлись —
// рассинхрон версии/даты бьёт по юр-доказуемости акцепта.
export const OFFER_EDITION = {
  version: "2026-06-02", // машинная версия, совпадает с CONSENT_VERSION на бэкенде
  human: "2 июня 2026 г.", // человекочитаемая дата редакции (показывается в /legal/offer)
} as const;
