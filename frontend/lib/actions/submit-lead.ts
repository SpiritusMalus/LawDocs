"use server";

import { headers } from "next/headers";
import { SITUATIONS, type SituationId } from "@/lib/situations";
import { rateLimit, pruneRateLimitBuckets } from "@/lib/rate-limit";
import { isValidContact } from "@/lib/validators";

export interface LeadState {
  status: "idle" | "success" | "error";
  message?: string;
}

const MAX_LEN = 2000;
const ALLOWED_SITUATIONS = new Set<string>([
  ...SITUATIONS.map((s) => s.id),
  "other",
]);

const RATE_WINDOW_MS = 60 * 60 * 1000;
const RATE_MAX = 5;

function clean(value: FormDataEntryValue | null, max = 200): string {
  if (typeof value !== "string") return "";
  return value.trim().slice(0, max);
}

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

export async function submitLead(
  _prev: LeadState,
  formData: FormData
): Promise<LeadState> {
  const honeypot = clean(formData.get("website"));
  if (honeypot) {
    return { status: "success" };
  }

  pruneRateLimitBuckets();
  const ip = await getClientIp();
  const rl = rateLimit(`submit:${ip}`, { windowMs: RATE_WINDOW_MS, max: RATE_MAX });
  if (!rl.ok) {
    const minutes = Math.max(1, Math.ceil(rl.retryAfterMs / 60000));
    return {
      status: "error",
      message: `Слишком много заявок с этого адреса. Попробуйте через ${minutes} мин или напишите на hi@lawdocs.ru.`,
    };
  }

  const name = clean(formData.get("name"), 100);
  const contact = clean(formData.get("contact"), 200);
  const rawSituation = clean(formData.get("situation"), 50);
  const description = clean(formData.get("description"), MAX_LEN);
  const consent = formData.get("consent") === "on";

  if (!name) return { status: "error", message: "Укажите имя." };
  if (!contact) return { status: "error", message: "Укажите телефон или email для связи." };
  if (!isValidContact(contact))
    return { status: "error", message: "Контакт не похож ни на телефон, ни на email." };
  if (!description || description.length < 20)
    return { status: "error", message: "Опишите ситуацию хотя бы парой предложений." };
  if (!consent)
    return { status: "error", message: "Для отправки нужно согласие на обработку персональных данных." };

  const situationId: SituationId | "other" | "" = ALLOWED_SITUATIONS.has(rawSituation)
    ? (rawSituation as SituationId | "other")
    : "";
  const situation = SITUATIONS.find((s) => s.id === situationId);
  const situationLabel =
    situation?.title ?? (situationId === "other" ? "Другое / нет в списке" : "Не выбрано");

  const text = [
    "🆕 <b>Новая заявка LawDocs</b>",
    "",
    `<b>Ситуация:</b> ${escapeHtml(situationLabel)}`,
    `<b>Имя:</b> ${escapeHtml(name)}`,
    `<b>Контакт:</b> ${escapeHtml(contact)}`,
    `<b>IP:</b> ${escapeHtml(ip)}`,
    "",
    "<b>Описание:</b>",
    escapeHtml(description),
  ].join("\n");

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;

  if (!token || !chatId) {
    console.warn("[submitLead] Telegram env vars missing — lead not delivered. Situation: %s", situationLabel);
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
      console.error("[submitLead] Telegram error:", res.status, body);
      return {
        status: "error",
        message: "Не получилось отправить заявку. Попробуйте ещё раз или напишите на hi@lawdocs.ru.",
      };
    }
  } catch (err) {
    console.error("[submitLead] Telegram fetch failed:", err);
    return {
      status: "error",
      message: "Не получилось отправить заявку. Попробуйте ещё раз или напишите на hi@lawdocs.ru.",
    };
  }

  return { status: "success" };
}
