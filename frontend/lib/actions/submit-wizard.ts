"use server";

import { cookies, headers } from "next/headers";
import { rateLimit, pruneRateLimitBuckets } from "@/lib/rate-limit";
import { WIZARD_STEPS, type WizardSituationId } from "@/lib/wizard-questions";
import { SITUATIONS } from "@/lib/situations";
import { isValidEmail, isValidPhone } from "@/lib/validators";
import { validateOrderInitResponse } from "@/lib/api-schemas";

export interface WizardState {
  status: "idle" | "success" | "error" | "email_sent" | "redirect";
  message?: string;
  orderId?: string;
}

// Derived from SITUATIONS — single source of truth for situation titles
const SITUATION_LABELS = Object.fromEntries(
  SITUATIONS.map((s) => [s.id, s.title])
) as Record<WizardSituationId, string>;

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
  // X-Real-IP: nginx sets this to $remote_addr — cannot be spoofed by the client
  const realIp = h.get("x-real-ip");
  if (realIp) return realIp.trim();
  // CF-Connecting-IP: Cloudflare sets this (trusted at edge level)
  const cfIp = h.get("cf-connecting-ip");
  if (cfIp) return cfIp.trim();
  // X-Forwarded-For: nginx appends real IP at the end — take last entry, not first
  const forwarded = h.get("x-forwarded-for");
  if (forwarded) {
    const ips = forwarded.split(",").map((ip) => ip.trim());
    return ips[ips.length - 1] ?? "unknown";
  }
  return "unknown";
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
  const maxRequests = process.env.APP_ENV === "development" ? 1000 : 5;
  const rl = rateLimit(`submit:${ip}`, { windowMs: 60 * 60 * 1000, max: maxRequests });
  if (!rl.ok) {
    const minutes = Math.max(1, Math.ceil(rl.retryAfterMs / 60000));
    return {
      status: "error",
      message: `Слишком много заявок. Попробуйте через ${minutes} мин или напишите на lawdocsru@gmail.com.`,
    };
  }

  // Server-side validation: required fields
  const requiredFieldIds = WIZARD_STEPS[situationId]
    .flatMap((step) => step.fields)
    .filter((f) => f.required)
    .map((f) => f.id);

  const missing = requiredFieldIds.filter((id) => !answers[id]?.trim());
  if (missing.length > 0) {
    return { status: "error", message: "Не заполнены обязательные поля." };
  }

  const email = answers["email"]!.trim();
  const phone = answers["phone"]!.trim();

  if (!isValidEmail(email)) {
    return { status: "error", message: "Укажите корректный email-адрес (например ivan@mail.ru)." };
  }
  if (!isValidPhone(phone)) {
    return { status: "error", message: "Укажите корректный номер телефона." };
  }

  // Phase 2: route to FastAPI when backend is configured
  const backendUrl = process.env.BACKEND_URL;
  if (backendUrl) {
    try {
      const cookieStore = await cookies();
      const accessToken = cookieStore.get("access_token")?.value;

      const reqHeaders: Record<string, string> = {
        "Content-Type": "application/json",
        "X-Real-IP": ip,
      };
      if (accessToken) reqHeaders["Authorization"] = `Bearer ${accessToken}`;

      const res = await fetch(`${backendUrl}/api/v1/orders/init`, {
        method: "POST",
        headers: reqHeaders,
        body: JSON.stringify({
          email: answers["email"]!.trim(),
          situation_id: situationId,
          form_data: answers,
        }),
        cache: "no-store",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = (body as { detail?: unknown }).detail;
        return {
          status: "error",
          message: typeof detail === "string" ? detail : "Ошибка сервера. Попробуйте ещё раз.",
        };
      }
      try {
        const jsonData = await res.json();
        const validated = validateOrderInitResponse(jsonData);
        if (!validated.requires_verification && validated.redirect_to) {
          return { status: "redirect", orderId: validated.order_id };
        }
        return { status: "email_sent", orderId: validated.order_id };
      } catch {
        return {
          status: "error",
          message: "Неверный ответ от сервера. Попробуйте ещё раз.",
        };
      }
    } catch {
      return {
        status: "error",
        message: "Сервер недоступен. Попробуйте ещё раз или напишите на lawdocsru@gmail.com.",
      };
    }
  }

  // Phase 1 fallback: send to Telegram
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
    console.warn("[submitWizard] Telegram not configured — lead not delivered. Situation: %s", situationId);
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
        message: "Не получилось отправить заявку. Напишите на lawdocsru@gmail.com.",
      };
    }
  } catch (err) {
    console.error("[submitWizard] fetch failed:", err);
    return {
      status: "error",
      message: "Не получилось отправить заявку. Напишите на lawdocsru@gmail.com.",
    };
  }

  return { status: "success" };
}
