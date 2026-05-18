import Link from "next/link";

export const metadata = {
  title: "Политика конфиденциальности — LawDocs",
  robots: { index: false },
};

export default function PrivacyPage() {
  return (
    <article className="max-w-3xl mx-auto px-4 py-16 prose prose-gray">
      <h1 className="text-3xl font-bold mb-2">Политика обработки персональных данных</h1>
      <p className="text-sm text-gray-400 mb-8">Редакция от 18 мая 2026 г.</p>

      <p className="text-gray-700 leading-relaxed">
        Настоящая политика определяет порядок обработки персональных данных пользователей
        сайта law-docs.ru (далее — Сайт). Оператором персональных данных является
        индивидуальный предприниматель Тихоненко Евгений Юрьевич (ИНН 504414138460,
        ОГРНИП 326508100294665, далее — Оператор). Обработка данных осуществляется в
        соответствии с Федеральным законом № 152-ФЗ «О персональных данных».
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">1. Какие данные мы собираем</h2>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Адрес электронной почты — для авторизации и доставки готового документа.</li>
        <li>Данные, указанные в форме заявки (имя, описание ситуации и иные сведения) —
          для подготовки юридического документа.</li>
        <li>Технические данные (IP-адрес, тип браузера, cookie) — для обеспечения
          корректной работы Сайта.</li>
      </ul>

      <h2 className="text-xl font-semibold mt-8 mb-3">2. Цели обработки</h2>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Исполнение договора-оферты: подготовка и доставка заказанного документа.</li>
        <li>Авторизация пользователя и управление личным кабинетом.</li>
        <li>Направление уведомлений, связанных с заказом (статус, готовность документа).</li>
        <li>Обработка платежей через сервис ЮKassa (ООО НКО «ЮMoney»).</li>
      </ul>

      <h2 className="text-xl font-semibold mt-8 mb-3">3. Основания обработки</h2>
      <p className="text-gray-700 leading-relaxed">
        Обработка данных осуществляется на основании согласия пользователя, выраженного
        при заполнении формы и оплате услуги, а также в целях исполнения договора
        (п. 5 ч. 1 ст. 6 152-ФЗ).
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">4. Передача данных третьим лицам</h2>
      <p className="text-gray-700 leading-relaxed">
        Для исполнения договора данные могут передаваться следующим лицам:
      </p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>ООО НКО «ЮMoney» (ЮKassa) — для проведения платежей.</li>
        <li>Языковой модели GigaChat (ПАО Сбербанк) — для автоматического составления
          документа по введённым данным. Данные обрабатываются в соответствии с
          политикой конфиденциальности Сбербанка.</li>
      </ul>
      <p className="text-gray-700 leading-relaxed mt-3">
        Данные не передаются иным третьим лицам без согласия пользователя, за исключением
        случаев, предусмотренных законодательством Российской Федерации.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">5. Хранение данных</h2>
      <p className="text-gray-700 leading-relaxed">
        Данные хранятся на серверах на территории Российской Федерации. Срок хранения —
        до момента удаления аккаунта по запросу пользователя или истечения 3 лет с
        момента последнего заказа, если пользователь не обратился с иным запросом.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">6. Права пользователя</h2>
      <p className="text-gray-700 leading-relaxed">
        В соответствии со ст. 14–17 152-ФЗ вы вправе:
      </p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Получить информацию об обрабатываемых персональных данных.</li>
        <li>Потребовать уточнения или удаления данных.</li>
        <li>Отозвать согласие на обработку данных.</li>
      </ul>
      <p className="text-gray-700 leading-relaxed mt-3">
        Для реализации прав напишите на{" "}
        <a href="mailto:lawdocsru@gmail.com" className="underline">lawdocsru@gmail.com</a>.
        Оператор рассмотрит обращение в течение 30 дней.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">7. Использование cookie</h2>
      <p className="text-gray-700 leading-relaxed">
        Сайт использует cookie только для поддержания сессии авторизованного пользователя.
        Файлы cookie не используются для рекламных целей и не передаются рекламным сетям.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">8. Контакты оператора</h2>
      <p className="text-gray-700">
        Полные реквизиты — на странице{" "}
        <Link href="/about" className="underline">О сервисе</Link>.{" "}
        Email:{" "}
        <a href="mailto:lawdocsru@gmail.com" className="underline">lawdocsru@gmail.com</a>.
      </p>
    </article>
  );
}
