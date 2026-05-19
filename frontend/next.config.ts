import type { NextConfig } from "next";

const getSecurityHeaders = () => {
  const isDev = process.env.NODE_ENV === "development";
  const scriptSrc = ["'self'", "'unsafe-inline'", "mc.yandex.ru", "mc.yandex.com"];
  if (isDev) scriptSrc.push("'unsafe-eval'"); // React dev needs eval for stack traces

  return [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "X-XSS-Protection", value: "1; mode=block" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
    {
      key: "Content-Security-Policy",
      value: [
        "default-src 'self'",
        `script-src ${scriptSrc.join(" ")}`,
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: mc.yandex.ru mc.yandex.com yandex.ru",
        "connect-src 'self' mc.yandex.ru mc.yandex.com api.telegram.org",
        "font-src 'self'",
        "frame-src 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
      ].join("; "),
    },
  ];
};

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: getSecurityHeaders(),
      },
    ];
  },
};

export default nextConfig;
