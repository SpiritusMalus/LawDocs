"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, KeyRound, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { loginViaKeyFile, loginViaPrivateKey } from "@/lib/e2ee-login";
import { loginViaPassword } from "@/lib/e2ee-password";

type Method = "keyfile" | "paste" | "password";

export default function DownloadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [method, setMethod] = useState<Method>("keyfile");
  const [pastedKey, setPastedKey] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<string>) {
    setBusy(true);
    setError(null);
    try {
      const redirectTo = await fn();
      router.push(redirectTo);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось войти по ключу");
      setBusy(false);
    }
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) run(() => loginViaKeyFile(file));
  }

  return (
    <main className="bg-gray-50 px-4 min-h-[calc(100vh-4rem)] flex items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-2xl border border-gray-100 p-8 space-y-5">
          <div className="text-center space-y-2">
            <KeyRound className="h-10 w-10 text-primary mx-auto" />
            <h1 className="text-xl font-bold text-gray-900">Скачать свои файлы</h1>
            <p className="text-sm text-gray-500">
              Войдите по ключу-файлу, который вы сохранили при покупке. Ключ
              остаётся в браузере — на сервер он не отправляется.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setMethod("keyfile"); setError(null); }}
              className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                method === "keyfile"
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-gray-200 text-gray-500 hover:text-gray-700"
              }`}
            >
              Ключ-файл
            </button>
            <button
              type="button"
              onClick={() => { setMethod("paste"); setError(null); }}
              className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                method === "paste"
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-gray-200 text-gray-500 hover:text-gray-700"
              }`}
            >
              Вставить ключ
            </button>
            <button
              type="button"
              onClick={() => { setMethod("password"); setError(null); }}
              className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                method === "password"
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-gray-200 text-gray-500 hover:text-gray-700"
              }`}
            >
              Пароль
            </button>
          </div>

          {method === "keyfile" ? (
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/json,.json"
                onChange={onFile}
                disabled={busy}
                className="hidden"
              />
              <Button
                type="button"
                variant="outline"
                className="w-full"
                disabled={busy}
                onClick={() => fileInputRef.current?.click()}
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Выбрать lawdocs-key.json
                  </>
                )}
              </Button>
            </div>
          ) : method === "paste" ? (
            <div className="space-y-3">
              <textarea
                value={pastedKey}
                onChange={(e) => setPastedKey(e.target.value)}
                disabled={busy}
                rows={3}
                placeholder="Вставьте приватный ключ (base64)"
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-mono focus:border-primary focus:outline-none"
              />
              <Button
                type="button"
                className="w-full"
                disabled={busy || pastedKey.trim().length === 0}
                onClick={() => run(() => loginViaPrivateKey(pastedKey))}
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Войти по ключу"}
              </Button>
            </div>
          ) : (
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                run(() => loginViaPassword(email, password));
              }}
            >
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={busy}
                placeholder="you@example.com"
                className="w-full h-10 rounded-lg border border-gray-200 px-3 text-sm focus:border-primary focus:outline-none"
              />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={busy}
                placeholder="Пароль аккаунта"
                className="w-full h-10 rounded-lg border border-gray-200 px-3 text-sm focus:border-primary focus:outline-none"
              />
              <Button
                type="submit"
                className="w-full"
                disabled={busy || email.trim().length === 0 || password.length === 0}
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Войти по паролю"}
              </Button>
            </form>
          )}

          {error && <p className="text-sm text-red-600 text-center">{error}</p>}

          <p className="text-xs text-gray-400 text-center">
            Потеряли ключ?{" "}
            <Link href="/login" className="text-blue-600 hover:underline">
              Войдите по email
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
