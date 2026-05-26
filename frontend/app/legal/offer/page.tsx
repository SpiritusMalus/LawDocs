import Link from "next/link";

export const metadata = {
  title: "Договор-оферта — LawDocs",
  robots: { index: false },
};

export default function OfferPage() {
  return (
    <article className="max-w-3xl mx-auto px-4 py-16 prose prose-gray">
      <h1 className="text-3xl font-bold mb-2">Договор-оферта</h1>
      <p className="text-sm text-gray-400 mb-8">Редакция от 18 мая 2026 г.</p>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-8 not-prose">
        <p className="font-semibold text-gray-800 mb-3">Главное для вас</p>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">Стоимость</p>
            <p className="text-lg font-semibold text-gray-800">199 ₽</p>
            <p className="text-xs text-gray-500">один документ</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Срок получения</p>
            <p className="text-lg font-semibold text-gray-800">10 мин</p>
            <p className="text-xs text-gray-500">после оплаты</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Возврат</p>
            <p className="text-lg font-semibold text-gray-800">7 дней</p>
            <p className="text-xs text-gray-500">если не подошло</p>
          </div>
        </div>
      </div>

      <p className="text-gray-700 leading-relaxed">
        Индивидуальный предприниматель Тихоненко Евгений Юрьевич (ИНН 504414138460,
        ОГРНИП 326508100294665, далее — Исполнитель) предлагает любому дееспособному
        физическому лицу (далее — Заказчик) заключить договор на условиях настоящей
        публичной оферты.
      </p>
      <p className="text-gray-700 leading-relaxed">
        Акцептом оферты является оплата услуги. С момента оплаты договор считается заключённым.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">1. Предмет договора</h2>
      <p className="text-gray-700 leading-relaxed">
        Исполнитель обязуется на основании данных, предоставленных Заказчиком через форму
        на сайте law-docs.ru, подготовить типовой юридический документ (претензию или жалобу)
        и передать его Заказчику в электронном виде (форматы Word и PDF).
      </p>
      <p className="text-gray-700 leading-relaxed">
        Услуга не является юридической консультацией. Документ формируется по типовому
        шаблону с использованием технологий искусственного интеллекта и носит
        информационный характер.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">2. Стоимость и порядок оплаты</h2>
      <p className="text-gray-700 leading-relaxed">
        Стоимость одного документа — <strong>199 рублей</strong>. Оплата производится
        онлайн картой или через СБП с использованием платёжного сервиса ЮKassa
        (ООО НКО «ЮMoney», лицензия ЦБ РФ № 3510-К). Документ предоставляется
        только после подтверждения оплаты.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">3. Права и обязанности сторон</h2>
      <p className="text-gray-700 leading-relaxed">
        Исполнитель обязуется передать готовый документ на email Заказчика в течение
        10 минут с момента подтверждения оплаты. В случае технической невозможности —
        уведомить Заказчика и вернуть оплату.
      </p>
      <p className="text-gray-700 leading-relaxed">
        Заказчик обязуется предоставить достоверные сведения при заполнении формы.
        Исполнитель не несёт ответственности за последствия использования документа,
        составленного на основе недостоверных данных.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">4. Возврат денежных средств</h2>
      <p className="text-gray-700 leading-relaxed">
        Если подготовленный документ не соответствует ситуации, описанной Заказчиком,
        Заказчик вправе запросить возврат в течение 7 календарных дней с момента
        получения документа. Для этого необходимо написать на{" "}
        <a href="mailto:lawdocsru@gmail.com" className="underline">lawdocsru@gmail.com</a>{" "}
        с указанием номера заказа. Возврат осуществляется на карту, с которой была
        произведена оплата, в течение 10 рабочих дней.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">5. Ответственность</h2>
      <p className="text-gray-700 leading-relaxed">
        Исполнитель не несёт ответственности за решения третьих лиц (организаций,
        государственных органов) по результатам рассмотрения подготовленных документов.
        Ответственность Исполнителя ограничена суммой оплаченной услуги.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">6. Реквизиты Исполнителя</h2>
      <p className="text-gray-700">
        Полные реквизиты — на странице{" "}
        <Link href="/about" className="underline">О сервисе</Link>.
      </p>

      <div className="mt-8 pt-6 border-t border-gray-200 text-xs text-gray-500 not-prose">
        <p>Редакция от 18 мая 2026 г.</p>
        <p>Статус: Опубликована и действует</p>
        <p>Соответствие: ГК РФ · ФЗ «О защите прав потребителей»</p>
      </div>
    </article>
  );
}
