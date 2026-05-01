import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <section className="bg-white py-24 px-4 min-h-[70vh] flex items-center">
      <div className="max-w-md mx-auto text-center">
        <div className="text-6xl font-bold text-gray-200 mb-6">404</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-3">
          Страница не найдена
        </h1>
        <p className="text-gray-500 mb-8">
          Похоже, такой страницы не существует или она переехала.
          Вернитесь на главную и начните оттуда.
        </p>
        <Link href="/" className={buttonVariants({}) + " h-10 px-5"}>
          На главную
        </Link>
      </div>
    </section>
  );
}
