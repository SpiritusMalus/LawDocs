"use client";

import { useState, useEffect, useTransition } from "react";
import { Eye, EyeOff, Star, LogIn } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface Review {
  id: string;
  order_id: string;
  user_id: string;
  situation_id: string;
  rating: number;
  text: string;
  name: string | null;
  city: string | null;
  completed_orders_count: number;
  is_hidden: boolean;
  created_at: string;
}

const SESSION_KEY = "admin_secret";

export default function AdminReviewsPage() {
  const [secret, setSecret] = useState("");
  const [authed, setAuthed] = useState(false);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const saved = sessionStorage.getItem(SESSION_KEY);
    if (saved) {
      setSecret(saved);
      loadReviews(saved);
    }
  }, []);

  async function loadReviews(s: string) {
    setError(null);
    const res = await fetch("/api/admin/reviews", {
      headers: { "X-Admin-Secret": s },
    });
    if (res.status === 403) {
      setError("Неверный пароль");
      sessionStorage.removeItem(SESSION_KEY);
      return;
    }
    if (!res.ok) {
      setError("Ошибка загрузки");
      return;
    }
    const data = (await res.json()) as Review[];
    setReviews(data);
    setAuthed(true);
    sessionStorage.setItem(SESSION_KEY, s);
  }

  function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    startTransition(() => loadReviews(secret));
  }

  function toggleVisibility(id: string) {
    startTransition(async () => {
      const res = await fetch(`/api/admin/reviews/${id}`, {
        method: "PATCH",
        headers: { "X-Admin-Secret": secret },
      });
      if (!res.ok) return;
      const updated = (await res.json()) as Review;
      setReviews((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    });
  }

  if (!authed) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl border border-gray-100 p-8 w-full max-w-sm">
          <h1 className="text-xl font-bold text-gray-900 mb-6">Модерация отзывов</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <Input
              type="password"
              placeholder="Admin secret"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              autoFocus
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" disabled={isPending || !secret} className="w-full">
              <LogIn className="h-4 w-4 mr-2" />
              {isPending ? "Входим..." : "Войти"}
            </Button>
          </form>
        </div>
      </main>
    );
  }

  const visible = reviews.filter((r) => !r.is_hidden).length;
  const hidden = reviews.filter((r) => r.is_hidden).length;

  return (
    <main className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Отзывы</h1>
          <p className="text-sm text-gray-500">
            {visible} показано · {hidden} скрыто
          </p>
        </div>

        {reviews.length === 0 && (
          <p className="text-gray-400 text-center py-16">Отзывов пока нет</p>
        )}

        <div className="flex flex-col gap-3">
          {reviews.map((review) => (
            <div
              key={review.id}
              className={`bg-white rounded-xl border p-5 flex gap-4 ${
                review.is_hidden ? "opacity-50 border-gray-100" : "border-gray-200"
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm text-gray-900">
                    {review.name ?? "Аноним"}
                  </span>
                  {review.city && (
                    <span className="text-xs text-gray-400">{review.city}</span>
                  )}
                  <span className="flex items-center gap-0.5 text-yellow-500 text-xs ml-auto">
                    <Star className="h-3.5 w-3.5 fill-current" />
                    {review.rating}
                  </span>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed break-words">
                  {review.text}
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  {review.situation_id} ·{" "}
                  {new Date(review.created_at).toLocaleDateString("ru-RU")}
                </p>
              </div>
              <button
                onClick={() => toggleVisibility(review.id)}
                disabled={isPending}
                title={review.is_hidden ? "Показать" : "Скрыть"}
                className="flex-shrink-0 p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-700 disabled:opacity-40"
              >
                {review.is_hidden ? (
                  <Eye className="h-5 w-5" />
                ) : (
                  <EyeOff className="h-5 w-5" />
                )}
              </button>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
