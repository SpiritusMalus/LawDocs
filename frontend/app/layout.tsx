import type { Metadata } from "next";
import Script from "next/script";
import { cookies } from "next/headers";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/landing/footer";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://law-docs.ru";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "LawDocs — готовый юридический документ за 5 минут, 199 ₽",
  description:
    "Претензия в магазин, банк, к работодателю или страховой — оформленная по всем правилам. Шаблоны проверены юристом.",
  keywords:
    "претензия в магазин, жалоба на банк, жалоба на работодателя, претензия страховой, претензия маркетплейс wildberries ozon, жалоба управляющая компания, претензия авиакомпания, юридический документ онлайн, защита прав потребителей",
  openGraph: {
    title: "LawDocs — готовый юридический документ за 5 минут",
    description:
      "Опишите проблему — получите претензию или жалобу с расчётом неустойки и инструкцией. От 199 ₽.",
    type: "website",
    locale: "ru_RU",
  },
};

const rawYmCounterId = process.env.NEXT_PUBLIC_YM_COUNTER_ID;
// Hard validation: must be digits only, otherwise refuse to inject into <script>.
const ymCounterId = rawYmCounterId && /^\d+$/.test(rawYmCounterId) ? rawYmCounterId : null;

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const isAuthenticated = !!cookieStore.get("access_token")?.value;

  return (
    <html lang="ru" className="h-full" data-scroll-behavior="smooth">
      <body className="min-h-full flex flex-col bg-background text-foreground antialiased">
        <Header isAuthenticated={isAuthenticated} />
        <main className="flex-1">{children}</main>
        <Footer />

        {ymCounterId && (
          <Script id="ym-counter" strategy="afterInteractive">
            {`
              (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
              m[i].l=1*new Date();
              for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
              k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
              (window, document,'script','https://mc.yandex.ru/metrika/tag.js','ym');
              ym(${ymCounterId}, 'init', { webvisor:true, clickmap:true, accurateTrackBounce:true, trackLinks:true });
            `}
          </Script>
        )}
      </body>
    </html>
  );
}
