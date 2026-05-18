import { CheckCircle } from "lucide-react";
import { ScrollReveal } from "@/components/ui/scroll-reveal";

const INCLUDED = [
  "Претензия в форматах .docx и .pdf",
  "Расчёт неустойки или процентов, если применимо",
  "Инструкция: реальные контакты компании, куда отправить, сроки",
  "Ссылки на законы — читать прямо в КонсультантПлюс",
  "Возврат денег, если документ вам не подойдёт",
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
          <div className="bg-gray-900 rounded-3xl overflow-hidden shadow-2xl">
            {/* Top accent line */}
            <div className="h-1 bg-gradient-to-r from-blue-500 via-blue-400 to-indigo-500" />

            <div className="p-8 md:p-10">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-8 pb-8 border-b border-gray-800">
                <div>
                  <h3 className="text-xl font-semibold text-white mb-1">
                    Один готовый документ
                  </h3>
                  <p className="text-sm text-gray-400">
                    Любая из 25 типовых ситуаций
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-5xl font-bold text-white">199&nbsp;<span className="text-blue-400">₽</span></div>
                  <div className="text-xs text-gray-500 mt-1">разовая оплата</div>
                </div>
              </div>

              <ul className="space-y-4">
                {INCLUDED.map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <CheckCircle className="h-5 w-5 text-blue-400 mt-0.5 shrink-0" />
                    <span className="text-sm text-gray-300">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
