"use client";

import React, { useState, useMemo } from "react";
import { Search } from "lucide-react";
import { SITUATIONS, CATEGORIES, type SituationCategory } from "@/lib/situations";
import { SituationCard } from "@/components/situation-card";

export function SituationsGrid() {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<SituationCategory | null>(null);

  const filtered = useMemo(() => {
    let items = SITUATIONS;
    if (activeCategory) {
      items = items.filter((s) => s.category === activeCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (s) =>
          s.title.toLowerCase().includes(q) ||
          s.blurb.toLowerCase().includes(q)
      );
    }
    return items;
  }, [search, activeCategory]);

  const grouped = useMemo(() => {
    const result: Record<string, typeof filtered> = {};
    filtered.forEach((s) => {
      if (!result[s.category]) result[s.category] = [];
      result[s.category].push(s);
    });
    return result;
  }, [filtered]);

  return (
    <>
      {/* Search + category tabs */}
      <section className="bg-white border-b border-gray-100 px-4 py-8">
        <div className="max-w-5xl mx-auto space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Найти ситуацию (например, wildberries или ЖКХ)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {activeCategory && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Поиск в:</span>
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 border border-blue-100 rounded-full text-sm text-blue-700">
                {CATEGORIES[activeCategory]?.icon} {CATEGORIES[activeCategory]?.label}
                <button
                  onClick={() => setActiveCategory(null)}
                  className="ml-0.5 text-blue-400 hover:text-blue-600 transition-colors"
                  aria-label="Сбросить категорию"
                >
                  ×
                </button>
              </span>
            </div>
          )}
          <div className="relative">
            <div
              className="flex gap-2 overflow-x-auto whitespace-nowrap pb-1 scrollbar-none"
              style={{ WebkitOverflowScrolling: "touch" } as React.CSSProperties}
            >
              <button
                onClick={() => setActiveCategory(null)}
                className={`shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  activeCategory === null
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                Все
              </button>
              {Object.entries(CATEGORIES).map(([catId, cat]) => (
                <button
                  key={catId}
                  onClick={() => setActiveCategory(catId as SituationCategory)}
                  className={`shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    activeCategory === catId
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {cat.icon} {cat.label}
                </button>
              ))}
            </div>
            <div className="absolute right-0 top-0 h-full w-8 bg-gradient-to-l from-white to-transparent pointer-events-none" />
          </div>
        </div>
      </section>

      {/* Situations by category */}
      <section className="bg-gray-50 px-4 py-12">
        <div className="max-w-5xl mx-auto space-y-12">
          {Object.entries(CATEGORIES).map(([catId, cat]) => {
            const items = grouped[catId] || [];
            if (items.length === 0) return null;
            return (
              <div key={catId}>
                <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                  <span>{cat.icon}</span> {cat.label}
                </h2>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((s) => (
                    <SituationCard key={s.id} situation={s} variant="dark" showLegal />
                  ))}
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <p className="text-center text-gray-400 py-12">Ничего не найдено</p>
          )}
        </div>
      </section>
    </>
  );
}
