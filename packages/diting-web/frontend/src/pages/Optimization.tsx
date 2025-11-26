import { useState } from "react";
import PromptOptimization from "./optimization/PromptOptimization";
import RAGOptimization from "./optimization/RAGOptimization";

type TabType = "prompt" | "rag";

export default function Optimization() {
  const [activeTab, setActiveTab] = useState<TabType>("prompt");

  const tabs = [
    { 
      key: "prompt" as TabType, 
      label: "提示词优化", 
      icon: "M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z",
      description: "使用AI智能优化提示词"
    },
    { 
      key: "rag" as TabType, 
      label: "RAG优化", 
      icon: "M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z",
      description: "优化检索增强生成配置",
      comingSoon: true
    },
  ];

  return (
    <div className="max-w-[1600px] mx-auto px-4 py-3 space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">智能优化</h1>
        <p className="text-sm text-gray-500 mt-1">使用AI技术自动优化系统配置</p>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="border-b border-gray-200">
          <nav className="flex gap-2 px-4 pt-3">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => !tab.comingSoon && setActiveTab(tab.key)}
                disabled={tab.comingSoon}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg font-medium text-sm transition-all relative ${
                  activeTab === tab.key
                    ? "bg-pink-50 text-pink-700 border-b-2 border-pink-600"
                    : tab.comingSoon
                    ? "text-gray-400 cursor-not-allowed"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d={tab.icon} />
                </svg>
                {tab.label}
                {tab.comingSoon && (
                  <span className="ml-1 px-1.5 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">
                    即将推出
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-4">
          {/* Tab Description */}
          <div className="bg-gradient-to-r from-pink-50 to-purple-50 border border-pink-200 rounded-lg p-4 mb-4">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-pink-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
              </svg>
              <div>
                <h3 className="text-sm font-semibold text-pink-900 mb-1">
                  {tabs.find(t => t.key === activeTab)?.label}
                </h3>
                <p className="text-sm text-pink-700">
                  {tabs.find(t => t.key === activeTab)?.description}
                </p>
              </div>
            </div>
          </div>

          {/* Tab Content */}
          {activeTab === "prompt" && <PromptOptimization />}
          {activeTab === "rag" && <RAGOptimization />}
        </div>
      </div>
    </div>
  );
}

