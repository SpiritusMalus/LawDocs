import { CheckCircle, XCircle } from "lucide-react";
import { ScrollReveal } from "@/components/ui/scroll-reveal";

const POINTS = [
  {
    yes: "Знаем форму жалобы в Роспотребнадзор по 2026 году и актуальные реквизиты",
    no: "Может выдумать структуру, которую не примут в ведомстве",
  },
  {
    yes: "Считаем неустойку по правильной формуле (1% за день просрочки по ЗоЗПП и т.д.)",
    no: "Считает «на глаз», часто ошибается с применимыми статьями",
  },
  {
    yes: "Шаблоны проверены практикующим юристом на реальных кейсах",
    no: "Не отвечает за результат, ссылок на статьи может не существовать",
  },
  {
    yes: "Готовый Word — распечатал, подписал, отнёс. Ничего не переформатировать",
    no: "Сырой текст, который надо вычитывать и собирать самому",
  },
];

export function WhyNotChatGPT() {
  return (
    <section className="bg-gray-50 border-y border-gray-100 py-24 px-4">
      <div className="max-w-(--l-content) mx-auto">
        <ScrollReveal>
          <div className="mb-(--l-section-heading)">
            <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-100 px-3 py-1.5 rounded-full mb-6">
              Главный вопрос
            </div>
            <h2 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight">
              А чем это лучше, чем спросить у ChatGPT?
            </h2>
            <p className="text-gray-500 text-lg max-w-xl">
              Если коротко — ChatGPT отвечает на вопрос. Мы выдаём документ,
              готовый к отправке.
            </p>
          </div>
        </ScrollReveal>

        <ScrollReveal delay={100}>
          <div className="rounded-2xl overflow-hidden shadow-sm border border-gray-200">
            <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-200">
              {/* LawDocs side — dark */}
              <div className="bg-gray-900 p-6 md:p-8">
                <div className="inline-flex items-center gap-2 text-sm font-semibold text-blue-400 mb-6">
                  <CheckCircle className="h-4 w-4" />
                  LawDocs
                </div>
                <ul className="space-y-4">
                  {POINTS.map((p) => (
                    <li key={p.yes} className="flex items-start gap-3">
                      <CheckCircle className="h-4 w-4 text-blue-400 mt-1 shrink-0" />
                      <span className="text-sm text-gray-300 leading-relaxed">{p.yes}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* ChatGPT side — light */}
              <div className="bg-white p-6 md:p-8">
                <div className="inline-flex items-center gap-2 text-sm font-semibold text-gray-400 mb-6">
                  <XCircle className="h-4 w-4" />
                  Универсальный AI
                </div>
                <ul className="space-y-4">
                  {POINTS.map((p) => (
                    <li key={p.no} className="flex items-start gap-3">
                      <XCircle className="h-4 w-4 text-gray-300 mt-1 shrink-0" />
                      <span className="text-sm text-gray-500 leading-relaxed">{p.no}</span>
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
