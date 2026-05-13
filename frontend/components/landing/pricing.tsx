import { CheckCircle } from "lucide-react";

const INCLUDED = [
  "Претензия в форматах .docx и .pdf",
  "Расчёт неустойки или процентов, если применимо",
  "Инструкция: реальные контакты компании, куда отправить, сроки",
  "Ссылки на законы — читать прямо в КонсультантПлюс",
  "Возврат денег, если документ вам не подойдёт",
];

export function Pricing() {
  return (
    <section className="bg-white py-24 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Прозрачная цена
          </h2>
          <p className="text-gray-500 max-w-xl">
            Платите один раз за результат, без подписок и скрытых комиссий.
          </p>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-white rounded-3xl border-2 border-blue-100 p-8 md:p-10">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-8 pb-8 border-b border-gray-100">
            <div>
              <h3 className="text-xl font-semibold text-gray-900 mb-1">
                Один готовый документ
              </h3>
              <p className="text-sm text-gray-500">
                Любая из 7 типовых ситуаций
              </p>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold text-gray-900">100&nbsp;₽</div>
              <div className="text-xs text-gray-400">разовая оплата</div>
            </div>
          </div>

          <ul className="space-y-3">
            {INCLUDED.map((item) => (
              <li key={item} className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
                <span className="text-sm text-gray-700">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6 max-w-md mx-auto">
          Сложный случай и нужна личная консультация?{" "}
          <a
            href="mailto:lawdocsru@gmail.com?subject=Консультация юриста"
            className="text-blue-500 hover:underline"
          >
            Напишите нам
          </a>{" "}
          — подключим партнёра, от 1500&nbsp;₽.
        </p>
      </div>
    </section>
  );
}
