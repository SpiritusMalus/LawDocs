declare global {
  interface Window {
    ym?: (
      id: number,
      method: "reachGoal" | "hit",
      goal: string,
      params?: Record<string, unknown>
    ) => void;
  }
}

export {};
