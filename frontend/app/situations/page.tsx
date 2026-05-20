"use client";

import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight, Search } from "lucide-react";
import { SITUATIONS, CATEGORIES } from "@/lib/situations";
import { SituationCard } from "@/components/situation-card";
import { useState, useMemo } from "react";

export const metadata: Metadata = {
  title: "Все ситуации — юридические документы за 199 ₽ | LawDocs",
  description:
    "Все ситуации — 25 готовых юридических документов: претензии в магазин, банк, маркетплейс, страховую, УК и другие. 199 ₽.",
};

export default function SituationsPage() {
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
      {/* Breadcrumb */}
      <nav aria-label="Хлебные крошки" className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-1 text-sm text-gray-500">
          <Link href="/" className="hover:text-gray-900 transition-colors">
            Главная
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
          <span className="text-gray-900 font-medium">Все ситуации</span>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-gray-900 py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 leading-tight tracking-tight">
            Все ситуации
          </h1>
          <p className="text-lg text-gray-400 max-w-xl mx-auto">
            25 готовых шаблонов. Каждая претензия — со ссылками на конкретные статьи закона.{" "}
            <span className="font-medium text-gray-200">199&nbsp;₽ за документ.</span>
          </p>
        </div>
      </section>

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
        </div>
      </section>
    </>
  );
}
