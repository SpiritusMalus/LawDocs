import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight, ArrowRight } from "lucide-react";
import { ARTICLES, ARTICLE_CATEGORIES } from "@/lib/articles";
import { buttonVariants } from "@/components/ui/button";

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateStaticParams() {
  return ARTICLES.map((article) => ({
    id: article.id,
  }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const article = ARTICLES.find((a) => a.id === id);

  if (!article) {
    return {
      title: "Статья не найдена",
    };
  }

  return {
    title: `${article.title} | LawDocs`,
    description: article.description,
  };
}

export default async function ArticlePage({ params }: Props) {
  const { id } = await params;
  const article = ARTICLES.find((a) => a.id === id);

  if (!article) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Статья не найдена</h1>
          <Link
            href="/articles"
            className={buttonVariants({ variant: "default" })}
          >
            Вернуться к статьям
          </Link>
        </div>
      </div>
    );
  }

  const relatedArticles = ARTICLES.filter((a) => article.relatedIds.includes(a.id));

  return (
    <>
      {/* Breadcrumb */}
      <nav aria-label="Хлебные крошки" className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-1 text-sm text-gray-500">
          <Link href="/" className="hover:text-gray-900 transition-colors">
            Главная
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
          <Link href="/articles" className="hover:text-gray-900 transition-colors">
            Статьи
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
          <span className="text-gray-900 font-medium truncate">{article.title}</span>
        </div>
      </nav>

      {/* Back-link */}
      <section className="bg-white border-b border-gray-100 px-4 py-4">
        <div className="max-w-3xl mx-auto">
          <Link
            href="/articles"
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            ← Все статьи
          </Link>
        </div>
      </section>

      {/* Article content with sidebar */}
      <div className="bg-gray-50 px-4 py-12">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Main content */}
          <div className="md:col-span-2">
            {/* Hero section */}
            <div className="bg-white rounded-2xl border border-gray-100 p-8 mb-8">
              <div className="mb-4 flex items-center gap-2">
                <span className="text-3xl">{ARTICLE_CATEGORIES[article.category].icon}</span>
                <span className="text-sm px-3 py-1 bg-gray-100 text-gray-600 rounded-full">
                  {ARTICLE_CATEGORIES[article.category].label}
                </span>
              </div>
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 leading-tight">
                {article.title}
              </h1>
              <p className="text-base text-gray-600 mb-6">{article.description}</p>
              <div className="text-sm text-gray-500">
                {article.readTime} мин чтения
              </div>
            </div>

            {/* Article body - prose styling */}
            <div className="bg-white rounded-2xl border border-gray-100 p-8 prose prose-sm max-w-none">
              <div
                dangerouslySetInnerHTML={{ __html: markdownToHtml(article.content) }}
              />
            </div>
          </div>

          {/* Sidebar - desktop only */}
          <aside className="hidden md:block md:col-span-1">
            {relatedArticles.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 p-6 sticky top-20">
                <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <span className="text-lg">📚</span>
                  Похожие статьи
                </h3>
                <div className="space-y-3">
                  {relatedArticles.map((related) => (
                    <Link
                      key={related.id}
                      href={`/articles/${related.id}`}
                      className="block p-3 rounded-lg border border-gray-100 hover:border-primary hover:bg-blue-50 transition-colors group"
                    >
                      <div className="flex items-start gap-2 mb-1">
                        <span className="text-lg shrink-0">{ARTICLE_CATEGORIES[related.category].icon}</span>
                        <h4 className="text-sm font-medium text-gray-900 group-hover:text-primary leading-snug">
                          {related.title}
                        </h4>
                      </div>
                      <p className="text-xs text-gray-500 ml-6">{related.readTime} мин</p>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </aside>
        </div>
      </div>

      {/* Related articles - mobile only */}
      {relatedArticles.length > 0 && (
        <section className="block md:hidden bg-white border-t border-gray-100 px-4 py-12">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
              <span>📚</span> Похожие статьи
            </h2>
            <div className="space-y-3">
              {relatedArticles.map((related) => (
                <Link
                  key={related.id}
                  href={`/articles/${related.id}`}
                  className="block p-4 rounded-xl border border-gray-100 hover:border-primary hover:bg-blue-50 transition-colors group"
                >
                  <div className="flex items-start gap-3 mb-2">
                    <span className="text-2xl shrink-0">{ARTICLE_CATEGORIES[related.category].icon}</span>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-base font-semibold text-gray-900 group-hover:text-primary leading-snug">
                        {related.title}
                      </h3>
                      <p className="text-xs text-gray-500 mt-1">{related.readTime} мин чтения</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Bottom CTA */}
      <section className="bg-gray-900 py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Готовы к действию?</h2>
          <p className="text-gray-400 mb-8">
            Используйте полученные знания для защиты своих прав. Составьте претензию и отстаивайте свои требования.
          </p>
          <Link
            href="/situations"
            className={buttonVariants({ variant: "default", size: "lg" })}
          >
            Подобрать документ
            <ArrowRight className="h-4 w-4 ml-2" />
          </Link>
        </div>
      </section>
    </>
  );
}

// Simple markdown-like to HTML converter for article content
function markdownToHtml(markdown: string): string {
  let html = markdown;

  // Headers
  html = html.replace(/^### (.*?)$/gm, '<h3 className="text-lg font-semibold text-gray-900 mt-6 mb-3">$1</h3>');
  html = html.replace(/^## (.*?)$/gm, '<h2 className="text-xl font-bold text-gray-900 mt-8 mb-4">$1</h2>');
  html = html.replace(/^# (.*?)$/gm, '<h1 className="text-2xl font-bold text-gray-900 mt-8 mb-4">$1</h1>');

  // Paragraphs
  html = html.split('\n\n').map(paragraph => {
    if (paragraph.match(/^[#\-|✓❌]/)) return paragraph;
    if (paragraph.trim() === '') return '';
    return `<p className="mb-4">${paragraph}</p>`;
  }).join('');

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Tables (simplified)
  html = html.replace(/\| (.*?) \|/g, '<td className="border border-gray-200 px-4 py-2">$1</td>');

  // Lists
  html = html.replace(/^✓ (.*?)$/gm, '<li className="list-none pl-6 mb-2 relative before:content-[\'✓\'] before:absolute before:left-0 before:text-green-600">$1</li>');
  html = html.replace(/^❌ (.*?)$/gm, '<li className="list-none pl-6 mb-2 relative before:content-[\'✕\'] before:absolute before:left-0 before:text-red-600">$1</li>');
  html = html.replace(/^- (.*?)$/gm, '<li className="list-disc list-inside mb-2">$1</li>');

  // Blockquotes
  html = html.replace(/^> (.*?)$/gm, '<blockquote className="border-l-4 border-gray-300 pl-4 py-2 mb-4 italic text-gray-600">$1</blockquote>');

  // Line breaks
  html = html.replace(/\n\n/g, '');

  return html;
}
