"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Star, ArrowRight } from "lucide-react";

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
          className={`h-3.5 w-3.5 ${s <= rating ? "fill-yellow-400 text-yellow-400" : "text-gray-200"}`}
        />
      ))}
    </div>
  );
}

function ReviewCard({ review }: { review: Review }) {
  const displayName = review.name ?? "Анонимно";
  const truncated = review.text.length > 180 ? review.text.slice(0, 180) + "…" : review.text;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm flex flex-col gap-3 min-w-[260px] max-w-[300px] shrink-0">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-gray-900">{displayName}</p>
          {review.city && <p className="text-xs text-gray-400">{review.city}</p>}
        </div>
        <StarRow rating={review.rating} />
      </div>
      <p className="text-sm text-gray-600 leading-relaxed flex-1">{truncated}</p>
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>✓ {review.completed_orders_count} {review.completed_orders_count === 1 ? "заказ" : "заказа"}</span>
        <span>{relativeTime(review.created_at)}</span>
      </div>
    </div>
  );
}

export function ReviewsCarousel() {
  const [reviews, setReviews] = useState<Review[]>([]);

  useEffect(() => {
    fetch("/api/reviews?limit=6")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.reviews) setReviews(data.reviews);
      })
      .catch(() => {});
  }, []);

  if (reviews.length === 0) return null;

  return (
    <section className="py-14 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">Отзывы клиентов</h2>
          <Link
            href="/reviews"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
          >
            Все отзывы
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        <div className="flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-hide">
          {reviews.map((r) => (
            <div key={r.id} className="snap-start">
              <ReviewCard review={r} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
