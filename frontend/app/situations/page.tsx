import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ChevronRight } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { SITUATIONS } from "@/lib/situations";
import { getSituationPage } from "@/lib/situation-pages";

export const metadata: Metadata = {
  title: "Все ситуации — юридические документы за 199 ₽ | LawDocs",
  description:
    "Претензии и жалобы для 7 типовых ситуаций: магазин, маркетплейс, банк, работодатель, страховая, УК, авиакомпания. Готовый документ со ссылками на законы.",
};

const SITUATION_EMOJI: Record<string, string> = {
  shop: "🛒",
  marketplace: "📦",
  bank: "🏦",
  employer: "💼",
  insurance: "🚗",
  utility: "🏠",
  airline: "✈️",
  other: "📋",
};

export default function SituationsPage() {
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
      <section className="bg-white py-14 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 leading-tight tracking-tight">
            С какими ситуациями работаем
          </h1>
          <p className="text-lg text-gray-500 max-w-xl mx-auto">
            Семь типовых случаев, которые покрывают большинство обращений.
            Каждый документ — со ссылками на конкретные статьи законов.{" "}
            <span className="font-medium text-gray-700">199&nbsp;₽.</span>
          </p>
        </div>
      </section>

      {/* Cards */}
      <section className="bg-gray-50 py-12 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {SITUATIONS.filter((s) => s.id !== "other").map((s) => {
              const page = getSituationPage(s.id);
              const emoji = SITUATION_EMOJI[s.id] ?? "📋";
              return (
                <Link
                  key={s.id}
                  href={`/situations/${s.id}`}
                  className="group bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md hover:border-blue-200 transition-all flex flex-col"
                >
                  <div className="text-3xl mb-4">{emoji}</div>
                  <h2 className="font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                    {s.title}
                  </h2>
                  <p className="text-sm text-gray-500 leading-relaxed mb-4 flex-1">{s.blurb}</p>
                  {page && (
                    <p className="text-xs text-gray-400 mb-4 leading-relaxed">
                      {page.legalBasis
                        .slice(0, 2)
                        .map((l) => l.article)
                        .join(" · ")}
                    </p>
                  )}
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600">
                    Оформить документ
                    <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-white py-14 px-4">
        <div className="max-w-xl mx-auto text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            Не нашли свою ситуацию?
          </h2>
          <p className="text-gray-500 mb-8">
            Опишите проблему в свободной форме — посмотрим, чем можем помочь.
          </p>
          <a
            href="mailto:lawdocsru@gmail.com"
            className={buttonVariants({ size: "lg" }) + " h-12 px-8 text-base"}
          >
            Написать нам
            <ArrowRight className="h-4 w-4 ml-2" />
          </a>
        </div>
      </section>
    </>
  );
}
