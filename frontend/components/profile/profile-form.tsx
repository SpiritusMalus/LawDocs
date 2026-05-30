"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { KeyRotation } from "@/components/profile/key-rotation";

interface ProfileFormProps {
  initialName: string | null;
  email: string;
  processingRestricted: boolean;
}

export function ProfileForm({ initialName, email, processingRestricted }: ProfileFormProps) {
  const [name, setName] = useState(initialName ?? "");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [isDeleting, startDeleteTransition] = useTransition();
  const [isRestricting, startRestrictTransition] = useTransition();
  const [restricted, setRestricted] = useState(processingRestricted);
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

  const [isExporting, startExportTransition] = useTransition();

  function handleDeleteAccount() {
    if (!window.confirm("Удалить аккаунт? Все ваши заказы будут удалены безвозвратно.")) return;
    startDeleteTransition(async () => {
      const res = await fetch("/api/user/me", { method: "DELETE" });
      if (!res.ok) {
        setError("Не удалось удалить аккаунт. Попробуйте ещё раз.");
        return;
      }
      router.push("/");
    });
  }

  function handleRevokeConsent() {
    if (!window.confirm("Отозвать согласие на обработку персональных данных? Аккаунт и все заказы будут удалены безвозвратно.")) return;
    startDeleteTransition(async () => {
      const res = await fetch("/api/user/me", { method: "DELETE" });
      if (!res.ok) {
        setError("Не удалось отозвать согласие. Попробуйте ещё раз.");
        return;
      }
      router.push("/");
    });
  }

  function handleToggleRestriction() {
    const msg = restricted
      ? "Разрешить обработку персональных данных?"
      : "Ограничить обработку персональных данных? Новые заказы станут недоступны до снятия ограничения.";
    if (!window.confirm(msg)) return;
    startRestrictTransition(async () => {
      const res = await fetch("/api/user/restrict-processing", {
        method: restricted ? "DELETE" : "POST",
      });
      if (!res.ok) {
        setError("Не удалось изменить настройку. Попробуйте ещё раз.");
        return;
      }
      setRestricted(!restricted);
    });
  }

  function handleExportData() {
    startExportTransition(async () => {
      const res = await fetch("/api/user/data-export");
      if (!res.ok) {
        setError("Не удалось выгрузить данные. Попробуйте ещё раз.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "my-data.json";
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  return (
    <>
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
    <div className="mt-8 pt-6 border-t border-gray-100 space-y-6">
      <div>
        <p className="text-sm text-gray-500 mb-3">
          {restricted
            ? "Обработка ваших персональных данных ограничена. Новые заказы недоступны."
            : "Вы можете временно ограничить обработку ваших персональных данных (ст. 21 152-ФЗ)."}
        </p>
        <Button
          type="button"
          variant="outline"
          disabled={isRestricting}
          onClick={handleToggleRestriction}
          className={restricted ? "text-green-600 border-green-200 hover:bg-green-50 hover:border-green-300" : ""}
        >
          {isRestricting
            ? "Применяем..."
            : restricted
            ? "Разрешить обработку данных"
            : "Ограничить обработку данных"}
        </Button>
      </div>
      <div>
        <p className="text-sm text-gray-500 mb-3">
          Скачайте копию всех ваших данных, хранящихся на сервисе.
        </p>
        <Button
          type="button"
          variant="outline"
          disabled={isExporting}
          onClick={handleExportData}
        >
          {isExporting ? "Подготавливаем..." : "Скачать мои данные"}
        </Button>
      </div>
      <div>
        <p className="text-sm text-gray-500 mb-3">
          После удаления аккаунта все ваши заказы будут удалены безвозвратно.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button
            type="button"
            variant="outline"
            disabled={isDeleting}
            onClick={handleDeleteAccount}
            className="text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300"
          >
            {isDeleting ? "Удаляем..." : "Удалить аккаунт"}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={isDeleting}
            onClick={handleRevokeConsent}
            className="text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300"
          >
            {isDeleting ? "Отзываем..." : "Отозвать согласие на обработку данных"}
          </Button>
        </div>
      </div>
      <div className="pt-6 border-t border-gray-100">
        <KeyRotation />
      </div>
    </div>
    </>
  );
}
