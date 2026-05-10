"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface Props {
  hasGenerating: boolean;
}

const POLL_INTERVAL_MS = 5000;

export function DashboardPoller({ hasGenerating }: Props) {
  const router = useRouter();

  useEffect(() => {
    if (!hasGenerating) return;
    const id = setInterval(() => router.refresh(), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [hasGenerating, router]);

  return null;
}
