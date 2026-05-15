import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "О сервисе — LawDocs",
  description:
    "Информация о сервисе LawDocs: подготовка юридических документов онлайн. Реквизиты, контакты, описание услуги.",
};

export default function AboutPage() {
  return (
    <article className="max-w-3xl mx-auto px-4 py-16 prose prose-gray">
      <h1 className="text-3xl font-bold mb-6">О сервисе</h1>

      <h2 className="text-xl font-semibold mt-8 mb-3">Что такое LawDocs</h2>
      <p className="text-gray-700 leading-relaxed">
        LawDocs — онлайн-сервис подготовки юридических документов. Пользователь описывает
        свою ситуацию через форму, система формирует готовый документ (претензию или жалобу)
        с расчётом неустойки и инструкцией по отправке. Документ предоставляется в форматах
        Word (.docx) и PDF на указанный email.
      </p>
      <p className="text-gray-700 leading-relaxed">
        Документы формируются на основе проверенных юридических шаблонов с применением
        технологий искусственного интеллекта. Сервис не оказывает юридических консультаций;
        документы носят информационный характер.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">Что получает покупатель</h2>
      <p className="text-gray-700 leading-relaxed">
        После оплаты покупатель получает цифровой товар — комплект файлов:
      </p>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>готовый юридический документ в формате Word (.docx) и PDF;</li>
        <li>инструкцию по подаче документа с указанием адресата и способа отправки.</li>
      </ul>
      <p className="text-gray-700 leading-relaxed">
        Файлы доступны для скачивания в личном кабинете сразу после формирования.
        Стоимость одного документа — <strong>199 рублей</strong>.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">Реквизиты</h2>
      <table className="text-sm text-gray-700 border-collapse w-full">
        <tbody>
          <tr className="border-b border-gray-100">
            <td className="py-2 pr-6 text-gray-500 font-medium whitespace-nowrap">Продавец</td>
            <td className="py-2">ИП Тихоненко Евгений Юрьевич</td>
          </tr>
          <tr className="border-b border-gray-100">
            <td className="py-2 pr-6 text-gray-500 font-medium">ИНН</td>
            <td className="py-2">504414138460</td>
          </tr>
          <tr className="border-b border-gray-100">
            <td className="py-2 pr-6 text-gray-500 font-medium">ОГРНИП</td>
            <td className="py-2">326508100294665</td>
          </tr>
          <tr>
            <td className="py-2 pr-6 text-gray-500 font-medium">Email</td>
            <td className="py-2">
              <a href="mailto:lawdocsru@gmail.com" className="underline">
                lawdocsru@gmail.com
              </a>
            </td>
          </tr>
        </tbody>
      </table>

      <h2 className="text-xl font-semibold mt-8 mb-3">Возврат средств</h2>
      <p className="text-gray-700 leading-relaxed">
        Если подготовленный документ не соответствует ситуации, описанной в форме,
        покупатель вправе запросить возврат в течение 7 календарных дней с момента получения.
        Для этого напишите на{" "}
        <a href="mailto:lawdocsru@gmail.com" className="underline">
          lawdocsru@gmail.com
        </a>{" "}
        с указанием номера заказа.
      </p>
    </article>
  );
}
