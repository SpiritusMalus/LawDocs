import { notFound } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { ChevronRight } from "lucide-react";
import type { WizardStep } from "@/lib/wizard-types";
import { getSituationPage } from "@/lib/situation-pages";
import { WizardShell } from "@/components/wizard/wizard-shell";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ situation: string }>;
}): Promise<Metadata> {
  const { situation } = await params;
  const page = getSituationPage(situation);
  if (!page) return {};
  return {
    title: `Оформить: ${page.h1} — LawDocs`,
    description: page.seoDescription,
    robots: { index: false },
  };
}

export default async function WizardPage({
  params,
}: {
  params: Promise<{ situation: string }>;
}) {
  const { situation } = await params;

  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) notFound();

  let steps: WizardStep[] = [];
  let fetchError = false;
  try {
    const res = await fetch(`${backendUrl}/api/v1/situations/${situation}`, {
      cache: "no-store",
    });
    if (res.status === 404) notFound();
    if (!res.ok) {
      fetchError = true;
    } else {
      const data: { wizard_steps: WizardStep[] } = await res.json();
      steps = data.wizard_steps;
    }
  } catch {
    fetchError = true;
  }

  const page = getSituationPage(situation);
  const cookieStore = await cookies();
  const isAuthenticated = !!cookieStore.get("access_token")?.value;

  return (
    <>
      <nav className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-1 text-sm text-gray-500">
          <Link href="/" className="hover:text-gray-900 transition-colors">
            Главная
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
          {page && (
            <>
              <Link
                href={`/situations/${situation}`}
                className="hover:text-gray-900 transition-colors truncate max-w-[160px]"
              >
                {page.h1}
              </Link>
              <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
            </>
          )}
          <span className="text-gray-900 font-medium">Оформить документ</span>
        </div>
      </nav>

      <section className="bg-gray-50 min-h-[calc(100vh-8rem)] py-10 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="mb-8">
            <div className="flex items-start justify-between gap-4 mb-2">
              <h1 className="text-2xl font-bold text-gray-900">
                {page?.h1 ?? "Оформить документ"}
              </h1>
              <span className="shrink-0 inline-flex items-center px-3 py-1 rounded-full bg-primary/8 border border-primary/20 text-primary text-sm font-semibold">
                199&nbsp;₽
              </span>
            </div>
            <p className="text-gray-500 text-sm">
              Ответьте на вопросы — составим документ со ссылками на закон и инструкцией куда
              отправить.
            </p>
          </div>

          <WizardShell
            steps={steps}
            situationId={situation}
            hasBackend={true}
            isAuthenticated={isAuthenticated}
            error={fetchError}
          />
        </div>
      </section>
    </>
  );
}
