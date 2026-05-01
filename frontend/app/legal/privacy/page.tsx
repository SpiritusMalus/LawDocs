export const metadata = {
  title: "Политика конфиденциальности — LawDocs",
  robots: { index: false },
};

export default function PrivacyPage() {
  return (
    <article className="max-w-3xl mx-auto px-4 py-16 prose prose-gray">
      <h1 className="text-3xl font-bold mb-6">Политика обработки персональных данных</h1>

      <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-lg px-4 py-3 text-sm mb-8">
        <strong>Черновик.</strong> Финальная редакция готовится юристом-партнёром
        в соответствии с 152-ФЗ. До запуска платных услуг будет также подано
        уведомление в Роскомнадзор.
      </div>

      <h2 className="text-xl font-semibold mt-8 mb-3">1. Какие данные мы собираем</h2>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Имя — для обращения к вам.</li>
        <li>Контакт (телефон или email) — чтобы связаться по заявке.</li>
        <li>Описание ситуации — чтобы подготовить документ.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-8 mb-3">2. Цели обработки</h2>
      <p className="text-gray-700 leading-relaxed">
        Данные используются исключительно для подготовки и доставки заказанного документа,
        а также для связи с пользователем по поводу заказа.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">3. Где и как хранятся данные</h2>
      <p className="text-gray-700 leading-relaxed">
        Данные хранятся на серверах в Российской Федерации в соответствии с 152-ФЗ.
        Доступ ограничен сотрудниками сервиса и привлечёнными юристами на основании
        соглашения о конфиденциальности.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">4. Передача третьим лицам</h2>
      <p className="text-gray-700 leading-relaxed">
        Данные не передаются третьим лицам без согласия пользователя, за исключением
        случаев, прямо предусмотренных законодательством Российской Федерации.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">5. Использование ИИ</h2>
      <p className="text-gray-700 leading-relaxed">
        При подготовке документа описание ситуации обрабатывается языковой моделью
        (GigaChat от ПАО Сбербанк или аналог в РФ), что необходимо для автоматического
        подбора и заполнения шаблона. Согласие на это обрабатывание пользователь
        выражает при отправке заявки.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">6. Ваши права</h2>
      <p className="text-gray-700 leading-relaxed">
        Вы вправе запросить удаление своих данных, написав на{" "}
        <a href="mailto:hi@lawdocs.ru" className="underline">hi@lawdocs.ru</a>.
      </p>
    </article>
  );
}
