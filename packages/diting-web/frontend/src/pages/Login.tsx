import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "@/api/client";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      const response = await login({ username, password });
      
      // 保存token和认证信息
      localStorage.setItem("access_token", response.access_token);
      localStorage.setItem("token", response.access_token); // 兼容
      if (response.refresh_token) {
      localStorage.setItem("refresh_token", response.refresh_token);
      }
      localStorage.setItem("isAuthenticated", "true");
      
      // 加载用户信息
      // UserContext 会自动加载，或者直接跳转
      navigate("/dashboard");
      
      // 刷新页面以加载用户上下文
      window.location.reload();
    } catch (err: any) {
      console.error("Login error:", err);
      setError(err.response?.data?.detail || err.response?.data?.msg || "登录失败，请检查用户名和密码");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-gradient-to-r from-indigo-100 via-slate-50 to-white relative">
      {/* 全局背景装饰 - 多层次 */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* 柔和的品牌色光晕 */}
        <div className="absolute top-0 left-0 w-96 h-96 bg-indigo-200/30 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-32 w-80 h-80 bg-purple-200/30 rounded-full blur-3xl"></div>
        
        {/* 分散的轨道圈 - 增强可见度 */}
        <div className="absolute left-[5%] top-40 opacity-[0.15]">
          <svg width="200" height="200" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="40" stroke="#6366F1" strokeWidth="2" fill="none" opacity="0.7"/>
            <circle cx="100" cy="100" r="70" stroke="#6366F1" strokeWidth="1.5" fill="none" opacity="0.5" strokeDasharray="4 6"/>
          </svg>
        </div>
        
        <div className="absolute left-[25%] top-20 opacity-[0.12]">
          <svg width="180" height="180" viewBox="0 0 180 180">
            <circle cx="90" cy="90" r="50" stroke="#8B5CF6" strokeWidth="2" fill="none" opacity="0.6"/>
            <circle cx="90" cy="90" r="80" stroke="#8B5CF6" strokeWidth="1.5" fill="none" opacity="0.4" strokeDasharray="3 5"/>
          </svg>
        </div>
        
        <div className="absolute left-[15%] bottom-32 opacity-[0.13]">
          <svg width="160" height="160" viewBox="0 0 160 160">
            <circle cx="80" cy="80" r="35" stroke="#D946EF" strokeWidth="2" fill="none" opacity="0.6"/>
            <circle cx="80" cy="80" r="60" stroke="#D946EF" strokeWidth="1.5" fill="none" opacity="0.4"/>
          </svg>
        </div>
        
        {/* 漂浮粒子 - 增强可见度 */}
        <div className="absolute left-[8%] top-[25%] w-2 h-2 bg-indigo-400/50 rounded-full"></div>
        <div className="absolute left-[18%] top-[35%] w-1.5 h-1.5 bg-purple-400/45 rounded-full"></div>
        <div className="absolute left-[12%] top-[55%] w-2.5 h-2.5 bg-indigo-300/40 rounded-full"></div>
        <div className="absolute left-[22%] top-[65%] w-1.5 h-1.5 bg-fuchsia-400/50 rounded-full"></div>
        <div className="absolute left-[28%] top-[45%] w-2 h-2 bg-purple-300/40 rounded-full"></div>
        <div className="absolute left-[32%] top-[30%] w-1.5 h-1.5 bg-indigo-400/45 rounded-full"></div>
        
        {/* 节点连线 */}
        <div className="absolute left-8 bottom-24 opacity-[0.15]">
          <svg width="280" height="140" viewBox="0 0 280 140" fill="none">
            <circle cx="20" cy="100" r="2.5" fill="#8B5CF6"/>
            <circle cx="50" cy="80" r="2.5" fill="#8B5CF6"/>
            <circle cx="90" cy="60" r="2.5" fill="#8B5CF6"/>
            <line x1="20" y1="100" x2="50" y2="80" stroke="#8B5CF6" strokeWidth="1" opacity="0.4" strokeDasharray="2 3"/>
            <line x1="50" y1="80" x2="90" y2="60" stroke="#8B5CF6" strokeWidth="1" opacity="0.4" strokeDasharray="2 3"/>
          </svg>
        </div>
        
        {/* 轻微网格 */}
        <div className="absolute inset-0 opacity-[0.015]" style={{
          backgroundImage: 'linear-gradient(rgba(99,102,241,1) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,1) 1px, transparent 1px)',
          backgroundSize: '40px 40px'
        }}></div>
      </div>

      {/* 左侧：品牌展示区 */}
      <div className="hidden lg:flex lg:w-[45%] relative">
        {/* 内容区 - 上中下分布 */}
        <div className="relative z-10 flex flex-col justify-between p-12 text-slate-800 w-full">
          {/* 顶部Logo */}
          <div className="flex items-center gap-4">
            <img src="/diting.svg?v=2" alt="Diting Logo" className="w-14 h-14 rounded-2xl" />
            <div>
              <h1 className="text-3xl font-bold">Diting</h1>
              <p className="text-slate-600 text-sm mt-1">AI 评估与数据增强平台</p>
            </div>
          </div>

          {/* 中部功能介绍 - 紧凑列表 */}
          <div className="space-y-4 max-w-md">
            <div className="flex gap-3 items-start">
              <svg className="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h3 className="text-lg font-semibold mb-1 text-slate-800">智能评估</h3>
                <p className="text-slate-600 text-sm leading-relaxed">全方位多维度评估体系，精准洞察模型质量与性能表现</p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <svg className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              <div>
                <h3 className="text-lg font-semibold mb-1 text-slate-800">数据增强</h3>
                <p className="text-slate-600 text-sm leading-relaxed">支持数据合成、负样本挖掘、数据蒸馏等多种增强方式</p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <svg className="w-5 h-5 text-fuchsia-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <div>
                <h3 className="text-lg font-semibold mb-1 text-slate-800">智能优化</h3>
                <p className="text-slate-600 text-sm leading-relaxed">持续优化提示词与参数配置，提升模型响应质量</p>
              </div>
            </div>
          </div>

          {/* 底部版权 */}
          <div className="text-slate-500 text-sm">
            © 2025 Diting. All rights reserved.
          </div>
        </div>
      </div>

      {/* 右侧：登录表单区 */}
      <div className="flex-1 flex items-center justify-center p-8 relative z-10">
        <div className="w-full max-w-md">
          {/* 移动端Logo */}
          <div className="lg:hidden mb-8 text-center">
            <div className="inline-flex items-center gap-3 mb-2">
              <img src="/diting.svg?v=2" alt="Diting Logo" className="w-12 h-12 rounded-2xl" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-fuchsia-600 bg-clip-text text-transparent">Diting</h1>
          </div>
            <p className="text-gray-500 text-sm">AI 评估与数据增强平台</p>
        </div>

          {/* 登录卡片 - 优化阴影 */}
          <div className="bg-white rounded-3xl shadow-2xl shadow-indigo-100/50 ring-1 ring-slate-200/50 p-8 lg:p-10">
            <h2 className="text-2xl font-semibold text-gray-800 mb-8">欢迎回来</h2>
          
          {/* Error Message */}
          {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm mb-6">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span>{error}</span>
              </div>
            </div>
          )}
          
            <form onSubmit={handleSubmit} className="space-y-5" autoComplete="on">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                用户名
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <input
                  type="text"
                  id="username"
                  name="username"
                  autoComplete="username"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                    className="w-full h-12 pl-12 pr-4 border border-gray-200 rounded-2xl placeholder:text-gray-400 text-gray-800 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent focus:ring-offset-2 transition-all"
                  placeholder="请输入用户名"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                密码
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <input
                  type="password"
                  id="password"
                  name="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                    className="w-full h-12 pl-12 pr-4 border border-gray-200 rounded-2xl placeholder:text-gray-400 text-gray-800 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent focus:ring-offset-2 transition-all"
                  placeholder="请输入密码"
                  required
                />
              </div>
            </div>

            {/* Remember & Forgot */}
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center">
                  <input type="checkbox" className="w-4 h-4 text-brand-600 rounded focus:ring-brand-500" />
                <span className="ml-2 text-gray-600">记住我</span>
              </label>
                <a href="#" className="text-brand-600 hover:text-brand-700 font-medium">
                忘记密码？
              </a>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
                className="w-full h-12 bg-gradient-to-r from-brand-500 to-violet-500 text-white rounded-2xl font-semibold shadow-lg shadow-indigo-200/50 hover:shadow-xl transform hover:scale-[1.01] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  登录中...
                </span>
              ) : (
                "登录"
              )}
            </button>
          </form>

          {/* Contact Admin */}
          <p className="mt-6 text-center text-sm text-gray-600">
            还没有账号？请联系管理员创建
          </p>
        </div>
        </div>
      </div>

      <style>{`
        @keyframes rotate-sweep {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .radar-sweep {
          animation: rotate-sweep 12s linear infinite;
        }
        @keyframes dash-move {
          to { stroke-dashoffset: -120; }
        }
        .dash-flow {
          stroke-dasharray: 6 8;
          stroke-linecap: round;
          animation: dash-move 6s linear infinite;
        }
        @keyframes chart-move {
          to { stroke-dashoffset: -300; }
        }
        .chart-dash {
          stroke-dasharray: 8 10;
          animation: chart-move 8s linear infinite;
        }
        @keyframes pulse-dot {
          0%, 100% { transform: scale(1); opacity: 0.6; }
          50% { transform: scale(1.25); opacity: 1; }
        }
        .pulse-dot {
          transform-origin: center;
          animation: pulse-dot 2.4s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
