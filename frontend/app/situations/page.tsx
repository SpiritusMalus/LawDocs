import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { SituationsGrid } from "./situations-grid";

export const metadata: Metadata = {
  title: "Все ситуации — юридические документы за 199 ₽ | LawDocs",
  description:
    "25 ситуаций: потребитель, работодатель, банк, жильё, транспорт, страховая, ДДУ. Готовые претензии и жалобы со ссылками на законы за 199 ₽.",
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
      <section className="bg-gray-900 py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 leading-tight tracking-tight">
            С какими ситуациями работаем
          </h1>
          <p className="text-lg text-gray-400 max-w-xl mx-auto">
            25 типовых случаев — потребитель, жильё, транспорт, банк, работа.
            Каждый документ со ссылками на конкретные статьи законов.{" "}
            <span className="font-medium text-gray-200">199&nbsp;₽.</span>
          </p>
        </div>
      </section>

      <SituationsGrid />
    </>
  );
}
