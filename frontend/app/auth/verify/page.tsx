"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";

/**
 * Страница подтверждения входа по magic-link.
 *
 * Раньше ссылка из письма сразу «съедала» одноразовый токен на загрузке
 * (GET-обработчик), и почтовые сканеры/антивирусы, делая предпросмотр через GET,
 * гасили ссылку до того, как юзер по ней кликнет. Теперь токен расходуется
 * только по нажатию кнопки (POST на /auth/verify/confirm) — сканеры POST не шлют.
 */
export default function VerifyPage() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");
  const order = params.get("order");

  const [isVerifying, setIsVerifying] = useState(false);

  async function handleConfirm() {
    if (!token) {
      router.replace("/auth/error?reason=missing_token");
      return;
    }
    setIsVerifying(true);
    try {
      const res = await fetch("/auth/verify/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, order }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        router.replace(`/auth/error?reason=${data.error ?? "invalid_link"}`);
        return;
      }
      router.replace(data.redirectTo as string);
    } catch {
      router.replace("/auth/error?reason=unavailable");
    }
  }

  return (
    <main className="bg-gray-50 py-24 px-4 min-h-[70vh] flex items-center">
      <div className="max-w-md mx-auto text-center bg-white rounded-2xl border border-gray-100 p-10">
        <div className="text-5xl mb-5">🔐</div>
        <h1 className="text-xl font-bold text-gray-900 mb-3">Подтвердите вход</h1>
        <p className="text-gray-500 text-sm mb-8">
          Нажмите кнопку, чтобы войти в LawDocs и перейти к вашему документу.
        </p>
        <Button onClick={handleConfirm} disabled={isVerifying} className="h-10 px-6 w-full">
          {isVerifying ? "Входим…" : "Войти в LawDocs"}
        </Button>
      </div>
    </main>
  );
}
