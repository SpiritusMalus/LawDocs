"use client";

import { useState } from "react";
import { Loader2, CheckCircle, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { setAccountPassword } from "@/lib/e2ee-password";

/**
 * Установка пароля аккаунта — вторая дверь к тем же ключам, чтобы не носить
 * ключ-файл. Пароль оборачивает текущий ключ устройства в браузере; на сервер
 * уходит только обёртка + хэш пароля. Приватный ключ сервер не видит.
 */
export function SetPasswordSection() {
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (pw.length < 8) {
      setError("Пароль должен быть не короче 8 символов");
      return;
    }
    if (pw !== pw2) {
      setError("Пароли не совпадают");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await setAccountPassword(pw);
      setDone(true);
      setPw("");
      setPw2("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить пароль");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="flex items-center gap-2 text-sm text-green-700">
        <CheckCircle className="h-4 w-4" />
        Пароль установлен. Теперь можно входить по email и паролю — без ключа-файла.
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
        <Lock className="h-4 w-4 text-primary" />
        Пароль для входа без ключа-файла
      </div>
      <p className="text-xs text-gray-500">
        Пароль зашифрует ваш ключ в браузере и позволит входить по email. Сам ключ
        на сервер не отправляется.
      </p>
      <input
        type="password"
        value={pw}
        onChange={(e) => setPw(e.target.value)}
        disabled={busy}
        placeholder="Новый пароль (минимум 8 символов)"
        className="w-full h-10 rounded-lg border border-gray-200 px-3 text-sm focus:border-primary focus:outline-none"
      />
      <input
        type="password"
        value={pw2}
        onChange={(e) => setPw2(e.target.value)}
        disabled={busy}
        placeholder="Повторите пароль"
        className="w-full h-10 rounded-lg border border-gray-200 px-3 text-sm focus:border-primary focus:outline-none"
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button type="submit" disabled={busy} className="w-full">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Установить пароль"}
      </Button>
    </form>
  );
}
