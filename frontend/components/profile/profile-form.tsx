"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface ProfileFormProps {
  initialName: string | null;
  email: string;
}

export function ProfileForm({ initialName, email }: ProfileFormProps) {
  const [name, setName] = useState(initialName ?? "");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);

    startTransition(async () => {
      const res = await fetch("/api/user/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim() || null }),
      });
      if (!res.ok) {
        setError("Не удалось сохранить. Попробуйте ещё раз.");
        return;
      }
      setSaved(true);
      router.refresh();
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <Label htmlFor="email" className="text-sm text-gray-500 mb-1.5 block">
          Электронная почта
        </Label>
        <Input
          id="email"
          type="email"
          value={email}
          disabled
          className="bg-gray-50 text-gray-500 cursor-not-allowed"
        />
      </div>
      <div>
        <Label htmlFor="name" className="text-sm font-medium mb-1.5 block">
          Имя
        </Label>
        <Input
          id="name"
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setSaved(false);
          }}
          placeholder="Как вас зовут?"
          maxLength={100}
        />
        <p className="text-xs text-gray-400 mt-1.5">
          Отображается в отзывах, если вы их оставляете
        </p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isPending} className="px-6">
          {isPending ? "Сохраняем..." : "Сохранить"}
        </Button>
        {saved && (
          <span className="flex items-center gap-1.5 text-sm text-green-600 font-medium">
            <Check className="h-4 w-4" />
            Сохранено
          </span>
        )}
      </div>
    </form>
  );
}
