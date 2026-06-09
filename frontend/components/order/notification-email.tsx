"use client";

import { useState } from "react";
import { Loader2, Mail } from "lucide-react";
import { resendNotification } from "@/lib/api-client";
import { GMAIL_BLOCKED_MESSAGE, isBlockedEmailDomain, isValidEmail } from "@/lib/validators";

// Блок «письмо ушло на <почту>» с возможностью исправить адрес и переслать.
// Закрывает кейс «опечатался в почте → документ не пришёл»: форму не перезаполняем.
export function NotificationEmail({
  orderId,
  email,
}: {
  orderId: string;
  email: string | null;
}) {
  const [current, setCurrent] = useState(email);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(email ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit() {
    const trimmed = value.trim();
    if (!isValidEmail(trimmed)) {
      setError("Укажите корректный email-адрес.");
      return;
    }
    if (isBlockedEmailDomain(trimmed)) {
      setError(GMAIL_BLOCKED_MESSAGE);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const changed = trimmed.toLowerCase() !== (current ?? "").toLowerCase();
      const res = await resendNotification(orderId, changed ? trimmed : undefined);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? data.error ?? "Не удалось отправить письмо. Попробуйте позже.");
        return;
      }
      setCurrent(trimmed);
      setEditing(false);
      setDone(true);
    } catch {
      setError("Не удалось связаться с сервером. Попробуйте позже.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-left text-sm">
      <div className="flex items-start gap-2">
        <Mail className="h-4 w-4 text-gray-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          {done ? (
            <p className="text-gray-600">
              Письмо отправлено на <span className="font-medium text-gray-900">{current}</span>.
            </p>
          ) : (
            <p className="text-gray-600">
              Письмо на <span className="font-medium text-gray-900">{current ?? "вашу почту"}</span>.
              Не пришло или адрес с ошибкой?
            </p>
          )}

          {!editing && (
            <button
              type="button"
              onClick={() => {
                setEditing(true);
                setDone(false);
                setValue(current ?? "");
              }}
              className="mt-1 font-medium text-primary underline hover:no-underline"
            >
              Изменить адрес и переслать
            </button>
          )}

          {editing && (
            <div className="mt-2 space-y-2">
              <input
                type="email"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="ivan@mail.ru"
                disabled={busy}
                className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={submit}
                  disabled={busy}
                  className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-60"
                >
                  {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                  Переслать
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditing(false);
                    setError(null);
                  }}
                  disabled={busy}
                  className="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900 disabled:opacity-60"
                >
                  Отмена
                </button>
              </div>
            </div>
          )}

          {error && <p className="mt-2 text-red-600">{error}</p>}
        </div>
      </div>
    </div>
  );
}
