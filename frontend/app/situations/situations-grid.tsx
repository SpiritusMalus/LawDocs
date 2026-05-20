"use client";

import { useState, useMemo } from "react";
import { Search } from "lucide-react";
import { SITUATIONS, CATEGORIES } from "@/lib/situations";
import { SituationCard } from "@/components/situation-card";

export function SituationsGrid() {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return SITUATIONS;
    const q = search.toLowerCase();
    return SITUATIONS.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.blurb.toLowerCase().includes(q)
    );
  }, [search]);

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
      {/* Search */}
      <section className="bg-white border-b border-gray-100 px-4 py-8">
        <div className="max-w-5xl mx-auto">
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
                  <span>{cat.icon}</span> {cat.label} ({items.length})
                </h2>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((s) => (
                    <SituationCard key={s.id} situation={s} variant="dark" />
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
