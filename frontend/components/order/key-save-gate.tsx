"use client";

import { useState } from "react";
import { Download, KeyRound, Loader2 } from "lucide-react";
import { E2EEClient } from "@/lib/e2ee-client";
import type { E2EEKeyPair } from "@/lib/e2ee-client";

// Обязательный шаг перед оплатой: гость сохраняет ключ-файл. Документ шифруется
// этим ключом; без файла доступ к нему не вернуть (чистый E2EE, вариант 2 из эпика).
export function KeySaveGate({
  keyPair,
  isPaying,
  error,
  onProceed,
}: {
  keyPair: E2EEKeyPair;
  isPaying: boolean;
  error: string | null;
  onProceed: () => void;
}) {
  const [downloaded, setDownloaded] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-left space-y-3">
      <div className="flex items-center gap-2 text-gray-900 font-semibold">
        <KeyRound className="h-5 w-5 text-primary" />
        Сохраните ключ доступа
      </div>
      <p className="text-sm text-gray-600">
        Документ шифруется вашим ключом — мы его не храним. Скачайте файл с ключом и
        сохраните его. Без этого файла восстановить доступ к документу будет невозможно.
      </p>

      <button
        type="button"
        onClick={() => {
          E2EEClient.downloadKeyFile(keyPair);
          setDownloaded(true);
        }}
        className="inline-flex items-center gap-2 rounded-md bg-white border border-gray-200 px-3 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50"
      >
        <Download className="h-4 w-4" />
        {downloaded ? "Скачать ещё раз" : "Скачать файл с ключом"}
      </button>

      <label className="flex items-start gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
          disabled={!downloaded}
          className="mt-0.5"
        />
        Я сохранил файл с ключом в надёжном месте
      </label>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="button"
        onClick={onProceed}
        disabled={!confirmed || isPaying}
        className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
      >
        {isPaying && <Loader2 className="h-4 w-4 animate-spin" />}
        Перейти к оплате
      </button>
    </div>
  );
}
