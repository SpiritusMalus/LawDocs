"use client";

import { useState } from "react";
import { Search, Mail } from "lucide-react";
import { SITUATIONS, type SituationId } from "@/lib/situations";
import { SituationCard } from "@/components/situation-card";

type CategoryId =
  | "all"
  | "consumer"
  | "banking"
  | "labor"
  | "housing"
  | "transport"
  | "insurance"
  | "legal";

const CATEGORIES: { id: CategoryId; label: string }[] = [
  { id: "all", label: "Все" },
  { id: "consumer", label: "Потребитель" },
  { id: "housing", label: "Жильё" },
  { id: "transport", label: "Транспорт" },
  { id: "banking", label: "Банк" },
  { id: "insurance", label: "Страховая" },
  { id: "labor", label: "Работа" },
  { id: "legal", label: "Суд и долги" },
];

const SITUATION_CATEGORY: Record<SituationId, CategoryId> = {
  shop: "consumer",
  marketplace: "consumer",
  online_course: "consumer",
  gym_refund: "consumer",
  tour_operator: "consumer",
  medical: "consumer",
  telecom: "consumer",
  bank: "banking",
  bank_block: "banking",
  employer: "labor",
  utility: "housing",
  rental_deposit: "housing",
  neighbor_flood: "housing",
  repair: "housing",
  ddu_delay: "housing",
  ddu_defects: "housing",
  ddu_termination: "housing",
  airline: "transport",
  gibdd: "transport",
  auto_repair: "transport",
  carsharing: "transport",
  insurance: "insurance",
  dtp_osago: "insurance",
  court_order: "legal",
  debt_collector: "legal",
  other: "consumer",
};

export function SituationsGrid() {
  const [activeCategory, setActiveCategory] = useState<CategoryId>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const query = searchQuery.trim().toLowerCase();
  const filtered = SITUATIONS.filter((s) => {
    if (s.id === "other") return false;
    if (activeCategory !== "all" && SITUATION_CATEGORY[s.id] !== activeCategory) return false;
    if (query) {
      return (
        s.title.toLowerCase().includes(query) ||
        s.blurb.toLowerCase().includes(query) ||
        s.examples.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const showGrouped = activeCategory === "all" && !query;

  return (
    <section className="bg-gray-50 py-12 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Search */}
        <div className="relative mb-5">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <input
            type="search"
            placeholder="Найти ситуацию..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-colors"
          />
        </div>

        {/* Category chips */}
        <div className="flex flex-wrap gap-2 mb-8 items-center">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors duration-150 ${
                activeCategory === cat.id
                  ? "bg-gray-900 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:border-gray-400 hover:text-gray-900"
              }`}
            >
              {cat.label}
            </button>
          ))}
          <a
            href="mailto:lawdocsru@gmail.com"
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium border border-dashed border-gray-300 text-gray-500 hover:border-gray-500 hover:text-gray-700 transition-colors duration-150 whitespace-nowrap"
          >
            <Mail className="h-3.5 w-3.5" />
            Не вижу свою ситуацию
          </a>
        </div>

        {/* Empty state */}
        {filtered.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">Ничего не найдено</p>
            <a
              href="mailto:lawdocsru@gmail.com"
              className="mt-3 inline-block text-sm text-primary hover:underline"
            >
              Написать нам — подберём вариант
            </a>
          </div>
        )}

        {/* Grouped view: H2 per category when "All" selected with no search */}
        {showGrouped ? (
          <div className="space-y-10">
            {CATEGORIES.filter((cat) => cat.id !== "all").map((cat) => {
              const catSituations = filtered.filter(
                (s) => SITUATION_CATEGORY[s.id] === cat.id
              );
              if (catSituations.length === 0) return null;
              return (
                <div key={cat.id}>
                  <h2 className="text-xl font-bold text-gray-900 mb-4">
                    {cat.label}
                  </h2>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {catSituations.map((s) => (
                      <SituationCard key={s.id} situation={s} variant="list" showLegal />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Flat filtered view: searching or category selected */
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map((s) => (
              <SituationCard key={s.id} situation={s} variant="list" showLegal />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
