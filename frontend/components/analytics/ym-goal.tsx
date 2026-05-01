"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    ym?: (id: number, action: string, goal: string) => void;
  }
}

export function YmGoal({ goal }: { goal: string }) {
  useEffect(() => {
    const id = Number(process.env.NEXT_PUBLIC_YM_COUNTER_ID);
    if (id && window.ym) {
      window.ym(id, "reachGoal", goal);
    }
  }, [goal]);

  return null;
}
