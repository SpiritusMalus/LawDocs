"use client";

import { LogOut } from "lucide-react";
import { useState } from "react";

export function LogoutButton() {
  const [isLoading, setIsLoading] = useState(false);

  async function handleLogout() {
    try {
      setIsLoading(true);
      // Call API to delete httpOnly cookie on server
      const res = await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });

      if (!res.ok) {
        console.error("Logout failed:", res.status);
        return;
      }

      // Force full page reload to clear all caches
      window.location.href = "/";
    } catch (err) {
      console.error("Logout error:", err);
      setIsLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      disabled={isLoading}
      className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 border-2 border-red-600 hover:bg-red-50 active:bg-red-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <LogOut className="h-4 w-4" />
      {isLoading ? "Выходим..." : "Выйти"}
    </button>
  );
}
