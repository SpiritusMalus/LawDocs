import { Suspense } from "react";
import { Hero } from "@/components/landing/hero";
import { Situations } from "@/components/landing/situations";
import { HowItWorks } from "@/components/landing/how-it-works";
import { WhyNotChatGPT } from "@/components/landing/why-not-chatgpt";
import { Pricing } from "@/components/landing/pricing";
import { Faq } from "@/components/landing/faq";
import { FaqJsonLd } from "@/components/landing/faq-jsonld";
import { LeadForm } from "@/components/landing/lead-form";

export default function HomePage() {
  return (
    <>
      <FaqJsonLd />
      <Hero />
      <Situations />
      <HowItWorks />
      <WhyNotChatGPT />
      <Pricing />
      <Faq />
      <Suspense fallback={null}>
        <LeadForm />
      </Suspense>
    </>
  );
}
