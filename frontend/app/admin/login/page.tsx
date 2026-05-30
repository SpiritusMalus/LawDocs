"use client";

import { useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LogIn } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { adminLoginAction } from "../actions";

export default function AdminLoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/admin/dashboard";

  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await adminLoginAction(inputValue);
      if (result.success) {
        router.push(next);
      } else {
        setError(result.error || "Неверный пароль");
      }
    });
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl border border-gray-100 p-8 w-full max-w-sm">
        <h1 className="text-xl font-bold text-gray-900 mb-6">Вход в админку</h1>
        <form onSubmit={handleLogin} className="space-y-4">
          <Input
            type="password"
            placeholder="Admin secret"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            autoFocus
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={isPending || !inputValue} className="w-full">
            <LogIn className="h-4 w-4 mr-2" />
            {isPending ? "Входим..." : "Войти"}
          </Button>
        </form>
      </div>
    </main>
  );
}
