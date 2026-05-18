const STEPS = [
  {
    title: "Выбираете ситуацию",
    desc: "Из списка типовых случаев или описываете в свободной форме.",
  },
  {
    title: "Отвечаете на 5–10 вопросов",
    desc: "Дата, сумма, реквизиты сторон. Простыми словами, без юридических терминов.",
  },
  {
    title: "Оплачиваете 199 ₽",
    desc: "Картой или СБП. Быстро и безопасно — через сервис ЮKassa.",
  },
  {
    title: "Получаете готовый комплект",
    desc: "Претензия в .docx и .pdf + инструкция с контактами и ссылками на законы — на email через несколько минут.",
  },
];

import { ScrollReveal } from "@/components/ui/scroll-reveal";

export function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-white py-24 px-4 scroll-mt-16">
      <div className="max-w-(--l-content) mx-auto">
        <div className="mb-(--l-section-heading)">
          <h2 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight">
            Как это работает
          </h2>
          <p className="text-gray-500 text-lg max-w-xl">
            5 минут от вопроса до готового документа на руках.
          </p>
        </div>

        <div className="grid md:grid-cols-4 gap-6">
          {STEPS.map(({ title, desc }, i) => (
            <ScrollReveal key={title} delay={i * 80}>
              <div className="relative">
                <div className="bg-gray-50 rounded-2xl border border-gray-100 p-6 h-full hover:border-primary/20 hover:shadow-md transition-all">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-gray-900 flex items-center justify-center shrink-0">
                      <span className="text-sm font-bold text-white">0{i + 1}</span>
                    </div>
                    {i < STEPS.length - 1 && (
                      <div className="hidden md:block absolute top-10 left-full w-6 h-px bg-gray-200 -translate-y-1/2 z-10" />
                    )}
                  </div>
                  <h3 className="text-base font-semibold text-gray-900 mb-2">{title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
