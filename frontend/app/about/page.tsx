import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "О сервисе — LawDocs",
  description:
    "LawDocs — онлайн-сервис подготовки юридических документов. Узнайте, как мы помогаем людям защищать свои права.",
};

export default function AboutPage() {
  return (
    <article className="max-w-3xl mx-auto px-4 py-16 prose prose-gray">
      <h1 className="text-3xl font-bold mb-6">О сервисе</h1>

      <h2 className="text-xl font-semibold mt-8 mb-3">Зачем мы это сделали</h2>
      <p className="text-gray-700 leading-relaxed">
        Большинство людей, столкнувшись с нарушением своих прав — будь то некачественный товар,
        задержка возврата денег или отказ страховой — не знают, с чего начать. Составить претензию
        самому страшно: непонятно, какие статьи цитировать, как рассчитать неустойку и куда всё это
        нести.
      </p>
      <p className="text-gray-700 leading-relaxed">
        LawDocs появился в 2026 году как ответ на этот барьер. Мы автоматизировали то, что юристы
        делают каждый день: берём описание вашей ситуации и составляем документ с правильными
        формулировками, расчётами и ссылками на закон — за 5 минут и 199 рублей.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">Как это работает</h2>
      <p className="text-gray-700 leading-relaxed">
        Вы отвечаете на вопросы формы — система подбирает шаблон и заполняет его вашими данными.
        Шаблоны составлены и проверены юристом. Итоговый документ приходит на email в форматах
        Word и PDF вместе с инструкцией: куда подавать, в какие сроки, что писать на конверте.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">Что получает покупатель</h2>
      <ul className="list-disc pl-6 text-gray-700 space-y-1">
        <li>Готовый юридический документ в форматах Word (.docx) и PDF</li>
        <li>Расчёт неустойки по закону — формула и сумма</li>
        <li>Инструкция по подаче: адресат, способ отправки, сроки ответа</li>
      </ul>
      <p className="text-gray-700 leading-relaxed mt-3">
        Файлы доступны для скачивания в личном кабинете сразу после формирования.
        Стоимость — <strong>199 рублей</strong> за документ.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">Возврат средств</h2>
      <p className="text-gray-700 leading-relaxed">
        Если документ не соответствует ситуации, описанной в форме, — вернём деньги без вопросов
        в течение 7 дней. Пишите на{" "}
        <a href="mailto:lawdocsru@gmail.com" className="underline">
          lawdocsru@gmail.com
        </a>{" "}
        с номером заказа.
      </p>

      <hr className="my-12 border-gray-200" />

      <h2 className="text-xl font-semibold mb-3 text-gray-500">Реквизиты</h2>
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

      <p className="text-sm text-gray-400 mt-6">
        Полные условия оферты:{" "}
        <Link href="/legal/offer" className="underline">
          Договор оферты
        </Link>
        {" · "}
        <Link href="/legal/privacy" className="underline">
          Политика конфиденциальности
        </Link>
      </p>
    </article>
  );
}
