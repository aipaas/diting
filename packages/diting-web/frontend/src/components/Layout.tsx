import { Link, NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import { useUser } from "@/contexts/UserContext";

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser, isAdmin, logout } = useUser();
  const username = currentUser?.username || currentUser?.email || "用户";
  const [evaluationExpanded, setEvaluationExpanded] = useState(
    location.pathname.startsWith("/evaluation")
  );
  const [synthesisExpanded, setSynthesisExpanded] = useState(
    location.pathname.startsWith("/synthesis")
  );

  // Keep menus expanded when on respective pages
  useEffect(() => {
    if (location.pathname.startsWith("/evaluation")) {
      setEvaluationExpanded(true);
    }
    if (location.pathname.startsWith("/synthesis")) {
      setSynthesisExpanded(true);
    }
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div data-theme="corporate" className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="p-5 border-b border-gray-200">
          <Link to="/dashboard" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <img src="/diting.svg?v=2" alt="Diting Logo" className="w-10 h-10 rounded-xl shadow-sm" />
            <div>
              <h1 className="text-lg font-bold text-gray-900">Diting</h1>
              <p className="text-xs text-gray-500 mt-0.5">AI 评估与数据增强</p>
            </div>
          </Link>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 p-4 space-y-1">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              }`
            }
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            仪表板
          </NavLink>

          {/* Evaluation Center with Submenu */}
          <div>
            <button
              onClick={() => setEvaluationExpanded(!evaluationExpanded)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                location.pathname.startsWith("/evaluation")
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
              <span className="flex-1 text-left">评估中心</span>
              <svg
                className={`w-4 h-4 transition-transform ${evaluationExpanded ? "rotate-180" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* Submenu */}
            {evaluationExpanded && (
              <div className="ml-4 mt-1 space-y-1 border-l-2 border-brand-100 pl-4">
                <NavLink
                  to="/evaluation/tasks"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                      isActive
                        ? "bg-brand-50 text-brand-700 font-medium"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`
                  }
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  评估任务
                </NavLink>
                <NavLink
                  to="/evaluation/evaluators"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                      isActive
                        ? "bg-brand-50 text-brand-700 font-medium"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`
                  }
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                  评估器
                </NavLink>
                <NavLink
                  to="/evaluation/metrics"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                      isActive
                        ? "bg-brand-50 text-brand-700 font-medium"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`
                  }
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                  </svg>
                  评估维度
                </NavLink>
              </div>
            )}
          </div>

          {/* Data Synthesis with Submenu */}
          <div>
            <button
              onClick={() => setSynthesisExpanded(!synthesisExpanded)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                location.pathname.startsWith("/synthesis")
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              <span className="flex-1 text-left">数据增强</span>
              <svg
                className={`w-4 h-4 transition-transform ${synthesisExpanded ? "rotate-180" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* Submenu */}
            {synthesisExpanded && (
              <div className="ml-4 mt-1 space-y-1 border-l-2 border-brand-100 pl-4">
                <NavLink
                  to="/synthesis/generation"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                      isActive
                        ? "bg-brand-50 text-brand-700 font-medium"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`
                  }
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                  </svg>
                  智能生成
                </NavLink>
                <NavLink
                  to="/synthesis/hard-negative"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                      isActive
                        ? "bg-brand-50 text-brand-700 font-medium"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`
                  }
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  负样本挖掘
                </NavLink>
                <NavLink
                  to="/synthesis/distillation"
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                      isActive
                        ? "bg-brand-50 text-brand-700 font-medium"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`
                  }
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  数据蒸馏
                </NavLink>
              </div>
            )}
          </div>

          <NavLink
            to="/datasets"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              }`
            }
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
            数据集
          </NavLink>

          <NavLink
            to="/models"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              }`
            }
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
            模型管理
          </NavLink>

          <NavLink
            to="/prompts"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              }`
            }
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            提示词仓库
          </NavLink>

          <NavLink
            to="/optimization"
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              }`
            }
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            智能优化
          </NavLink>

          {/* Admin Only Menu */}
          {isAdmin && (
            <>
              <div className="border-t border-gray-200 my-2"></div>
              <NavLink
                to="/users"
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                    isActive
                      ? "bg-purple-50 text-purple-700 font-medium"
                      : "text-purple-600 hover:bg-purple-50"
                  }`
                }
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                用户管理
                <span className="ml-auto px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full font-medium">
                  Admin
                </span>
              </NavLink>
            </>
          )}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-gray-200">
          <div className="dropdown dropdown-top dropdown-end w-full">
            <label tabIndex={0} className="btn btn-ghost w-full justify-start px-4 py-3 hover:bg-gray-50">
              <div className="flex items-center gap-3 w-full">
                <div className="w-9 h-9 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold flex-shrink-0">
                  {username.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 text-left">
                  <div className="text-sm font-medium text-gray-900">{username}</div>
                  <div className="text-xs text-gray-500">{isAdmin ? "管理员" : "普通用户"}</div>
                </div>
                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </label>
            <ul tabIndex={0} className="mb-2 p-2 shadow-xl menu dropdown-content bg-white rounded-lg border border-gray-200 w-56">
              <li>
                <a className="flex items-center gap-3 py-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  个人资料
                </a>
              </li>
              <li>
                <a className="flex items-center gap-3 py-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  设置
                </a>
              </li>
              <div className="divider my-1"></div>
              <li>
                <button onClick={handleLogout} className="flex items-center gap-3 py-2 text-red-600 hover:bg-red-50">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  退出登录
                </button>
              </li>
            </ul>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Main Content */}
        <main className="flex-1 p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

