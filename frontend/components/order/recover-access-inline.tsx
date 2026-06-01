"use client";

import { useState, useRef } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { recoverViaKeyFile, recoverViaPhrase } from "@/lib/e2ee-recovery";

type Method = "keyfile" | "phrase";

/**
 * Инлайн-восстановление доступа прямо на странице заказа, когда приватного
 * ключа нет в этом браузере. Юзер загружает ключ-файл или вводит фразу — ключ
 * встаёт в localStorage, и onRecovered повторяет скачивание. Без перезаходов.
 */
export function RecoverAccessInline({ onRecovered }: { onRecovered: () => void }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [method, setMethod] = useState<Method>("keyfile");
  const [email, setEmail] = useState("");
  const [phrase, setPhrase] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onRecovered();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось восстановить доступ");
    } finally {
      setBusy(false);
    }
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) run(() => recoverViaKeyFile(file));
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-left space-y-3">
      <p className="text-sm text-amber-800">
        Документ зашифрован вашим ключом, а в этом браузере его нет (другое
        устройство или очищенные данные). Восстановите доступ — файл скачается сразу.
      </p>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => { setMethod("keyfile"); setError(null); }}
          className={`flex-1 text-sm py-1.5 rounded border font-medium transition ${
            method === "keyfile"
              ? "bg-white border-amber-300 text-amber-900"
              : "bg-transparent border-amber-200 text-amber-700"
          }`}
        >
          Ключ-файл
        </button>
        <button
          type="button"
          onClick={() => { setMethod("phrase"); setError(null); }}
          className={`flex-1 text-sm py-1.5 rounded border font-medium transition ${
            method === "phrase"
              ? "bg-white border-amber-300 text-amber-900"
              : "bg-transparent border-amber-200 text-amber-700"
          }`}
        >
          Фраза восстановления
        </button>
      </div>

      {method === "keyfile" && (
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            onChange={onFile}
            className="hidden"
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={busy}
            className="w-full"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Загрузить ключ-файл (lawdocs-key.json)"}
          </Button>
        </div>
      )}

      {method === "phrase" && (
        <form
          onSubmit={(e) => { e.preventDefault(); run(() => recoverViaPhrase(email, phrase)); }}
          className="space-y-2"
        >
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Ваш email"
            required
            className="w-full px-3 py-2 border border-amber-200 rounded-lg text-sm"
          />
          <input
            type="text"
            value={phrase}
            onChange={(e) => setPhrase(e.target.value)}
            placeholder="Фраза восстановления"
            required
            className="w-full px-3 py-2 border border-amber-200 rounded-lg font-mono text-sm"
          />
          <Button type="submit" disabled={busy || !email || !phrase} className="w-full">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Восстановить доступ"}
          </Button>
        </form>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
