"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { ARTICLES, ARTICLE_CATEGORIES, type ArticleCategory } from "@/lib/articles";

function ArticleCard({ article }: { article: typeof ARTICLES[0] }) {
  return (
    <Link
      href={`/articles/${article.id}`}
      className="group bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-lg hover:bg-gray-50 hover:-translate-y-0.5 transition-all duration-150 flex flex-col"
    >
      <div className="flex items-start gap-3 mb-3">
        <span className="text-2xl">{ARTICLE_CATEGORIES[article.category].icon}</span>
        <h3 className="text-base font-semibold text-gray-900 group-hover:text-primary leading-snug pt-1">
          {article.title}
        </h3>
      </div>
      <p className="text-sm text-gray-600 mb-4 flex-1">{article.description}</p>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">{article.readTime} мин чтения</span>
        <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full group-hover:bg-primary/10 group-hover:text-primary transition-colors">
          {ARTICLE_CATEGORIES[article.category].label}
        </span>
      </div>
    </Link>
  );
}

export function ArticlesGrid() {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<ArticleCategory | null>(null);

  const filtered = useMemo(() => {
    let items = ARTICLES;
    if (activeCategory) {
      items = items.filter((a) => a.category === activeCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (a) => a.title.toLowerCase().includes(q) || a.description.toLowerCase().includes(q)
      );
    }
    return items;
  }, [search, activeCategory]);

  return (
    <>
      {/* Search + category tabs */}
      <section className="bg-white border-b border-gray-100 px-4 py-8">
        <div className="max-w-screen-xl mx-auto space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Найти статью (например, претензия или залог)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-12 pr-4 h-11 border border-gray-200 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {activeCategory && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Категория:</span>
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 border border-blue-100 rounded-full text-sm text-blue-700">
                {ARTICLE_CATEGORIES[activeCategory].icon} {ARTICLE_CATEGORIES[activeCategory].label}
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
              {Object.entries(ARTICLE_CATEGORIES).map(([catId, cat]) => (
                <button
                  key={catId}
                  onClick={() => setActiveCategory(catId as ArticleCategory)}
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

      {/* Articles grid */}
      <section className="bg-gray-50 px-4 py-12">
        <div className="max-w-screen-xl mx-auto">
          {filtered.length === 0 ? (
            <p className="text-center text-gray-400 py-12">Статей не найдено</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
