import { CheckCircle, XCircle } from "lucide-react";
import { ScrollReveal } from "@/components/ui/scroll-reveal";

const POINTS = [
  {
    yes: "Реальные шаблоны из юридической практики",
    no: "Придумывает структуру документа на лету",
  },
  {
    yes: "Расчёт неустойки по формуле из ЗоЗПП — автоматически",
    no: "Считает «на глаз», может ошибиться со статьями",
  },
  {
    yes: "Прямые ссылки на статьи в КонсультантПлюс — можно проверить",
    no: "Может сослаться на статью, которой не существует",
  },
  {
    yes: "Готовый .docx и .pdf — распечатал, подписал, отнёс",
    no: "Сырой текст — придётся переформатировать",
  },
];

export function WhyNotChatGPT() {
  return (
    <section className="bg-gray-50 border-y border-gray-100 py-24 px-4">
      <div className="max-w-(--l-content) mx-auto">
        <ScrollReveal>
          <div className="mb-(--l-section-heading)">
            <div className="inline-flex items-center gap-2 text-xs font-semibold text-primary bg-primary/8 border border-primary/15 px-3 py-1.5 rounded-full mb-6">
              Главный вопрос
            </div>
            <h2 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight">
              А чем это лучше ChatGPT?
            </h2>
            <p className="text-gray-500 text-lg max-w-xl">
              Если коротко — ChatGPT отвечает на вопрос. Мы выдаём документ,
              готовый к отправке.
            </p>
          </div>
        </ScrollReveal>

        <ScrollReveal delay={100}>
          <div className="rounded-2xl overflow-hidden border border-gray-200 shadow-sm">
            <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-200">
              {/* LawDocs — светлая сторона с синим акцентом */}
              <div className="bg-white p-6 md:p-8">
                <div className="inline-flex items-center gap-2 text-sm font-semibold text-primary mb-6">
                  <CheckCircle className="h-4 w-4" />
                  LawDocs
                </div>
                <ul className="space-y-4">
                  {POINTS.map((p) => (
                    <li key={p.yes} className="flex items-start gap-3">
                      <CheckCircle className="h-4 w-4 text-emerald-500 mt-1 shrink-0" />
                      <span className="text-sm text-gray-800 leading-relaxed font-medium">{p.yes}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* ChatGPT — приглушённая сторона */}
              <div className="bg-gray-50 p-6 md:p-8">
                <div className="inline-flex items-center gap-2 text-sm font-semibold text-gray-400 mb-6">
                  <XCircle className="h-4 w-4" />
                  Универсальный AI
                </div>
                <ul className="space-y-4">
                  {POINTS.map((p) => (
                    <li key={p.no} className="flex items-start gap-3">
                      <XCircle className="h-4 w-4 text-gray-300 mt-1 shrink-0" />
                      <span className="text-sm text-gray-400 leading-relaxed">{p.no}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
