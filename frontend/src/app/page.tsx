"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Building2,
  FileText,
  Youtube,
  BookOpen,
  Sparkles,
  ArrowRight,
  Presentation,
} from "lucide-react";
import {
  isAuthenticated,
  getUser,
  User,
} from "../lib/apiClient";
import { Header } from "../components/layout/Header";
import { LoadingScreen } from "../components/ui/Spinner";

interface FeatureCard {
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  color: string;
  bgGradient: string;
}

const features: FeatureCard[] = [
  {
    title: "審議会管理",
    description: "審議会の議事録や資料をアップロードし、AIによる要約・分析・検索を行います。会議内容を効率的に管理できます。",
    icon: <Building2 className="w-10 h-10" />,
    href: "/councils",
    color: "text-blue-600 dark:text-blue-400",
    bgGradient: "from-blue-500/10 to-blue-600/10 dark:from-blue-500/20 dark:to-blue-600/20",
  },
  {
    title: "ノートブック",
    description: "社内文書やPDF、テキストファイルをアップロードし、AIによる検索・質問応答ができます。ナレッジベースを構築できます。",
    icon: <FileText className="w-10 h-10" />,
    href: "/notebooks",
    color: "text-primary-600 dark:text-primary-400",
    bgGradient: "from-primary-500/10 to-accent-500/10 dark:from-primary-500/20 dark:to-accent-500/20",
  },
  {
    title: "SlideStudio",
    description: "AIがドキュメントをチェックし、スライドを自動生成します。プレゼンテーション資料の作成を効率化できます。",
    icon: <Presentation className="w-10 h-10" />,
    href: "/document-checker",
    color: "text-purple-600 dark:text-purple-400",
    bgGradient: "from-purple-500/10 to-purple-600/10 dark:from-purple-500/20 dark:to-purple-600/20",
  },
  {
    title: "YouTube文字起こし",
    description: "YouTube動画のURLを入力して、音声を自動でテキストに変換します。会議録画や講演動画のテキスト化に便利です。",
    icon: <Youtube className="w-10 h-10" />,
    href: "/transcription",
    color: "text-red-600 dark:text-red-400",
    bgGradient: "from-red-500/10 to-red-600/10 dark:from-red-500/20 dark:to-red-600/20",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Check authentication on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setUser(getUser());
    setAuthChecked(true);
  }, [router]);

  // Don't render anything until auth check is complete
  if (!authChecked) {
    return <LoadingScreen message="読み込み中..." />;
  }

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950">
      <Header user={user} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 mb-6 shadow-lg">
            <BookOpen className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-surface-900 dark:text-surface-100 mb-4">
            AI ノートブック
          </h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 max-w-2xl mx-auto">
            社内ナレッジベースプラットフォーム
          </p>
          <p className="text-surface-400 dark:text-surface-500 mt-2">
            ドキュメント管理、会議録分析、動画文字起こしをAIがサポートします
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
          {features.map((feature, index) => (
            <Link
              key={feature.href}
              href={feature.href}
              className="group relative bg-white dark:bg-surface-900 rounded-2xl shadow-soft hover:shadow-lg transition-all duration-300 overflow-hidden border border-surface-200/50 dark:border-surface-700/50 hover:border-primary-300 dark:hover:border-primary-600"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              {/* Card Content */}
              <div className="p-6">
                {/* Icon */}
                <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${feature.bgGradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                  <span className={feature.color}>{feature.icon}</span>
                </div>

                {/* Title */}
                <h2 className="text-xl font-semibold text-surface-900 dark:text-surface-100 mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                  {feature.title}
                </h2>

                {/* Description */}
                <p className="text-sm text-surface-500 dark:text-surface-400 leading-relaxed mb-4">
                  {feature.description}
                </p>

                {/* Action */}
                <div className="flex items-center gap-2 text-sm font-medium text-primary-600 dark:text-primary-400 group-hover:gap-3 transition-all">
                  <span>開く</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>

              {/* Hover gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary-500/5 to-accent-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
            </Link>
          ))}
        </div>

        {/* Footer hint */}
        <div className="text-center mt-12">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-surface-100 dark:bg-surface-800 text-sm text-surface-500 dark:text-surface-400">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>ヘッダーのアイコンからいつでも各機能にアクセスできます</span>
          </div>
        </div>
      </main>
    </div>
  );
}
