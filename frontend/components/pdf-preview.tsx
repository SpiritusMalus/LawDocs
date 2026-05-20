"use client";

import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";

export function PdfPreview({ src }: { src: string }) {
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    // CriOS = Chrome on iOS, FxiOS = Firefox on iOS — both support PDF via their own engines
    setIsIOS(
      /iPhone|iPad|iPod/i.test(navigator.userAgent) &&
        !/CriOS|FxiOS/i.test(navigator.userAgent)
    );
  }, []);

  if (isIOS) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-gray-50 flex flex-col items-center justify-center py-16 px-8 text-center gap-4">
        <FileText className="h-12 w-12 text-gray-300" />
        <p className="text-gray-500 text-sm">
          Встроенный просмотр PDF недоступен в Safari на iOS
        </p>
        <a
          href={src}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonVariants({ variant: "outline" })}
        >
          <FileText className="h-4 w-4 mr-2" />
          Открыть PDF
        </a>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gray-200 overflow-hidden">
      <iframe
        src={src}
        className="w-full h-[700px]"
        title="Пример документа"
      />
    </div>
  );
}
