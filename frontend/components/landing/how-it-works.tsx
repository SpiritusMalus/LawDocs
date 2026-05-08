import { ClipboardList, MessageSquare, CreditCard, FileCheck } from "lucide-react";

const STEPS = [
  {
    icon: ClipboardList,
    title: "Выбираете ситуацию",
    desc: "Из списка типовых случаев или описываете в свободной форме.",
  },
  {
    icon: MessageSquare,
    title: "Отвечаете на 5–10 вопросов",
    desc: "Дата, сумма, реквизиты сторон. Простыми словами, без юридических терминов.",
  },
  {
    icon: CreditCard,
    title: "Оплачиваете 500 ₽",
    desc: "Картой или СБП. Счёт пришлём после уточнения деталей — никаких предоплат вслепую.",
  },
  {
    icon: FileCheck,
    title: "Получаете готовый комплект",
    desc: "Претензия в .docx и .pdf + инструкция с контактами и ссылками на законы — на email через несколько минут.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-white py-24 px-4 scroll-mt-16">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Как это работает
          </h2>
          <p className="text-gray-500 max-w-xl mx-auto">
            5 минут от вопроса до готового документа на руках.
          </p>
        </div>

        <div className="grid md:grid-cols-4 gap-6">
          {STEPS.map(({ icon: Icon, title, desc }, i) => (
            <div key={title} className="relative">
              <div className="bg-gray-50 rounded-2xl border border-gray-100 p-6 h-full">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-xs font-semibold text-gray-300">
                    0{i + 1}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
