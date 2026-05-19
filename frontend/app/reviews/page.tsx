"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Star, ChevronRight } from "lucide-react";
import { SITUATIONS, type SituationId } from "@/lib/situations";

interface Review {
  id: string;
  rating: number;
  text: string;
  name: string | null;
  city: string | null;
  completed_orders_count: number;
  created_at: string;
  situation_id: string;
}

const SITUATION_LABELS: Partial<Record<SituationId, string>> = Object.fromEntries(
  SITUATIONS.filter((s) => s.id !== "other").map((s) => [s.id, s.title])
) as Partial<Record<SituationId, string>>;

function relativeTime(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return "только что";
  if (diff < 3600) return `${Math.floor(diff / 60)} мин. назад`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч. назад`;
  const days = Math.floor(diff / 86400);
  if (days === 1) return "вчера";
  if (days < 30) return `${days} дн. назад`;
  if (days < 365) return `${Math.floor(days / 30)} мес. назад`;
  return `${Math.floor(days / 365)} г. назад`;
}

function StarRow({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star
          key={s}
          className={`h-4 w-4 ${s <= rating ? "fill-yellow-400 text-yellow-400" : "text-gray-200"}`}
        />
      ))}
    </div>
  );
}

function ReviewCard({ review }: { review: Review }) {
  const [expanded, setExpanded] = useState(false);
  const long = review.text.length > 200;
  const displayText = expanded || !long ? review.text : review.text.slice(0, 200) + "…";
  const displayName = review.name ?? "Анонимно";
  const situationTitle = SITUATION_LABELS[review.situation_id as SituationId];

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-gray-900 text-sm">{displayName}</p>
          {review.city && <p className="text-xs text-gray-400 mt-0.5">{review.city}</p>}
        </div>
        <StarRow rating={review.rating} />
      </div>

      {situationTitle && (
        <span className="inline-block text-xs text-primary bg-primary/8 rounded-full px-2.5 py-0.5 w-fit">
          {situationTitle}
        </span>
      )}

      <p className="text-sm text-gray-600 leading-relaxed">
        {displayText}
        {long && !expanded && (
          <button
            onClick={() => setExpanded(true)}
            className="ml-1 text-primary hover:underline text-sm font-medium"
          >
            Читать полностью →
          </button>
        )}
      </p>

      <div className="flex items-center justify-between text-xs text-gray-400 pt-1 border-t border-gray-50">
        <span>✓ {review.completed_orders_count} {review.completed_orders_count === 1 ? "заказ" : "заказа"}</span>
        <span>{relativeTime(review.created_at)}</span>
      </div>
    </div>
  );
}

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [activeSituation, setActiveSituation] = useState<string>("all");

  const situations = SITUATIONS.filter((s) => s.id !== "other");

  async function fetchReviews(newPage: number, situation: string, replace: boolean) {
    const params = new URLSearchParams({ page: String(newPage), limit: "12" });
    if (situation !== "all") params.set("situation", situation);
    const res = await fetch(`/api/reviews?${params}`);
    if (!res.ok) return;
    const data = await res.json();
    setReviews((prev) => (replace ? data.reviews : [...prev, ...data.reviews]));
    setTotal(data.total);
    setPage(newPage);
  }

  useEffect(() => {
    setLoading(true);
    fetchReviews(1, activeSituation, true).finally(() => setLoading(false));
  }, [activeSituation]);

  async function handleLoadMore() {
    setLoadingMore(true);
    await fetchReviews(page + 1, activeSituation, false);
    setLoadingMore(false);
  }

  const hasMore = reviews.length < total;

  return (
    <>
      <nav className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-1 text-sm text-gray-500">
          <Link href="/" className="hover:text-gray-900 transition-colors">Главная</Link>
          <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
          <span className="text-gray-900 font-medium">Отзывы</span>
        </div>
      </nav>

      <main className="min-h-screen bg-gray-50 py-10 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-1">Отзывы клиентов</h1>
            <p className="text-gray-500 text-sm">Смотрите, что думают люди, которые уже использовали LawDocs</p>
          </div>

          {/* Фильтр по ситуациям */}
          <div className="flex flex-wrap gap-2 mb-8">
            <button
              onClick={() => setActiveSituation("all")}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors duration-150 ${
                activeSituation === "all"
                  ? "bg-gray-900 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:border-gray-400 hover:text-gray-900"
              }`}
            >
              Все
            </button>
            {situations.map((s) => (
              <button
                key={s.id}
                onClick={() => setActiveSituation(s.id)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors duration-150 ${
                  activeSituation === s.id
                    ? "bg-gray-900 text-white"
                    : "bg-white border border-gray-200 text-gray-600 hover:border-gray-400 hover:text-gray-900"
                }`}
              >
                {s.title}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="text-center py-20 text-gray-400 text-sm">Загружаем отзывы…</div>
          ) : reviews.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-gray-400 text-sm">Отзывов пока нет</p>
              <p className="text-gray-400 text-xs mt-1">Будьте первым после завершения заказа</p>
            </div>
          ) : (
            <>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
                {reviews.map((r) => (
                  <ReviewCard key={r.id} review={r} />
                ))}
              </div>

              {hasMore && (
                <div className="text-center mt-8">
                  <button
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="px-6 py-2.5 rounded-xl border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:border-gray-400 hover:text-gray-900 transition-colors disabled:opacity-50"
                  >
                    {loadingMore ? "Загружаем…" : `Показать ещё (${total - reviews.length})`}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </>
  );
}
