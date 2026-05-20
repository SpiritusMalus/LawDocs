import Link from "next/link";
import { CheckCircle, ArrowRight } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { ScrollReveal } from "@/components/ui/scroll-reveal";

const INCLUDED = [
  "Претензия в форматах .docx и .pdf",
  "Расчёт неустойки или процентов, если применимо",
  "Инструкция: реальные контакты компании, куда отправить, сроки",
  "Ссылки на законы — читать прямо в КонсультантПлюс",
  "Гарантия возврата 199 ₽ за 7 дней, если не подойдёт",
];

export function Pricing() {
  return (
    <section className="bg-white py-24 px-4">
      <div className="max-w-(--l-content-narrow) mx-auto">
        <ScrollReveal>
          <div className="mb-(--l-section-heading-narrow)">
            <h2 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight">
              Прозрачная цена
            </h2>
            <p className="text-gray-500 text-lg max-w-xl">
              Платите один раз за результат, без подписок и скрытых комиссий.
            </p>
          </div>
        </ScrollReveal>

        <ScrollReveal delay={100}>
          <div className="rounded-3xl border-2 border-primary/20 overflow-hidden">
            {/* Top accent */}
            <div className="h-1 bg-gradient-to-r from-blue-600 via-blue-500 to-indigo-500" />

            <div className="p-8 md:p-10">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-8 pb-8 border-b border-gray-100">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-1">
                    Один готовый документ
                  </h3>
                  <p className="text-sm text-gray-500">
                    Любая из 25 типовых ситуаций
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500 line-through mb-1">Юрист — от 5&nbsp;000&nbsp;₽</div>
                  <div className="text-5xl font-bold text-gray-900">199&nbsp;<span className="text-primary">₽</span></div>
                  <div className="text-xs text-gray-400 mt-1">разовая оплата, без подписок</div>
                </div>
              </div>

              <ul className="space-y-3">
                {INCLUDED.map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <CheckCircle className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                    <span className="text-sm text-gray-700">{item}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-8 pt-8 border-t border-gray-100">
                <Link
                  href="/situations"
                  className={buttonVariants({ size: "lg" }) + " w-full h-12 text-base"}
                >
                  Получить документ
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Link>
              </div>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
