import { Hero } from "@/components/landing/hero";
import { TrustBlock } from "@/components/landing/trust-block";
import { SocialProofBar } from "@/components/landing/social-proof-bar";
import { Situations } from "@/components/landing/situations";
import { HowItWorks } from "@/components/landing/how-it-works";
import { WhyNotChatGPT } from "@/components/landing/why-not-chatgpt";
import { Pricing } from "@/components/landing/pricing";
import { Faq } from "@/components/landing/faq";
import { FaqJsonLd } from "@/components/landing/faq-jsonld";
import { MobileStickyCTA } from "@/components/landing/mobile-sticky-cta";
import { ReviewsCarousel } from "@/components/reviews/reviews-carousel";
import { DOCUMENT_PRICE_RUB } from "@/lib/pricing";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://law-docs.ru";

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Service",
  name: "LawDocs",
  url: SITE_URL,
  description:
    "Онлайн-сервис подготовки юридических документов: претензии и жалобы для защиты прав потребителей.",
  areaServed: { "@type": "Country", name: "RU" },
  availableLanguage: "Russian",
  offers: {
    "@type": "Offer",
    price: String(DOCUMENT_PRICE_RUB),
    priceCurrency: "RUB",
    description: "Составление претензии или жалобы с расчётом неустойки и инструкцией по отправке",
  },
  provider: {
    "@type": "Organization",
    name: "LawDocs",
    url: SITE_URL,
    contactPoint: {
      "@type": "ContactPoint",
      email: "lawdocsru@gmail.com",
      contactType: "customer service",
      availableLanguage: "Russian",
    },
  },
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
      />
      <FaqJsonLd />
      <MobileStickyCTA />
      <Hero />
      <TrustBlock />
      <SocialProofBar />
      <Situations />
      <HowItWorks />
      <WhyNotChatGPT />
      <Pricing />
      <ReviewsCarousel />
      <Faq />
    </>
  );
}
