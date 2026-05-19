"use client";

import { useEffect, useState } from "react";
import { Star, Loader2, CheckCircle } from "lucide-react";

interface UserMe {
  id: string;
  email: string;
  name: string | null;
  completed_orders_count: number;
}

interface ExistingReview {
  id: string;
  rating: number;
  text: string;
  name: string | null;
  city: string | null;
}

interface ReviewFormProps {
  orderId: string;
  situationId: string;
}

function StarRating({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  const [hovered, setHovered] = useState(0);

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          className="focus:outline-none"
          aria-label={`${star} звезд`}
        >
          <Star
            className={`h-7 w-7 transition-colors ${
              star <= (hovered || value)
                ? "fill-yellow-400 text-yellow-400"
                : "text-gray-300"
            }`}
          />
        </button>
      ))}
    </div>
  );
}

export function ReviewForm({ orderId, situationId }: ReviewFormProps) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserMe | null>(null);
  const [existing, setExisting] = useState<ExistingReview | null | false>(false);

  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [useProfileName, setUseProfileName] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/user/me").then((r) => (r.ok ? r.json() : null)),
      fetch(`/api/reviews/my?order_id=${orderId}`).then((r) => (r.ok ? r.json() : null)),
    ]).then(([me, review]) => {
      setUser(me);
      setExisting(review ?? null);
      setLoading(false);
    });
  }, [orderId]);

  useEffect(() => {
    if (useProfileName && user?.name) {
      setName(user.name);
    }
  }, [useProfileName, user]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating === 0) {
      setError("Пожалуйста, выберите оценку.");
      return;
    }
    if (text.trim().length < 50) {
      setError("Отзыв должен быть не менее 50 символов.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: orderId,
          rating,
          text: text.trim(),
          name: name.trim() || null,
          city: city.trim() || null,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Не удалось отправить отзыв. Попробуйте позже.");
        return;
      }
      setSubmitted(true);
    } catch {
      setError("Не удалось связаться с сервером.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return null;

  if (existing) {
    return (
      <div className="pt-2 text-center text-sm text-gray-500">
        <CheckCircle className="h-5 w-5 text-green-500 mx-auto mb-1" />
        Спасибо за отзыв!
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="pt-4 text-center">
        <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
        <p className="font-medium text-gray-900">Спасибо! Отзыв опубликован.</p>
        <p className="text-sm text-gray-500 mt-1">Он виден другим пользователям.</p>
      </div>
    );
  }

  if (user && user.completed_orders_count === 0) {
    return (
      <div className="pt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500 text-center">
        Отзывы могут оставлять только покупатели.
        <br />
        Оставьте отзыв после первой успешной покупки.
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="pt-4 space-y-4">
      <p className="text-sm font-medium text-gray-700">Оставьте отзыв</p>

      {/* Stars */}
      <div className="flex flex-col gap-1">
        <span className="text-xs text-gray-500">Оценка</span>
        <StarRating value={rating} onChange={setRating} />
      </div>

      {/* Text */}
      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-500">
          Ваш отзыв <span className="text-gray-400">(50–1000 символов)</span>
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          maxLength={1000}
          placeholder="Расскажите, как всё прошло..."
          className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 resize-none transition-colors"
        />
        <span className="text-xs text-gray-400 text-right">{text.length}/1000</span>
      </div>

      {/* Name */}
      <div className="flex flex-col gap-1.5">
        <label className="text-xs text-gray-500">Имя <span className="text-gray-400">(необязательно)</span></label>
        <input
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setUseProfileName(false);
          }}
          maxLength={100}
          placeholder="Анонимно"
          disabled={useProfileName}
          className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-colors disabled:bg-gray-50 disabled:text-gray-500"
        />
        <label className={`flex items-center gap-2 text-xs cursor-pointer ${!user?.name ? "opacity-40 cursor-not-allowed" : ""}`}>
          <input
            type="checkbox"
            checked={useProfileName}
            disabled={!user?.name}
            onChange={(e) => setUseProfileName(e.target.checked)}
            className="accent-primary"
          />
          Взять имя из профиля
          {!user?.name && <span className="text-gray-400">(не указано)</span>}
        </label>
      </div>

      {/* City */}
      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-500">Город <span className="text-gray-400">(необязательно)</span></label>
        <input
          type="text"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          maxLength={50}
          placeholder="Москва"
          className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-colors"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full h-10 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Отправляем…
          </>
        ) : (
          "Отправить отзыв"
        )}
      </button>
    </form>
  );
}
