"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { E2EEClient } from "@/lib/e2ee-client";
import { Button } from "@/components/ui/button";

type Step = "generating" | "show_phrase" | "saving" | "done" | "error";

function generatePhrase(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(18));
  const b64 = btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
  // Разбиваем 24 символа на 4 группы по 6: xxxx-xx xxxx-xx xxxx-xx xxxx-xx
  return [
    b64.slice(0, 6),
    b64.slice(6, 12),
    b64.slice(12, 18),
    b64.slice(18, 24),
  ].join(" — ");
}

export default function SetupE2EEPage() {
  const router = useRouter();
  const params = useSearchParams();
  const nextUrl = params.get("next") ?? "/";

  const [step, setStep] = useState<Step>("generating");
  const [phrase, setPhrase] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const keypairRef = useRef<{ publicKey: string; privateKey: string } | null>(null);

  useEffect(() => {
    // Если ключи уже есть — пропускаем setup
    if (E2EEClient.hasKeys()) {
      router.replace(nextUrl);
      return;
    }

    const kp = E2EEClient.generateKeyPair();
    keypairRef.current = kp;
    const p = generatePhrase();
    setPhrase(p);
    setStep("show_phrase");
  }, [nextUrl, router]);

  async function handleSave() {
    const kp = keypairRef.current;
    if (!kp || !phrase) return;

    setStep("saving");
    try {
      const backup = await E2EEClient.createPasswordProtectedBackup(
        kp.privateKey,
        phrase
      );

      const res = await fetch("/api/auth/setup-e2ee", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          public_key: kp.publicKey,
          encrypted_backup: backup,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail ?? "Ошибка сервера");
      }

      E2EEClient.savePrivateKeyToLocalStorage(kp.privateKey);
      E2EEClient.savePublicKeyToLocalStorage(kp.publicKey);

      setStep("done");
      setTimeout(() => router.replace(nextUrl), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Неизвестная ошибка");
      setStep("error");
    }
  }

  function downloadKeyFile() {
    const kp = keypairRef.current;
    if (!kp) return;
    const content = JSON.stringify(
      { privateKey: kp.privateKey, publicKey: kp.publicKey, createdAt: new Date().toISOString() },
      null,
      2
    );
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lawdocs-key.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="bg-gray-50 min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
      <div className="w-full max-w-lg">
        <div className="bg-white rounded-2xl border border-gray-100 p-8 space-y-6">

          {step === "generating" && (
            <div className="text-center py-8 text-gray-500">Генерируем ключи…</div>
          )}

          {step === "show_phrase" && (
            <>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Настройте защиту документов</h1>
                <p className="text-sm text-gray-500 mt-1">
                  Ваши документы будут зашифрованы так, что открыть их сможете только вы.
                </p>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
                <p className="text-sm font-semibold text-amber-800">
                  ⚠️ Сохраните фразу восстановления
                </p>
                <p className="text-xs text-amber-700">
                  Она показывается <strong>один раз</strong>. Если потеряете фразу — документы
                  восстановить будет невозможно, даже с нашей помощью.
                </p>
              </div>

              <div className="bg-gray-50 rounded-xl border border-gray-200 p-4">
                <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide font-medium">
                  Ваша фраза восстановления
                </p>
                <p className="font-mono text-lg text-gray-900 tracking-wider select-all break-all">
                  {phrase}
                </p>
              </div>

              <div className="space-y-3">
                <button
                  onClick={downloadKeyFile}
                  className="w-full text-sm text-blue-600 hover:underline text-left"
                >
                  Дополнительно: скачать ключ-файл (для восстановления без фразы)
                </button>

                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={acknowledged}
                    onChange={(e) => setAcknowledged(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300"
                  />
                  <span className="text-sm text-gray-700">
                    Я сохранил фразу восстановления в надёжном месте и понимаю,
                    что без неё документы нельзя будет восстановить
                  </span>
                </label>

                <Button
                  onClick={handleSave}
                  disabled={!acknowledged}
                  className="w-full"
                >
                  Продолжить
                </Button>
              </div>
            </>
          )}

          {step === "saving" && (
            <div className="text-center py-8 text-gray-500">Сохраняем ключи…</div>
          )}

          {step === "done" && (
            <div className="text-center py-8 space-y-2">
              <div className="text-green-600 text-3xl">✓</div>
              <p className="font-semibold text-gray-900">Защита настроена</p>
              <p className="text-sm text-gray-500">Переходим к вашему заказу…</p>
            </div>
          )}

          {step === "error" && (
            <div className="space-y-4">
              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <p className="text-sm text-red-700">{error}</p>
              </div>
              <Button variant="outline" onClick={() => setStep("show_phrase")} className="w-full">
                Попробовать снова
              </Button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
