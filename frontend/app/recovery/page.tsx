"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { E2EEClient } from "@/lib/e2ee-client";
import { Button } from "@/components/ui/button";

type Step = "form" | "recovering" | "done" | "error";

export default function RecoveryPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [phrase, setPhrase] = useState("");
  const [step, setStep] = useState<Step>("form");
  const [error, setError] = useState<string | null>(null);

  async function handleRecover(e: React.FormEvent) {
    e.preventDefault();
    setStep("recovering");
    setError(null);

    try {
      const res = await fetch("/api/auth/recover-access", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });

      if (res.status === 404) {
        throw new Error("Пользователь с таким email не найден");
      }
      if (res.status === 400) {
        throw new Error("Для этого аккаунта нет сохранённого backup ключа");
      }
      if (!res.ok) {
        throw new Error("Ошибка сервера. Попробуйте позже.");
      }

      const { backup_encrypted } = await res.json() as { backup_encrypted: string };

      const privateKey = await E2EEClient.decryptPasswordProtectedBackup(
        backup_encrypted,
        phrase
      );

      // Получаем public_key из приватного через nacl
      // (для простоты — получить при setup'е. Пока просто сохраняем privateKey)
      E2EEClient.savePrivateKeyToLocalStorage(privateKey);

      setStep("done");
      setTimeout(() => router.replace("/"), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Неизвестная ошибка");
      setStep("error");
    }
  }

  return (
    <main className="bg-gray-50 min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-2xl border border-gray-100 p-8 space-y-6">

          {(step === "form" || step === "error") && (
            <>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Восстановление доступа</h1>
                <p className="text-sm text-gray-500 mt-1">
                  Введите email и фразу восстановления — ключ будет расшифрован в вашем браузере.
                  Фраза не передаётся на сервер.
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                <p className="text-xs text-amber-800">
                  ⚠️ Если вы потеряли фразу восстановления <strong>и</strong> ключ-файл —
                  восстановить документы невозможно даже с нашей помощью.
                </p>
              </div>

              <form onSubmit={handleRecover} className="space-y-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-gray-700">Email</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-gray-700">Фраза восстановления</label>
                  <input
                    type="text"
                    required
                    value={phrase}
                    onChange={(e) => setPhrase(e.target.value)}
                    placeholder="xxxx — xxxx — xxxx — xxxx"
                    className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
                <Button type="submit" className="w-full">
                  Восстановить ключ
                </Button>
              </form>
            </>
          )}

          {step === "recovering" && (
            <div className="text-center py-8 text-gray-500">Расшифровываем ключ…</div>
          )}

          {step === "done" && (
            <div className="text-center py-8 space-y-2">
              <div className="text-green-600 text-3xl">✓</div>
              <p className="font-semibold text-gray-900">Ключ восстановлен</p>
              <p className="text-sm text-gray-500">Переходим на главную…</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
