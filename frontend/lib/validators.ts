/** Shared client/server validation helpers. */

export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

/** Accepts +7XXXXXXXXXX, 8(999)123-45-67, etc. Min 7 digits total. */
export function isValidPhone(value: string): boolean {
  return /^[+\d][\d\s()\-]{6,}$/.test(value);
}

/** True if value looks like a valid email or phone number. */
export function isValidContact(value: string): boolean {
  if (!value) return false;
  return isValidEmail(value) || isValidPhone(value);
}

/** UUID v4 pattern — used to validate IDs received from URLs before using them. */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isValidUuid(value: string): boolean {
  return UUID_RE.test(value);
}
