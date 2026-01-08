"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  Key,
  Save,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
} from "lucide-react";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { isAuthenticated, getUser, changePassword, User as UserType } from "../../../lib/apiClient";

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserType | null>(null);
  const [loading, setLoading] = useState(true);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  // Check auth and load user
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    const currentUser = getUser();
    setUser(currentUser);
    setLoading(false);
  }, [router]);

  const validatePassword = (password: string): string | null => {
    if (password.length < 8) {
      return "パスワードは8文字以上である必要があります";
    }
    if (!/[a-z]/.test(password)) {
      return "パスワードには小文字を含める必要があります";
    }
    if (!/[A-Z]/.test(password)) {
      return "パスワードには大文字を含める必要があります";
    }
    if (!/\d/.test(password)) {
      return "パスワードには数字を含める必要があります";
    }
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
      return "パスワードには特殊文字（!@#$%^&*など）を含める必要があります";
    }
    return null;
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);

    // Validation
    if (!currentPassword) {
      setPasswordError("現在のパスワードを入力してください");
      return;
    }

    if (!newPassword) {
      setPasswordError("新しいパスワードを入力してください");
      return;
    }

    const validationError = validatePassword(newPassword);
    if (validationError) {
      setPasswordError(validationError);
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("新しいパスワードと確認用パスワードが一致しません");
      return;
    }

    if (currentPassword === newPassword) {
      setPasswordError("新しいパスワードは現在のパスワードと異なる必要があります");
      return;
    }

    setChangingPassword(true);

    try {
      await changePassword(currentPassword, newPassword);
      setPasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      // Clear success message after 3 seconds
      setTimeout(() => setPasswordSuccess(false), 3000);
    } catch (error) {
      setPasswordError(error instanceof Error ? error.message : "パスワードの変更に失敗しました");
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-50 dark:bg-surface-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-900">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-surface-800/80 backdrop-blur-xl border-b border-surface-200 dark:border-surface-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-surface-600 dark:text-surface-400" />
            </button>
            <div className="flex items-center gap-2">
              <User className="w-6 h-6 text-primary-500" />
              <h1 className="text-xl font-bold text-surface-900 dark:text-surface-100">
                ユーザー情報
              </h1>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* User Info Section */}
        <section className="bg-white dark:bg-surface-800 rounded-2xl p-6 shadow-soft">
          <div className="flex items-center gap-2 mb-4">
            <User className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
              アカウント情報
            </h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-500 dark:text-surface-400 mb-1">
                ユーザー名
              </label>
              <p className="text-surface-900 dark:text-surface-100 font-medium">
                @{user?.username}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-500 dark:text-surface-400 mb-1">
                表示名
              </label>
              <p className="text-surface-900 dark:text-surface-100 font-medium">
                {user?.display_name}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-500 dark:text-surface-400 mb-1">
                ロール
              </label>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                user?.role === "admin"
                  ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300"
                  : "bg-surface-100 dark:bg-surface-700 text-surface-600 dark:text-surface-400"
              }`}>
                {user?.role === "admin" ? "管理者" : "ユーザー"}
              </span>
            </div>
          </div>
        </section>

        {/* Password Change Section */}
        <section className="bg-white dark:bg-surface-800 rounded-2xl p-6 shadow-soft">
          <div className="flex items-center gap-2 mb-4">
            <Key className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
              パスワード変更
            </h2>
          </div>

          <form onSubmit={handleChangePassword} className="space-y-4">
            {/* Current Password */}
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                現在のパスワード
              </label>
              <div className="relative">
                <Input
                  type={showCurrentPassword ? "text" : "password"}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="現在のパスワードを入力"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600"
                >
                  {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* New Password */}
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                新しいパスワード
              </label>
              <div className="relative">
                <Input
                  type={showNewPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="新しいパスワードを入力"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600"
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="mt-1 text-xs text-surface-500">
                8文字以上、大文字・小文字・数字・特殊文字を含む
              </p>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
                新しいパスワード（確認）
              </label>
              <div className="relative">
                <Input
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="新しいパスワードを再入力"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error message */}
            {passwordError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {passwordError}
              </div>
            )}

            {/* Success message */}
            {passwordSuccess && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-sm">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                パスワードを変更しました
              </div>
            )}

            {/* Submit button */}
            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                isLoading={changingPassword}
                leftIcon={<Save className="w-4 h-4" />}
                disabled={!currentPassword || !newPassword || !confirmPassword}
              >
                パスワードを変更
              </Button>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}
