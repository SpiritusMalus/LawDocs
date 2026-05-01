import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { SITUATIONS } from "@/lib/situations";

export default function NotFound() {
  return (
    <section className="bg-white py-24 px-4 min-h-[70vh]">
      <div className="max-w-2xl mx-auto text-center">
        <div className="text-8xl font-bold text-gray-100 mb-4">404</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-3">
          Страница не найдена
        </h1>
        <p className="text-gray-500 mb-10">
          Такой страницы не существует. Возможно, вы искали один из этих документов:
        </p>

        <div className="grid sm:grid-cols-2 gap-3 text-left mb-10">
          {SITUATIONS.map((s) => (
            <Link
              key={s.id}
              href={`/situations/${s.id}`}
              className="flex items-center gap-3 bg-gray-50 hover:bg-blue-50 border border-gray-100 hover:border-blue-200 rounded-xl px-4 py-3 text-sm font-medium text-gray-700 hover:text-blue-700 transition-all"
            >
              <span className="text-blue-500">→</span>
              {s.title}
            </Link>
          ))}
        </div>

        <Link href="/" className={buttonVariants({ variant: "outline" }) + " h-10 px-5"}>
          На главную
        </Link>
      </div>
    </section>
  );
}
