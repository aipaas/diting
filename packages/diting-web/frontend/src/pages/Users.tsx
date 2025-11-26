/**
 * Users Management Page - Admin Only
 */

import { useState, useEffect } from "react";
import { useUser } from "@/contexts/UserContext";
import { AdminGuard } from "@/components/AdminGuard";
import { resetUserPassword } from "@/api/client";

interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

interface CreateUserForm {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  is_admin: boolean;
}

export function Users() {
  return (
    <AdminGuard>
      <UsersContent />
    </AdminGuard>
  );
}

function UsersContent() {
  const { currentUser } = useUser();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [createForm, setCreateForm] = useState<CreateUserForm>({
    username: "",
    email: "",
    password: "",
    full_name: "",
    is_admin: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showResetPasswordModal, setShowResetPasswordModal] = useState(false);
  const [resetPasswordForm, setResetPasswordForm] = useState({
    userId: "",
    username: "",
    newPassword: "",
  });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("token");
      const response = await fetch("/api/v1/users", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (data.code === 200) {
        setUsers(data.data.items);
      }
    } catch (error) {
      console.error("Failed to load users:", error);
    } finally {
      setLoading(false);
    }
  };

  const resetCreateModal = () => {
    setShowCreateModal(false);
    setCreateForm({
      username: "",
      email: "",
      password: "",
      full_name: "",
      is_admin: false,
    });
    setShowPassword(false);
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("/api/v1/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(createForm),
      });
      const data = await response.json();
      
      if (data.code === 201) {
        alert("用户创建成功！");
        resetCreateModal();
        loadUsers();
      } else {
        alert(`创建用户失败：${data.message || "未知错误"}`);
      }
    } catch (error) {
      console.error("Failed to create user:", error);
      alert("创建用户失败");
    }
  };

  const handleDeleteUser = async (userId: string, username: string) => {
    if (userId === currentUser?.id) {
      alert("不能删除自己的账号！");
      return;
    }

    if (!confirm(`确定要删除用户 "${username}" 吗？`)) {
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/api/v1/users/${userId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      
      if (data.code === 200) {
        alert("用户删除成功！");
        loadUsers();
      } else {
        alert(`删除用户失败：${data.message || "未知错误"}`);
      }
    } catch (error) {
      console.error("Failed to delete user:", error);
      alert("删除用户失败");
    }
  };

  const toggleUserStatus = async (userId: string, currentStatus: boolean) => {
    // 不能停用自己的账户
    if (userId === currentUser?.id) {
      alert("不能停用自己的账号！");
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/api/v1/users/${userId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          is_active: !currentStatus,
        }),
      });
      const data = await response.json();
      
      if (data.code === 200) {
        loadUsers();
      } else {
        alert(`更新用户失败：${data.message || "未知错误"}`);
      }
    } catch (error) {
      console.error("Failed to update user:", error);
      alert("更新用户失败");
    }
  };

  // 添加重置密码处理函数
  const handleResetPassword = async (userId: string, username: string) => {
    setResetPasswordForm({
      userId,
      username,
      newPassword: "",
    });
    setShowResetPasswordModal(true);
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await resetUserPassword(resetPasswordForm.userId, resetPasswordForm.newPassword);
      alert("密码重置成功！");
      setShowResetPasswordModal(false);
      setResetPasswordForm({
        userId: "",
        username: "",
        newPassword: "",
      });
    } catch (error: any) {
      console.error("Failed to reset password:", error);
      alert(`密码重置失败：${error?.response?.data?.detail || "未知错误"}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] mx-auto space-y-4 px-4 py-3">
      {/* Users Table Container */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* Header Bar */}
        <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center justify-between gap-4">
            {/* Left: Title and Search */}
            <div className="flex items-center gap-6">
              <h2 className="text-lg font-bold text-gray-900">
                用户管理
              </h2>

              {/* Search Box */}
              <div className="relative w-80">
                <input
                  type="text"
                  placeholder="搜索用户..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all"
                />
                <svg className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </div>

            {/* Right: Create Button */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-gradient-to-r from-brand-500 to-violet-500 text-white text-sm font-medium rounded-lg hover:from-brand-600 hover:to-violet-600 transition-all flex items-center gap-2 shadow-sm hover:shadow whitespace-nowrap"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                </svg>
                创建用户
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                用户名
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                邮箱
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                全名
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                角色
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                状态
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100">
            {users
              .filter(user => {
                const matchesSearch = 
                  user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
                  (user.email && user.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
                  (user.full_name && user.full_name.toLowerCase().includes(searchQuery.toLowerCase()));
                return matchesSearch;
              })
              .map((user) => (
              <tr key={user.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-slate-900">
                    {user.username}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-slate-600">{user.email || "-"}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-slate-600">
                    {user.full_name || "-"}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2.5 py-1 inline-flex text-xs font-semibold rounded-full ${
                      user.is_admin
                        ? "bg-purple-100 text-purple-700"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {user.is_admin ? "管理员" : "普通用户"}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2.5 py-1 inline-flex text-xs font-semibold rounded-full ${
                      user.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {user.is_active ? "激活" : "未激活"}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-3">
                  <button
                    onClick={() => toggleUserStatus(user.id, user.is_active)}
                    disabled={user.id === currentUser?.id}
                    className="text-blue-600 hover:text-blue-800 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors"
                  >
                    {user.is_active ? "停用" : "启用"}
                  </button>
                  <button
                    onClick={() => handleDeleteUser(user.id, user.username)}
                    disabled={user.id === currentUser?.id}
                    className="text-red-600 hover:text-red-800 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors"
                  >
                    删除
                  </button>
                  <button
                    onClick={() => handleResetPassword(user.id, user.username)}
                    disabled={user.id === currentUser?.id}
                    className="text-blue-600 hover:text-blue-800 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors"
                  >
                    重置密码
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-900">创建新用户</h2>
              <button
                onClick={resetCreateModal}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-4">
              {/* Username */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>用户名</span>
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={createForm.username}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, username: e.target.value })
                  }
                  placeholder="请输入用户名"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300"
                />
              </div>

              {/* Email */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>邮箱</span>
                  <span className="text-slate-400 font-normal text-xs">(可选)</span>
                </label>
                <input
                  type="email"
                  value={createForm.email}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, email: e.target.value })
                  }
                  placeholder="user@example.com"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300"
                />
              </div>

              {/* Password */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>密码</span>
                  <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={createForm.password}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, password: e.target.value })
                    }
                    placeholder="至少8位，包含大小写字母和数字"
                    autoComplete="new-password"
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 pr-10 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPassword ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Full Name */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>全名</span>
                  <span className="text-slate-400 font-normal text-xs">(可选)</span>
                </label>
                <input
                  type="text"
                  value={createForm.full_name}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, full_name: e.target.value })
                  }
                  placeholder="请输入全名"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300"
                />
              </div>

              {/* Admin Checkbox */}
              <div className="pt-2">
                <label className="flex items-center gap-2.5 cursor-pointer group">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={createForm.is_admin}
                      onChange={(e) =>
                        setCreateForm({ ...createForm, is_admin: e.target.checked })
                      }
                      className="peer sr-only"
                    />
                    <div className="w-5 h-5 border-2 border-slate-300 rounded bg-white transition-all peer-checked:bg-blue-500 peer-checked:border-blue-500 group-hover:border-slate-400 peer-checked:group-hover:bg-blue-600 peer-checked:group-hover:border-blue-600 flex items-center justify-center">
                      <svg className="w-3 h-3 text-white opacity-0 peer-checked:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  </div>
                  <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900 transition-colors">
                    管理员权限
                  </span>
                </label>
              </div>

              {/* Buttons */}
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={resetCreateModal}
                  className="px-5 py-2.5 bg-slate-100 text-slate-700 text-sm font-medium rounded-xl hover:bg-slate-200 transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition-colors shadow-sm hover:shadow-md"
                >
                  创建
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {showResetPasswordModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-900">重置密码</h2>
              <button
                onClick={() => setShowResetPasswordModal(false)}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
              {/* Username */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>用户名</span>
                </label>
                <input
                  type="text"
                  value={resetPasswordForm.username}
                  readOnly
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300"
                />
              </div>

              {/* New Password */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>新密码</span>
                  <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={resetPasswordForm.newPassword}
                    onChange={(e) =>
                      setResetPasswordForm({ ...resetPasswordForm, newPassword: e.target.value })
                    }
                    placeholder="至少8位，包含大小写字母和数字"
                    autoComplete="new-password"
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 pr-10 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPassword ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Buttons */}
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowResetPasswordModal(false)}
                  className="px-5 py-2.5 bg-slate-100 text-slate-700 text-sm font-medium rounded-xl hover:bg-slate-200 transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 transition-colors shadow-sm hover:shadow-md"
                >
                  重置
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

