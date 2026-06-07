"use client";

import { useRef, useState } from "react";
import { Loader2, CheckCircle, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { importKeysToKeyring } from "@/lib/e2ee-password";

/**
 * Импорт нескольких ключ-файлов в keyring под паролем аккаунта. Объединяет
 * заказы по разным ключам под одним паролем — документы не переподписываются.
 * Требует уже установленного пароля аккаунта (см. SetPasswordSection).
 */
export function ImportKeysSection() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [total, setTotal] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const count = await importKeysToKeyring(files, password);
      setTotal(count);
      setFiles([]);
      setPassword("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось импортировать ключи");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
        <KeyRound className="h-4 w-4 text-primary" />
        Объединить ключи
      </div>
      <p className="text-xs text-gray-500">
        Если у вас несколько ключ-файлов от разных заказов — добавьте их сюда. Под
        одним паролем кабинет покажет заказы по всем ключам. Сначала установите пароль выше.
      </p>

      <input
        ref={fileInputRef}
        type="file"
        accept="application/json,.json"
        multiple
        disabled={busy}
        onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
        className="block w-full text-sm text-gray-500 file:mr-3 file:rounded-lg file:border-0 file:bg-primary/10 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary"
      />
      {files.length > 0 && (
        <p className="text-xs text-gray-500">Выбрано файлов: {files.length}</p>
      )}

      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={busy}
        placeholder="Пароль аккаунта"
        className="w-full h-10 rounded-lg border border-gray-200 px-3 text-sm focus:border-primary focus:outline-none"
      />

      {error && <p className="text-sm text-red-600">{error}</p>}
      {total !== null && (
        <p className="flex items-center gap-2 text-sm text-green-700">
          <CheckCircle className="h-4 w-4" />
          Готово. Ключей в связке: {total}.
        </p>
      )}

      <Button
        type="submit"
        disabled={busy || files.length === 0 || password.length === 0}
        className="w-full"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Импортировать ключи"}
      </Button>
    </form>
  );
}
