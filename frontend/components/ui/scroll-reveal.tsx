"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";

// useLayoutEffect warns during SSR; fall back to useEffect on the server.
const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;

interface ScrollRevealProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  /** Direction to slide from. Default: "bottom" */
  from?: "bottom" | "left" | "none";
}

export function ScrollReveal({
  children,
  className = "",
  delay = 0,
  from = "bottom",
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [armed, setArmed] = useState(false);
  const [visible, setVisible] = useState(false);

  // Progressive enhancement: the server and any no-JS / pre-hydration /
  // reduced-motion render must show content. Only arm the hide-then-reveal
  // once the client can guarantee the element gets revealed. The layout
  // effect runs before paint, so JS users see no flash.
  useIsomorphicLayoutEffect(() => {
    if (
      typeof window === "undefined" ||
      !("IntersectionObserver" in window) ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return;
    }
    setArmed(true);
  }, []);

  useEffect(() => {
    if (!armed) return;
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [armed]);

  const translatePending =
    from === "bottom" ? "translate-y-5" : from === "left" ? "-translate-x-5" : "";

  const hidden = armed && !visible;

  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-out ${
        hidden ? `opacity-0 ${translatePending}` : "opacity-100 translate-y-0 translate-x-0"
      } ${className}`}
      style={{ transitionDelay: visible && delay ? `${delay}ms` : "0ms" }}
    >
      {children}
    </div>
  );
}
