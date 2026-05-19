import { Star } from "lucide-react";

const BACKEND_URL = process.env.BACKEND_URL ?? "";

interface Review {
  id: string;
  rating: number;
  text: string;
  name: string | null;
  city: string | null;
  created_at: string;
}

async function fetchSituationReviews(situationId: string): Promise<Review[]> {
  if (!BACKEND_URL) return [];
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/v1/reviews?situation=${encodeURIComponent(situationId)}&limit=3`,
      { next: { revalidate: 300 } }
    );
    if (!res.ok) return [];
    const data: unknown = await res.json();
    return Array.isArray(data) ? (data as Review[]) : [];
  } catch {
    return [];
  }
}

export async function SituationReviews({ situationId }: { situationId: string }) {
  const reviews = await fetchSituationReviews(situationId);
  if (reviews.length === 0) return null;

  return (
    <section className="bg-gray-50 py-16 px-4 border-t border-gray-100">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-8">Отзывы клиентов</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {reviews.map((r) => (
            <div
              key={r.id}
              className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex flex-col"
            >
              <div className="flex items-center gap-0.5 mb-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    className={`h-4 w-4 ${
                      i < r.rating
                        ? "fill-amber-400 text-amber-400"
                        : "fill-gray-100 text-gray-200"
                    }`}
                  />
                ))}
              </div>
              <p className="text-sm text-gray-700 leading-relaxed flex-1 mb-4">{r.text}</p>
              <p className="text-xs text-gray-400">
                {r.name ?? "Аноним"}
                {r.city ? ` · ${r.city}` : ""}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
