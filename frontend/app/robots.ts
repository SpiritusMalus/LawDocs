import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://law-docs.ru";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: ["ClaudeBot", "anthropic-ai"],
        allow: "/",
      },
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/legal/", "/thanks"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
