import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Scale, ArrowLeft } from "lucide-react";
import { ProfileForm } from "@/components/profile/profile-form";

export const metadata: Metadata = {
  title: "Профиль — LawDocs",
  robots: { index: false },
};

interface UserData {
  id: string;
  email: string;
  name: string | null;
  completed_orders_count: number;
}

async function fetchUser(token: string): Promise<UserData | null> {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) return null;
  try {
    const res = await fetch(`${backendUrl}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as UserData;
  } catch {
    return null;
  }
}

export default async function ProfilePage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) redirect("/auth/error?reason=unauthorized");

  const user = await fetchUser(token);
  if (!user) redirect("/auth/error?reason=unauthorized");

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-md mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <Scale className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold text-gray-900">Профиль</h1>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <ProfileForm initialName={user.name} email={user.email} />
        </div>
        <div className="mt-4">
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Мои заказы
          </Link>
        </div>
      </div>
    </main>
  );
}
