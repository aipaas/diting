import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { getDashboardStatistics } from "@/api/client";
import type { DashboardStatisticsResponse } from "@/types/api";

export default function Dashboard() {
  const [statistics, setStatistics] = useState<DashboardStatisticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchStatistics = async () => {
      try {
        setLoading(true);
        const data = await getDashboardStatistics();
        setStatistics(data);
      } catch (err: any) {
        console.error("Failed to fetch statistics:", err);
        setError("获取统计数据失败");
      } finally {
        setLoading(false);
      }
    };

    fetchStatistics();
  }, []);


  const quickActions = [
    { 
      title: "评估中心", 
      description: "管理评估维度和执行评估",
      color: "blue",
      link: "/evaluation/tasks"
    },
    {
      title: "数据增强",
      description: "数据合成、负样本挖掘、数据蒸馏",
      color: "purple",
      link: "/synthesis/generation"
    },
    {
      title: "提示词仓库",
      description: "管理和使用提示词模板",
      color: "indigo",
      link: "/prompts"
    },
    {
      title: "智能优化",
      description: "AI驱动的提示词和RAG优化",
      color: "violet",
      link: "/optimization"
    },
  ];

  if (loading) {
    return (
      <div className="max-w-[1600px] mx-auto px-4 py-3">
        <div className="flex items-center justify-center h-96">
          <div className="flex flex-col items-center gap-3">
            <svg className="animate-spin h-10 w-10 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="text-gray-600">加载中...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-[1600px] mx-auto px-4 py-3">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      </div>
    );
  }

  if (!statistics) return null;

  const stats = [
    { 
      name: "总任务数", 
      value: statistics.total_tasks?.toString() || "0", 
      color: "blue",
      icon: "tasks"
    },
    { 
      name: "已完成", 
      value: statistics.completed_tasks?.toString() || "0", 
      color: "green",
      icon: "completed"
    },
    {
      name: "失败任务",
      value: (statistics.failed_tasks || 0).toString(),
      color: "red",
      icon: "failed"
    },
    {
      name: "运行中任务",
      value: ((statistics.total_tasks || 0) - (statistics.completed_tasks || 0) - (statistics.failed_tasks || 0)).toString(),
      color: "indigo",
      icon: "running"
    },
    { 
      name: "成功率", 
      value: `${(typeof statistics.success_rate === 'number' ? statistics.success_rate * 100 : 0).toFixed(1)}%`, 
      color: "purple",
      icon: "success"
    },
    {
      name: "总 Token 消耗",
      value: (statistics.total_tokens || 0).toLocaleString(),
      color: "orange",
      icon: "tokens"
    },
  ];

  return (
    <div className="max-w-[1600px] mx-auto px-4 py-3 space-y-4">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl p-5 border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2 text-gray-900">
              欢迎回来，{localStorage.getItem("username") || "admin"}
            </h1>
            <p className="text-gray-600 text-sm">
              {new Date().toLocaleDateString("zh-CN", { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                weekday: 'long'
              })}
            </p>
          </div>
          <div className="hidden md:block">
            <svg className="w-20 h-20 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat, index) => (
          <div key={index} className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-600 mb-2">{stat.name}</div>
                <div className="text-3xl font-bold text-gray-900">{stat.value}</div>
              </div>
              <div className={`p-2.5 rounded-lg ${
                stat.color === 'blue' ? 'bg-blue-50' :
                stat.color === 'green' ? 'bg-green-50' :
                stat.color === 'purple' ? 'bg-purple-50' :
                stat.color === 'orange' ? 'bg-orange-50' :
                stat.color === 'red' ? 'bg-red-50' :
                stat.color === 'indigo' ? 'bg-indigo-50' :
                'bg-gray-50'
              }`}>
                {stat.icon === 'tasks' ? (
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                ) : stat.icon === 'completed' ? (
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ) : stat.icon === 'success' ? (
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                ) : stat.icon === 'tokens' ? (
                  <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                ) : stat.icon === 'running' ? (
                  <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                ) : stat.icon === 'failed' ? (
                  <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ) : null}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-3">快速操作</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quickActions.map((action, index) => (
            <Link
              key={index}
              to={action.link}
              className="group bg-white rounded-xl border border-gray-200 p-4 hover:border-transparent hover:shadow-lg hover:scale-[1.02] transition-all duration-200"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-start gap-4 flex-1">
                  <div className={`p-3 rounded-xl ${
                    action.color === 'blue' ? 'bg-blue-50 group-hover:bg-blue-100' :
                    action.color === 'purple' ? 'bg-purple-50 group-hover:bg-purple-100' :
                    action.color === 'indigo' ? 'bg-indigo-50 group-hover:bg-indigo-100' :
                    'bg-violet-50 group-hover:bg-violet-100'
                  } transition-colors`}>
                    {action.color === 'blue' ? (
                      <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                      </svg>
                    ) : action.color === 'purple' ? (
                      <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                      </svg>
                    ) : action.color === 'indigo' ? (
                      <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                    ) : (
                      <svg className="w-6 h-6 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-base font-semibold text-gray-900 mb-1 group-hover:text-blue-600 transition-colors">
                      {action.title}
                    </h3>
                    <p className="text-sm text-gray-600">{action.description}</p>
                  </div>
                </div>
                <svg className="w-6 h-6 text-gray-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      </div>

    </div>
  );
}

