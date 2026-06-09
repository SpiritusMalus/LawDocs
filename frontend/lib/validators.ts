/** Shared client/server validation helpers. */

export function isValidEmail(value: string): boolean {
  if (!value || value.length > 254) return false;
  // RFC 5321 simplified but more comprehensive than before
  return /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/.test(value);
}

/** Сообщение-плашка при попытке ввести Gmail. */
export const GMAIL_BLOCKED_MESSAGE = "Извините, gmail запрещен в России для регистрации";

// gmail.com и его историческое зеркало googlemail.com ведут в один и тот же
// сервис Google — запрещаем оба домена.
const BLOCKED_EMAIL_DOMAINS = ["gmail.com", "googlemail.com"];

/** True если домен почты запрещён (Gmail и зеркала). */
export function isBlockedEmailDomain(value: string): boolean {
  const at = value.lastIndexOf("@");
  if (at === -1) return false;
  return BLOCKED_EMAIL_DOMAINS.includes(value.slice(at + 1).trim().toLowerCase());
}

/** Accepts +7XXXXXXXXXX, 8(999)123-45-67, etc. Min 7 digits total. */
export function isValidPhone(value: string): boolean {
  if (!value || value.length > 20) return false;
  const digitsOnly = value.replace(/\D/g, "");
  return digitsOnly.length >= 7 && digitsOnly.length <= 15;
}

/** True if value looks like a valid email or phone number. */
export function isValidContact(value: string): boolean {
  if (!value) return false;
  return isValidEmail(value) || isValidPhone(value);
}

/** UUID v4 pattern — RFC 4122 UUIDv4: xxxxxxxx-xxxx-4xxx-[89ab]xxx-xxxxxxxxxxxx */
const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isValidUuid(value: string): boolean {
  return UUID_V4_RE.test(value);
}
