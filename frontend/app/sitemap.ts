import type { MetadataRoute } from "next";
import { SITUATION_PAGES } from "@/lib/situation-pages";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://lawdocs.ru";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    {
      url: SITE_URL,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/situations`,
      lastModified: now,
      changeFrequency: "weekly" as const,
      priority: 0.9,
    },
    ...SITUATION_PAGES.map((p) => ({
      url: `${SITE_URL}/situations/${p.slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.8,
    })),
  ];
}
