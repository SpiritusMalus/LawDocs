export const metadata = {
  title: "Договор-оферта — LawDocs",
  robots: { index: false },
};

export default function OfferPage() {
  return (
    <article className="max-w-3xl mx-auto px-4 py-16 prose prose-gray">
      <h1 className="text-3xl font-bold mb-6">Договор-оферта</h1>

      <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-lg px-4 py-3 text-sm mb-8">
        <strong>Черновик.</strong> Финальная редакция готовится юристом-партнёром.
        Если вам нужны юридические условия для конкретной сделки — напишите на{" "}
        <a href="mailto:lawdocsru@gmail.com" className="underline">lawdocsru@gmail.com</a>.
      </div>

      <h2 className="text-xl font-semibold mt-8 mb-3">1. Общие положения</h2>
      <p className="text-gray-700 leading-relaxed">
        Настоящий документ является публичной офертой (далее — Оферта) сервиса LawDocs.
        Принимая её условия, пользователь заключает договор на оказание услуг по подготовке
        типовых юридических документов.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">2. Предмет договора</h2>
      <p className="text-gray-700 leading-relaxed">
        Сервис обязуется на основании предоставленных пользователем данных подготовить
        юридический документ по типовому шаблону (претензия, жалоба и т. п.).
        Услуга не является юридической консультацией. Документ носит информационный характер.
        При формировании документа используются технологии искусственного интеллекта.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">3. Стоимость и порядок оплаты</h2>
      <p className="text-gray-700 leading-relaxed">
        Стоимость одного документа — 500 рублей. Оплата производится после согласования
        деталей в установленном на сайте порядке.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">4. Возврат денежных средств</h2>
      <p className="text-gray-700 leading-relaxed">
        Если пользователь считает, что подготовленный документ не соответствует его ситуации,
        он вправе запросить возврат в течение 7 календарных дней с момента получения документа.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">5. Ответственность</h2>
      <p className="text-gray-700 leading-relaxed">
        Сервис не несёт ответственности за решения третьих лиц (магазинов, банков, ведомств)
        по результатам рассмотрения подготовленных документов.
      </p>
    </article>
  );
}
