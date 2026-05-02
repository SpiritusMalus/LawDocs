import { notFound } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight, FileText, Scale, Send, ArrowRight } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { SITUATION_PAGES, getSituationPage } from "@/lib/situation-pages";
import { SituationLeadForm } from "@/components/landing/situation-lead-form";
import type { SituationId } from "@/lib/situations";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://lawdocs.ru";

// Use RegExp constructor to avoid file-encoding issues with U+2028/U+2029 literals
const UNSAFE_RE = new RegExp("[<>&\\u2028\\u2029]", "g");
function safeJson(v: unknown): string {
  return JSON.stringify(v).replace(UNSAFE_RE, (c) =>
    "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0")
  );
}

export function generateStaticParams() {
  return SITUATION_PAGES.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = getSituationPage(slug);
  if (!page) return {};
  return {
    title: page.seoTitle,
    description: page.seoDescription,
    alternates: { canonical: `${SITE_URL}/situations/${slug}` },
  };
}

export default async function SituationPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = getSituationPage(slug);
  if (!page) notFound();

  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Главная", item: SITE_URL },
      {
        "@type": "ListItem",
        position: 2,
        name: page.h1,
        item: `${SITE_URL}/situations/${page.slug}`,
      },
    ],
  };

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: page.faq.map(({ q, a }) => ({
      "@type": "Question",
      name: q,
      acceptedAnswer: { "@type": "Answer", text: a },
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: safeJson(breadcrumbJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: safeJson(faqJsonLd) }}
      />

      {/* Breadcrumb */}
      <nav aria-label="Хлебные крошки" className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-1 text-sm text-gray-500">
          <Link href="/" className="hover:text-gray-900 transition-colors">
            Главная
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
          <span className="text-gray-900 font-medium truncate">{page.h1}</span>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-white py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-5 leading-tight tracking-tight">
            {page.h1}
          </h1>
          <p className="text-lg text-gray-600 leading-relaxed mb-8 max-w-2xl">
            {page.leadIn}
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href={`/wizard/${page.slug}`}
              className={buttonVariants({ size: "lg" }) + " h-12 px-8 text-base"}
            >
              Получить документ — 500&nbsp;₽
              <ArrowRight className="h-4 w-4 ml-2" />
            </Link>
            <Link
              href="/situations"
              className={
                buttonVariants({ size: "lg", variant: "outline" }) + " h-12 px-6 text-base"
              }
            >
              Другие ситуации
            </Link>
          </div>
          <p className="mt-4 text-sm text-gray-400">
            Заявку отправляете бесплатно. Счёт пришлём после согласования деталей.
          </p>
        </div>
      </section>

      {/* Deliverables */}
      <section className="bg-gray-50 py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Что вы получите</h2>
          <p className="text-gray-500 mb-8">
            Комплект документов, готовых к отправке, — за 500&nbsp;₽.
          </p>
          <div className="grid md:grid-cols-3 gap-5">
            {page.deliverables.map(({ title, desc }) => (
              <div
                key={title}
                className="bg-white rounded-2xl border border-gray-100 p-6"
              >
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
                  <FileText className="h-5 w-5" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Legal Basis */}
      <section className="bg-white py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Законодательная база</h2>
          <p className="text-gray-500 mb-8">
            Документ составляется со ссылками на конкретные статьи — не шаблонный текст.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {page.legalBasis.map(({ article, description }) => (
              <div
                key={article}
                className="flex gap-4 items-start bg-gray-50 rounded-xl border border-gray-100 p-4"
              >
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 mt-0.5">
                  <Scale className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-semibold text-sm text-gray-900 mb-0.5">{article}</div>
                  <div className="text-sm text-gray-500">{description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Send To strip */}
      <section className="bg-blue-50 py-10 px-4">
        <div className="max-w-5xl mx-auto flex gap-4 items-start">
          <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
            <Send className="h-5 w-5" />
          </div>
          <div>
            <div className="font-semibold text-gray-900 mb-1">Куда направляется документ</div>
            <div className="text-gray-600 text-sm">{page.sendTo}</div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-white py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-8">
            Часто задаваемые вопросы
          </h2>
          <div className="space-y-4">
            {page.faq.map(({ q, a }) => (
              <div key={q} className="border border-gray-100 rounded-xl p-6">
                <h3 className="font-semibold text-gray-900 mb-3">{q}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Lead Form */}
      <SituationLeadForm defaultSituation={page.slug as SituationId} />
    </>
  );
}
