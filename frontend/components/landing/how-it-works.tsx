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
    title: "Оплачиваете 100 ₽",
    desc: "Картой или СБП. Быстро и безопасно — через сервис ЮKassa.",
  },
  {
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
          {STEPS.map(({ title, desc }, i) => (
            <div key={title} className="relative">
              <div className="bg-gray-50 rounded-2xl border border-gray-100 p-6 h-full">
                <div className="text-5xl font-bold text-blue-100 leading-none mb-4 select-none">
                  0{i + 1}
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
