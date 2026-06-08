import { OFFER_EDITION } from "@/lib/legal-version";

export const metadata = {
  title: "Договор-оферта — LawDocs",
  robots: { index: false },
};

// Оферта меняется редко; ISR на час, чтобы не дёргать бэкенд на каждый рендер.
export const revalidate = 3600;

type Offer = {
  version: string;
  edition_human: string;
  text_hash: string;
  text: string;
};

// Единственный источник текста оферты — бэкенд (app/legal/offer/<version>.md), он же
// хэширует его и штампует на заказ. Рендерим страницу ИЗ этого текста, поэтому
// показанное и захэшированное не могут разойтись.
async function fetchOffer(): Promise<Offer | null> {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) return null;
  try {
    const res = await fetch(`${backendUrl}/api/v1/legal/offer`, {
      next: { revalidate },
    });
    if (!res.ok) return null;
    return (await res.json()) as Offer;
  } catch {
    return null;
  }
}

// Лёгкий рендер канонического markdown оферты (## заголовки + абзацы). Полноценный
// markdown-движок не нужен: текст состоит только из заголовков второго уровня и
// абзацев. Ведущий `# …` (дублирует заголовок страницы) пропускаем.
function renderOfferBody(text: string) {
  const blocks = text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  return blocks.flatMap((block, i) => {
    if (block.startsWith("# ")) return [];
    if (block.startsWith("## ")) {
      return [
        <h2 key={i} className="text-xl font-semibold mt-8 mb-3">
          {block.slice(3).trim()}
        </h2>,
      ];
    }
    return [
      <p key={i} className="text-gray-700 leading-relaxed whitespace-pre-line">
        {block}
      </p>,
    ];
  });
}

export default async function OfferPage() {
  const offer = await fetchOffer();
  const editionHuman = offer?.edition_human ?? OFFER_EDITION.human;

  return (
    <article className="max-w-3xl mx-auto px-4 py-16 prose prose-gray">
      <h1 className="text-3xl font-bold mb-2">Договор-оферта</h1>
      <p className="text-sm text-gray-400 mb-8">Редакция от {editionHuman}</p>

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

      {offer ? (
        renderOfferBody(offer.text)
      ) : (
        <p className="text-gray-700 leading-relaxed">
          Текст оферты временно недоступен. Обновите страницу позже или напишите на{" "}
          <a href="mailto:lawdocsru@gmail.com" className="underline">
            lawdocsru@gmail.com
          </a>
          .
        </p>
      )}

      <div className="mt-8 pt-6 border-t border-gray-200 text-xs text-gray-500 not-prose">
        <p>Редакция от {editionHuman}</p>
        <p>Статус: Опубликована и действует</p>
        <p>Соответствие: ГК РФ · ФЗ «О защите прав потребителей»</p>
      </div>
    </article>
  );
}
