import { FAQ_ITEMS } from "@/lib/faq";

// Escape characters that would break out of a <script> tag or be re-interpreted
// when the JSON payload is embedded inline in HTML:
//   <, > — could form </script> or comments
//   &    — could form HTML entities
//   U+2028 / U+2029 — valid in JSON, but JavaScript treats them as line
//                     terminators, which corrupts re-parsing
const UNSAFE_RE = new RegExp("[<>&\\u2028\\u2029]", "g");

function safeJsonForScript(value: unknown): string {
  return JSON.stringify(value).replace(UNSAFE_RE, (c) => {
    return "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0");
  });
}

export function FaqJsonLd() {
  const data = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQ_ITEMS.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.a,
      },
    })),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: safeJsonForScript(data) }}
    />
  );
}
