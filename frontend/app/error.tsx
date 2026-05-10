"use client";

import { useEffect } from "react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[GlobalError]", error.digest ?? error.message);
  }, [error]);

  return (
    <section className="bg-white py-24 px-4 min-h-[70vh] flex items-center">
      <div className="max-w-md mx-auto text-center">
        <div className="text-6xl font-bold text-gray-100 mb-4">500</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Что-то пошло не так</h1>
        <p className="text-gray-500 mb-8">
          Ошибка на нашей стороне. Попробуйте ещё раз или напишите на{" "}
          <a href="mailto:lawdocsru@gmail.com" className="text-blue-600 hover:underline">
            lawdocsru@gmail.com
          </a>
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={reset}
            className={buttonVariants({ variant: "outline" }) + " h-10 px-5"}
          >
            Попробовать снова
          </button>
          <Link href="/" className={buttonVariants({}) + " h-10 px-5"}>
            На главную
          </Link>
        </div>
      </div>
    </section>
  );
}
