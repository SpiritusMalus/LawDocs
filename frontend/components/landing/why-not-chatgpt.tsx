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
      <div className="max-w-5xl mx-auto">
        <ScrollReveal>
        <div className="mb-14">
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-600 bg-blue-50 px-3 py-1.5 rounded-full mb-6">
            Главный вопрос
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            А чем это лучше, чем спросить у ChatGPT?
          </h2>
          <p className="text-gray-500 max-w-xl">
            Если коротко — ChatGPT отвечает на вопрос. Мы выдаём документ,
            готовый к отправке.
          </p>
        </div>
        </ScrollReveal>

        <ScrollReveal delay={100}>
        <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
          <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-100">
            <div className="p-6 md:p-8">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-600 mb-6">
                <CheckCircle className="h-4 w-4" />
                LawDocs
              </div>
              <ul className="space-y-4">
                {POINTS.map((p) => (
                  <li key={p.yes} className="flex items-start gap-3">
                    <CheckCircle className="h-4 w-4 text-emerald-500 mt-1 shrink-0" />
                    <span className="text-sm text-gray-700 leading-relaxed">{p.yes}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="p-6 md:p-8 bg-gray-50/50">
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
