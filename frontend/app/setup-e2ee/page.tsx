"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { E2EEClient } from "@/lib/e2ee-client";
import { Button } from "@/components/ui/button";

type Step = "generating" | "show_phrase" | "saving" | "done" | "error";

export default function SetupE2EEPage() {
  const router = useRouter();
  const params = useSearchParams();
  const rawNext = params.get("next") ?? "/";
  const nextUrl = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/";

  const [step, setStep] = useState<Step>("generating");
  const [phrase, setPhrase] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phraseCopied, setPhraseCopied] = useState(false);
  const [phraseInput, setPhraseInput] = useState("");
  const [phraseConfirmed, setPhraseConfirmed] = useState(false);

  const keypairRef = useRef<{ publicKey: string; privateKey: string } | null>(null);

  useEffect(() => {
    // Если ключи уже есть — пропускаем setup
    if (E2EEClient.hasKeys()) {
      router.replace(nextUrl);
      return;
    }

    const kp = E2EEClient.generateKeyPair();
    keypairRef.current = kp;
    const p = E2EEClient.generateRecoveryPhrase();
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

  async function copyPhraseToClipboard() {
    try {
      await navigator.clipboard.writeText(phrase);
      setPhraseCopied(true);
    } catch (e) {
      console.error("Failed to copy phrase", e);
    }
  }

  function validatePhraseInput(input: string) {
    setPhraseInput(input);
    setPhraseConfirmed(input === phrase);
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

              <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 space-y-3">
                <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">
                  Ваша фраза восстановления
                </p>
                <p className="font-mono text-lg text-gray-900 tracking-wider select-all break-all">
                  {phrase}
                </p>
                <button
                  onClick={copyPhraseToClipboard}
                  className={`w-full text-sm py-2 px-3 rounded border font-medium transition ${
                    phraseCopied
                      ? "bg-green-50 border-green-200 text-green-700"
                      : "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100"
                  }`}
                >
                  {phraseCopied ? "✓ Скопировано" : "📋 Скопировать фразу"}
                </button>
              </div>

              {phraseCopied && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-900">
                    Подтвердите фразу (вставьте скопированное)
                  </label>
                  <input
                    type="text"
                    value={phraseInput}
                    onChange={(e) => validatePhraseInput(e.target.value)}
                    placeholder="Вставьте фразу сюда…"
                    className={`w-full px-3 py-2 border rounded-lg font-mono text-sm transition ${
                      phraseConfirmed
                        ? "border-green-300 bg-green-50"
                        : phraseInput
                        ? "border-red-300 bg-red-50"
                        : "border-gray-300"
                    }`}
                  />
                  {phraseInput && !phraseConfirmed && (
                    <p className="text-xs text-red-600">Фраза не совпадает. Проверьте ввод.</p>
                  )}
                  {phraseConfirmed && (
                    <p className="text-xs text-green-600">✓ Фраза подтверждена</p>
                  )}
                </div>
              )}

              <div className="space-y-3">
                <button
                  onClick={downloadKeyFile}
                  className="w-full text-sm text-blue-600 hover:underline text-left"
                >
                  Дополнительно: скачать ключ-файл (для восстановления без фразы)
                </button>

                <Button
                  onClick={handleSave}
                  disabled={!phraseConfirmed}
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
