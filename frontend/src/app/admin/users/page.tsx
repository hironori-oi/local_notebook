"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Users,
  UserPlus,
  Edit2,
  Trash2,
  Shield,
  User as UserIcon,
  Loader2,
  ArrowLeft,
  Search,
} from "lucide-react";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Modal } from "../../../components/ui/Modal";
import {
  getUser,
  isAuthenticated,
  isAdmin,
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  AdminUser,
  AdminUserCreate,
  AdminUserUpdate,
} from "../../../lib/apiClient";

export default function AdminUsersPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);

  // Form state
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");

  // Create form
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "user">("user");

  // Edit form
  const [editDisplayName, setEditDisplayName] = useState("");
  const [editRole, setEditRole] = useState<"admin" | "user">("user");
  const [editPassword, setEditPassword] = useState("");

  // Check auth and admin
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }

    const currentUser = getUser();
    if (!isAdmin(currentUser)) {
      router.push("/");
      return;
    }

    loadUsers();
  }, [router]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await listUsers();
      setUsers(data.users);
    } catch (error) {
      console.error("Failed to load users:", error);
      alert("ユーザー一覧の取得に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      setFormLoading(true);
      setFormError("");

      const data: AdminUserCreate = {
        username: newUsername,
        password: newPassword,
        display_name: newDisplayName,
        role: newRole,
      };

      await createUser(data);
      await loadUsers();
      setShowCreateModal(false);
      resetCreateForm();
    } catch (error) {
      setFormError(
        error instanceof Error ? error.message : "ユーザーの作成に失敗しました"
      );
    } finally {
      setFormLoading(false);
    }
  };

  const handleEdit = async () => {
    if (!selectedUser) return;

    try {
      setFormLoading(true);
      setFormError("");

      const data: AdminUserUpdate = {};
      if (editDisplayName !== selectedUser.display_name) {
        data.display_name = editDisplayName;
      }
      if (editRole !== selectedUser.role) {
        data.role = editRole;
      }
      if (editPassword) {
        data.password = editPassword;
      }

      await updateUser(selectedUser.id, data);
      await loadUsers();
      setShowEditModal(false);
      setSelectedUser(null);
    } catch (error) {
      setFormError(
        error instanceof Error ? error.message : "ユーザーの更新に失敗しました"
      );
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;

    try {
      setFormLoading(true);
      setFormError("");

      await deleteUser(selectedUser.id);
      await loadUsers();
      setShowDeleteModal(false);
      setSelectedUser(null);
    } catch (error) {
      setFormError(
        error instanceof Error ? error.message : "ユーザーの削除に失敗しました"
      );
    } finally {
      setFormLoading(false);
    }
  };

  const resetCreateForm = () => {
    setNewUsername("");
    setNewPassword("");
    setNewDisplayName("");
    setNewRole("user");
    setFormError("");
  };

  const openEditModal = (user: AdminUser) => {
    setSelectedUser(user);
    setEditDisplayName(user.display_name);
    setEditRole(user.role);
    setEditPassword("");
    setFormError("");
    setShowEditModal(true);
  };

  const openDeleteModal = (user: AdminUser) => {
    setSelectedUser(user);
    setFormError("");
    setShowDeleteModal(true);
  };

  const filteredUsers = users.filter(
    (user) =>
      user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.display_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/")}
              className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-surface-600 dark:text-surface-400" />
            </button>
            <div className="flex items-center gap-2">
              <Users className="w-6 h-6 text-primary-500" />
              <h1 className="text-xl font-bold text-surface-900 dark:text-surface-100">
                ユーザー管理
              </h1>
            </div>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
            leftIcon={<UserPlus className="w-4 h-4" />}
          >
            ユーザー追加
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Search */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="ユーザーを検索..."
              className="pl-10"
            />
          </div>
        </div>

        {/* Users table */}
        <div className="bg-white dark:bg-surface-800 rounded-2xl shadow-soft overflow-hidden">
          <table className="w-full">
            <thead className="bg-surface-50 dark:bg-surface-700/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase tracking-wider">
                  ユーザー
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase tracking-wider">
                  ロール
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase tracking-wider">
                  作成日
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-surface-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
              {filteredUsers.map((user) => (
                <tr
                  key={user.id}
                  className="hover:bg-surface-50 dark:hover:bg-surface-700/30 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-accent-400 flex items-center justify-center text-white font-medium">
                        {user.display_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-surface-900 dark:text-surface-100">
                          {user.display_name}
                        </p>
                        <p className="text-sm text-surface-500">
                          @{user.username}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                        user.role === "admin"
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400"
                          : "bg-surface-100 text-surface-600 dark:bg-surface-700 dark:text-surface-400"
                      }`}
                    >
                      {user.role === "admin" ? (
                        <Shield className="w-3 h-3" />
                      ) : (
                        <UserIcon className="w-3 h-3" />
                      )}
                      {user.role === "admin" ? "管理者" : "一般"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-surface-500">
                    {new Date(user.created_at).toLocaleDateString("ja-JP")}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => openEditModal(user)}
                        className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 text-surface-500 hover:text-primary-500 transition-colors"
                        title="編集"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => openDeleteModal(user)}
                        className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-surface-500 hover:text-red-500 transition-colors"
                        title="削除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredUsers.length === 0 && (
            <div className="px-6 py-12 text-center text-surface-500">
              {searchQuery
                ? "検索結果がありません"
                : "ユーザーがいません"}
            </div>
          )}
        </div>
      </main>

      {/* Create Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false);
          resetCreateForm();
        }}
        title="ユーザー追加"
      >
        <div className="space-y-4">
          {formError && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              ユーザー名
            </label>
            <Input
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              placeholder="username"
            />
            <p className="mt-1 text-xs text-surface-500">
              英数字、アンダースコア、ハイフンのみ
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              表示名
            </label>
            <Input
              value={newDisplayName}
              onChange={(e) => setNewDisplayName(e.target.value)}
              placeholder="山田 太郎"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              パスワード
            </label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="********"
            />
            <p className="mt-1 text-xs text-surface-500">
              8文字以上、大文字・小文字・数字・特殊文字を含む
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              ロール
            </label>
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value as "admin" | "user")}
              className="w-full px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-600 bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="user">一般ユーザー</option>
              <option value="admin">管理者</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              variant="ghost"
              onClick={() => {
                setShowCreateModal(false);
                resetCreateForm();
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              isLoading={formLoading}
              disabled={!newUsername || !newPassword || !newDisplayName}
            >
              作成
            </Button>
          </div>
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedUser(null);
        }}
        title="ユーザー編集"
      >
        <div className="space-y-4">
          {formError && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              ユーザー名
            </label>
            <Input value={selectedUser?.username || ""} disabled />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              表示名
            </label>
            <Input
              value={editDisplayName}
              onChange={(e) => setEditDisplayName(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              新しいパスワード（変更する場合のみ）
            </label>
            <Input
              type="password"
              value={editPassword}
              onChange={(e) => setEditPassword(e.target.value)}
              placeholder="空欄で変更なし"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">
              ロール
            </label>
            <select
              value={editRole}
              onChange={(e) => setEditRole(e.target.value as "admin" | "user")}
              className="w-full px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-600 bg-white dark:bg-surface-700 text-surface-900 dark:text-surface-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="user">一般ユーザー</option>
              <option value="admin">管理者</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              variant="ghost"
              onClick={() => {
                setShowEditModal(false);
                setSelectedUser(null);
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="primary"
              onClick={handleEdit}
              isLoading={formLoading}
            >
              保存
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setSelectedUser(null);
        }}
        title="ユーザー削除"
      >
        <div className="space-y-4">
          {formError && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
              {formError}
            </div>
          )}

          <p className="text-surface-600 dark:text-surface-400">
            <span className="font-medium text-surface-900 dark:text-surface-100">
              {selectedUser?.display_name}
            </span>
            （@{selectedUser?.username}）を削除しますか？
          </p>
          <p className="text-sm text-red-500">
            この操作は取り消せません。ユーザーに関連するすべてのデータも削除されます。
          </p>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              variant="ghost"
              onClick={() => {
                setShowDeleteModal(false);
                setSelectedUser(null);
              }}
            >
              キャンセル
            </Button>
            <Button
              variant="danger"
              onClick={handleDelete}
              isLoading={formLoading}
            >
              削除
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
