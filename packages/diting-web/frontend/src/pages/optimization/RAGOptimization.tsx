import { useState } from "react";

export default function RAGOptimization() {
  const [_selectedStrategy, setSelectedStrategy] = useState<string>("");

  const strategies = [
    {
      id: "chunking",
      name: "分块策略优化",
      description: "优化文档分块大小和重叠策略",
      icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
      status: "planned"
    },
    {
      id: "embedding",
      name: "嵌入模型选择",
      description: "选择最适合的向量嵌入模型",
      icon: "M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01",
      status: "planned"
    },
    {
      id: "retrieval",
      name: "检索参数调优",
      description: "优化Top-K、相似度阈值等检索参数",
      icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
      status: "planned"
    },
    {
      id: "reranking",
      name: "重排序策略",
      description: "添加和优化检索结果重排序",
      icon: "M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12",
      status: "planned"
    },
    {
      id: "hybrid",
      name: "混合检索",
      description: "结合向量检索和关键词检索",
      icon: "M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z",
      status: "planned"
    },
    {
      id: "query",
      name: "查询优化",
      description: "自动改写和扩展用户查询",
      icon: "M8 16l2.879-2.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242zM21 12a9 9 0 11-18 0 9 9 0 0118 0z",
      status: "planned"
    },
  ];

  return (
    <div className="space-y-5">
      {/* Coming Soon Banner */}
      <div className="bg-gradient-to-r from-purple-100 via-pink-100 to-blue-100 rounded-lg p-8 text-center border-2 border-purple-300">
        <div className="mb-4">
          <svg className="w-20 h-20 mx-auto text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">RAG 优化功能即将推出</h2>
        <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
          我们正在开发强大的 RAG（检索增强生成）优化功能，将帮助您自动调优检索参数、优化分块策略、选择最佳嵌入模型等，敬请期待！
        </p>
        <div className="flex items-center justify-center gap-3">
          <span className="px-4 py-2 bg-purple-600 text-white rounded-lg font-medium">
            预计上线时间：2025 Q4
          </span>
          <button className="btn btn-outline">
            订阅更新通知
          </button>
        </div>
      </div>

      {/* Feature Preview */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">功能预览</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {strategies.map((strategy) => (
            <div
              key={strategy.id}
              className="bg-white rounded-lg border-2 border-gray-200 p-5 hover:border-purple-300 transition-all cursor-pointer group"
              onClick={() => setSelectedStrategy(strategy.id)}
            >
              <div className="flex items-start gap-3 mb-3">
                <div className="p-2 bg-purple-50 rounded-lg group-hover:bg-purple-100 transition-colors">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d={strategy.icon} />
                  </svg>
                </div>
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-gray-900 mb-1 group-hover:text-purple-600 transition-colors">
                    {strategy.name}
                  </h4>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200">
                    计划中
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-600">{strategy.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Roadmap */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">开发路线图</h3>
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-24 text-sm font-semibold text-gray-900">Q4 2025</div>
            <div className="flex-1">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  <span className="text-sm text-gray-700">分块策略优化</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  <span className="text-sm text-gray-700">嵌入模型评估与选择</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  <span className="text-sm text-gray-700">检索参数自动调优</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-24 text-sm font-semibold text-gray-900">Q1 2026</div>
            <div className="flex-1">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <span className="text-sm text-gray-700">重排序策略优化</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <span className="text-sm text-gray-700">混合检索优化</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-24 text-sm font-semibold text-gray-900">Q2 2026</div>
            <div className="flex-1">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500"></div>
                  <span className="text-sm text-gray-700">查询优化与改写</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500"></div>
                  <span className="text-sm text-gray-700">端到端 RAG 系统优化</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Call to Action */}
      <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200 p-6 text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">想要提前体验？</h3>
        <p className="text-sm text-gray-600 mb-4">
          加入我们的 Beta 测试计划，第一时间体验 RAG 优化功能
        </p>
        <button className="btn btn-primary gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          申请 Beta 测试资格
        </button>
      </div>
    </div>
  );
}

