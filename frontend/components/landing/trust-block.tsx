import { Shield, Scale, FileText, Globe } from "lucide-react";

const TRUST_ITEMS = [
  {
    icon: Shield,
    title: "Гарантия возврата",
    description: "Не подошло — вернём 199 ₽ за 7 дней без вопросов",
  },
  {
    icon: Scale,
    title: "Проверено юристом",
    description:
      "Шаблоны вычитаны практикующим юристом по защите прав потребителей",
  },
  {
    icon: FileText,
    title: "Проверяемые ссылки",
    description:
      "Каждая претензия со ссылками на статьи в КонсультантПлюс — проверяй сам",
  },
  {
    icon: Globe,
    title: "Российский ИП",
    description:
      "ИП Тихоненко Е.Ю., ИНН 504414138460. Оплата через ЮKassa",
  },
];

export function TrustBlock() {
  return (
    <section className="bg-white py-16 px-4" aria-labelledby="trust-heading">
      <h2 id="trust-heading" className="sr-only">Гарантии сервиса</h2>
      <div className="max-w-(--l-content) mx-auto">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {TRUST_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="rounded-2xl border border-gray-200 p-6 hover:border-blue-200 hover:shadow-sm transition-colors"
              >
                <Icon className="h-8 w-8 text-blue-600 mb-3" aria-hidden="true" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {item.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
