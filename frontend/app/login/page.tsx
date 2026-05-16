"use client";

import { useState } from "react";
import Link from "next/link";
import { Scale, Loader2, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/auth/magic-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.error ?? "Не удалось отправить письмо. Попробуйте позже.");
        return;
      }

      setSent(true);
    } catch {
      setError("Ошибка сети. Проверьте подключение и попробуйте снова.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 font-semibold text-lg text-gray-900">
            <Scale className="h-5 w-5 text-blue-600" />
            LawDocs
          </Link>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 p-8">
          {sent ? (
            <div className="text-center space-y-4">
              <CheckCircle className="h-10 w-10 text-green-500 mx-auto" />
              <div>
                <p className="font-semibold text-gray-900">Письмо отправлено</p>
                <p className="text-sm text-gray-500 mt-1">
                  Проверьте почту <span className="font-medium text-gray-700">{email}</span> и нажмите на ссылку в письме.
                </p>
              </div>
              <p className="text-xs text-gray-400">
                Не получили?{" "}
                <button
                  onClick={() => { setSent(false); setError(null); }}
                  className="text-blue-600 hover:underline"
                >
                  Отправить ещё раз
                </button>
              </p>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h1 className="text-xl font-bold text-gray-900">Войти в LawDocs</h1>
                <p className="text-sm text-gray-500 mt-1">
                  Введите email — пришлём ссылку для входа.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    autoFocus
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      e.target.setCustomValidity("");
                    }}
                    onInvalid={(e) => {
                      const input = e.target as HTMLInputElement;
                      if (input.validity.valueMissing) {
                        input.setCustomValidity("Введите email-адрес");
                      } else if (input.validity.typeMismatch) {
                        input.setCustomValidity("Введите корректный email-адрес (например ivan@mail.ru)");
                      } else {
                        input.setCustomValidity("Некорректный email-адрес");
                      }
                    }}
                    placeholder="you@example.com"
                    className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  />
                </div>

                {error && <p className="text-sm text-red-600">{error}</p>}

                <Button type="submit" disabled={loading} className="w-full h-10">
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Отправляем…
                    </>
                  ) : (
                    "Получить ссылку для входа"
                  )}
                </Button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-sm text-gray-400 mt-6">
          Нет заказов?{" "}
          <Link href="/situations" className="text-blue-600 hover:underline">
            Оформить документ
          </Link>
        </p>
      </div>
    </main>
  );
}
