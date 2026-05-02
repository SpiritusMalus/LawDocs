"use server";

import { headers } from "next/headers";
import { rateLimit, pruneRateLimitBuckets } from "@/lib/rate-limit";
import type { WizardSituationId } from "@/lib/wizard-questions";

export interface WizardState {
  status: "idle" | "success" | "error";
  message?: string;
}

const SITUATION_LABELS: Record<WizardSituationId, string> = {
  shop: "Магазин не возвращает деньги",
  marketplace: "Проблема с маркетплейсом",
  bank: "Банк списал лишнее",
  employer: "Работодатель не выплатил",
  insurance: "Страховая занизила выплату",
  utility: "УК / ЖКХ",
  airline: "Задержка или отмена рейса",
};

const FIELD_LABELS: Record<string, string> = {
  full_name: "ФИО",
  contact_address: "Адрес",
  phone: "Телефон",
  email: "Email",
  demand: "Требование",
  problem_desc: "Описание",
  problem_type: "Тип проблемы",
  violation_type: "Тип нарушения",
  store_name: "Магазин",
  store_address: "Адрес магазина",
  product_name: "Товар",
  product_price: "Цена, ₽",
  purchase_date: "Дата покупки",
  appeal_date: "Дата обращения",
  store_response: "Ответ магазина",
  penalty_start_date: "Дата начала неустойки",
  platform: "Маркетплейс",
  platform_other: "Другой маркетплейс",
  order_number: "Номер заказа",
  order_amount: "Сумма заказа, ₽",
  order_date: "Дата заказа",
  incident_date: "Дата события",
  withheld_amount: "Спорная сумма, ₽",
  bank_name: "Банк",
  contract_number: "Номер договора",
  violation_date: "Дата нарушения",
  amount: "Спорная сумма, ₽",
  company_name: "Организация",
  company_inn: "ИНН",
  director_name: "Директор",
  company_address: "Адрес организации",
  position: "Должность",
  hire_date: "Дата приёма",
  debt_amount: "Сумма долга, ₽",
  debt_period: "Период долга",
  last_payment_date: "Последняя выплата",
  additional_desc: "Доп. обстоятельства",
  insurance_company: "Страховая",
  policy_type: "Тип полиса",
  policy_number: "Номер полиса",
  incident_type: "Тип нарушения",
  incident_desc: "Обстоятельства",
  actual_damage: "Реальный ущерб, ₽",
  paid_amount: "Выплачено страховой, ₽",
  overdue_days: "Дней просрочки",
  apartment_address: "Адрес квартиры",
  violation_period: "Период нарушения",
  disputed_amount: "Сумма к перерасчёту, ₽",
  airline: "Авиакомпания",
  flight_number: "Номер рейса",
  route: "Маршрут",
  flight_date: "Дата вылета",
  delay_hours: "Задержка, часов",
  ticket_price: "Стоимость билетов, ₽",
  extra_expenses: "Доп. расходы, ₽",
  received_compensation: "Получено от авиакомпании, ₽",
};

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

async function getClientIp(): Promise<string> {
  const h = await headers();
  const forwarded = h.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0]!.trim();
  return h.get("x-real-ip") ?? "unknown";
}

export async function submitWizard({
  situationId,
  answers,
}: {
  situationId: WizardSituationId;
  answers: Record<string, string>;
}): Promise<WizardState> {
  pruneRateLimitBuckets();
  const ip = await getClientIp();
  const rl = rateLimit(`wizard:${ip}`, { windowMs: 60 * 60 * 1000, max: 5 });
  if (!rl.ok) {
    const minutes = Math.max(1, Math.ceil(rl.retryAfterMs / 60000));
    return {
      status: "error",
      message: `Слишком много заявок. Попробуйте через ${minutes} мин или напишите на hi@lawdocs.ru.`,
    };
  }

  const email = answers["email"]?.trim() ?? "";
  const fullName = answers["full_name"]?.trim() ?? "";
  if (!fullName || !email) {
    return { status: "error", message: "Не заполнены обязательные поля (ФИО, Email)." };
  }

  const situationLabel = SITUATION_LABELS[situationId];
  const lines: string[] = [
    "📋 <b>Новая заявка [WIZARD] — LawDocs</b>",
    "",
    `<b>Ситуация:</b> ${escapeHtml(situationLabel)}`,
    `<b>IP:</b> ${escapeHtml(ip)}`,
    "",
  ];

  for (const [key, raw] of Object.entries(answers)) {
    const value = raw?.trim();
    if (!value) continue;
    const label = FIELD_LABELS[key] ?? key;
    lines.push(`<b>${escapeHtml(label)}:</b> ${escapeHtml(value)}`);
  }

  const text = lines.join("\n");
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;

  if (!token || !chatId) {
    console.warn("[submitWizard] Telegram not configured — lead not delivered");
    console.info("[submitWizard]", { situationId, answers });
    return { status: "success" };
  }

  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text,
        parse_mode: "HTML",
        disable_web_page_preview: true,
      }),
      cache: "no-store",
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      console.error("[submitWizard] Telegram error:", res.status, body);
      return {
        status: "error",
        message: "Не получилось отправить заявку. Напишите на hi@lawdocs.ru.",
      };
    }
  } catch (err) {
    console.error("[submitWizard] fetch failed:", err);
    return {
      status: "error",
      message: "Не получилось отправить заявку. Напишите на hi@lawdocs.ru.",
    };
  }

  return { status: "success" };
}
