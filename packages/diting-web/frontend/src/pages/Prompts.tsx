import { useEffect, useMemo, useState } from "react";
import {
  getPrompts,
  getPromptStatistics,
  togglePromptFavorite,
  incrementPromptUsage,
  createPrompt,
  deletePrompt,
} from "@/api/client";
import { PromptCategoryEnum, type PromptResponse, type PromptStatisticsResponse } from "@/types/api";

interface Prompt {
  id: string;
  name: string;
  description: string;
  category: PromptCategoryEnum;
  content: string;
  variables: string[];
  version: string;
  isFavorite: boolean;
  usageCount: number;
  createdAt: string;
  updatedAt: string;
}

export default function Prompts() {
  const [activeCategory, setActiveCategory] = useState<"all" | PromptCategoryEnum>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [stats, setStats] = useState<PromptStatisticsResponse | null>(null);
  const [_loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    category: PromptCategoryEnum.EVALUATION as PromptCategoryEnum,
    content: "",
    variables: "",
    version: "v1.0",
    is_favorite: false,
  });

  const mapPrompt = (p: PromptResponse): Prompt => ({
    id: p.id,
    name: p.name,
    description: p.description ?? "",
    category: p.category,
    content: p.content,
    variables: p.variables ?? [],
    version: p.version,
    isFavorite: p.is_favorite,
    usageCount: p.usage_count,
    createdAt: p.created_at,
    updatedAt: p.updated_at,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [listRes, statsRes] = await Promise.all([
          getPrompts(
            1,
            100,
            activeCategory === "all" ? undefined : activeCategory,
            searchQuery || undefined,
            showFavoritesOnly
          ),
          getPromptStatistics(),
        ]);
        setPrompts(listRes.items.map(mapPrompt));
        setStats(statsRes);
        // 保持当前选中项同步
        if (selectedPrompt) {
          const refreshed = listRes.items.find((p) => p.id === selectedPrompt.id);
          if (refreshed) setSelectedPrompt(mapPrompt(refreshed));
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCategory, searchQuery, showFavoritesOnly]);

  const categories: Array<"all" | PromptCategoryEnum> = [
    "all",
    PromptCategoryEnum.SYSTEM,
    PromptCategoryEnum.EVALUATION,
    PromptCategoryEnum.SYNTHESIS,
    PromptCategoryEnum.CUSTOM,
  ];

  const filteredPrompts = useMemo(() => prompts, [prompts]);

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "系统": return "bg-blue-50 text-blue-700 border-blue-200";
      case "评估": return "bg-green-50 text-green-700 border-green-200";
      case "合成": return "bg-purple-50 text-purple-700 border-purple-200";
      case "优化": return "bg-pink-50 text-pink-700 border-pink-200";
      default: return "bg-gray-50 text-gray-700 border-gray-200";
    }
  };

  const toggleFavorite = async (promptId: string) => {
    const updated = await togglePromptFavorite(promptId);
    setPrompts((prev) =>
      prev.map((p) =>
        p.id === promptId ? { ...p, isFavorite: updated.is_favorite } : p
      )
    );
    if (selectedPrompt?.id === promptId) {
      setSelectedPrompt((prev) =>
        prev ? { ...prev, isFavorite: updated.is_favorite } : prev
      );
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="max-w-[1600px] mx-auto px-4 py-3 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">提示词仓库</h1>
          <p className="text-sm text-gray-500 mt-1">管理和使用提示词模板</p>
        </div>
        <button className="btn btn-primary btn-sm gap-2" onClick={() => setShowCreate(true)}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          创建提示词
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-xs font-medium text-gray-600 mb-2">总提示词</div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-semibold text-gray-900">{stats?.total_prompts ?? prompts.length}</div>
            <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-xs font-medium text-gray-600 mb-2">收藏</div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-semibold text-gray-900">{stats?.favorite_count ?? prompts.filter(p => p.isFavorite).length}</div>
            <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-xs font-medium text-gray-600 mb-2">总使用次数</div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-semibold text-gray-900">{stats?.total_usage_count ?? prompts.reduce((sum, p) => sum + p.usageCount, 0)}</div>
            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-xs font-medium text-gray-600 mb-2">分类</div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-semibold text-gray-900">{stats?.category_count ?? (categories.length - 1)}</div>
            <div className="w-2 h-2 rounded-full bg-green-500"></div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Categories */}
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setActiveCategory(category)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeCategory === category
                    ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                    : "text-gray-600 hover:bg-gray-50 border border-transparent"
                }`}
              >
                {category === "all" ? "全部" : category}
              </button>
            ))}
          </div>

          {/* Search & Favorite Filter */}
          <div className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="搜索提示词..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input input-sm input-bordered w-full pl-9"
              />
              <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <button
              onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
              className={`btn btn-sm gap-2 ${showFavoritesOnly ? 'btn-warning' : 'btn-ghost'}`}
            >
              <svg className="w-4 h-4" fill={showFavoritesOnly ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
              {showFavoritesOnly ? '仅收藏' : '收藏'}
            </button>
          </div>
        </div>
      </div>

      {/* Prompts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Prompt List */}
        <div className="lg:col-span-1 space-y-3">
          {filteredPrompts.map((prompt) => (
            <div
              key={prompt.id}
              onClick={() => setSelectedPrompt(prompt)}
              className={`bg-white rounded-lg border-2 p-4 cursor-pointer transition-all ${
                selectedPrompt?.id === prompt.id
                  ? "border-indigo-500 shadow-md"
                  : "border-gray-200 hover:border-indigo-300"
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-gray-900 mb-1 truncate">
                    {prompt.name}
                  </h3>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getCategoryColor(prompt.category)}`}>
                    {prompt.category}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFavorite(prompt.id);
                  }}
                  className="flex-shrink-0 ml-2"
                >
                  <svg
                    className={`w-5 h-5 ${prompt.isFavorite ? 'text-yellow-500 fill-current' : 'text-gray-300'}`}
                    fill={prompt.isFavorite ? "currentColor" : "none"}
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                  </svg>
                </button>
              </div>
              <p className="text-xs text-gray-500 mb-3 line-clamp-2">{prompt.description}</p>
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>v{prompt.version}</span>
                <span>{prompt.usageCount} 次使用</span>
              </div>
            </div>
          ))}

          {filteredPrompts.length === 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-sm text-gray-500">没有找到提示词</p>
            </div>
          )}
        </div>

        {/* Right: Prompt Detail */}
        <div className="lg:col-span-2">
          {selectedPrompt ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-5">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h2 className="text-lg font-bold text-gray-900">{selectedPrompt.name}</h2>
                    <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium border ${getCategoryColor(selectedPrompt.category)}`}>
                      {selectedPrompt.category}
                    </span>
                    <span className="text-xs text-gray-500">v{selectedPrompt.version}</span>
                  </div>
                  <p className="text-sm text-gray-600">{selectedPrompt.description}</p>
                </div>
                <div className="dropdown dropdown-end">
                  <label tabIndex={0} className="btn btn-ghost btn-sm btn-circle">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                    </svg>
                  </label>
                  <ul tabIndex={0} className="dropdown-content menu p-2 shadow-xl bg-white rounded-lg border border-gray-200 w-40">
                    <li><button className="text-left text-sm">编辑</button></li>
                    <li><button className="text-left text-sm" onClick={() => copyToClipboard(selectedPrompt.content)}>复制</button></li>
                    <li><button className="text-left text-sm" disabled>导出</button></li>
                    <li><button className="text-left text-sm" disabled>版本历史</button></li>
                    <div className="divider my-1"></div>
                    <li>
                      <button
                        className="text-left text-sm text-red-600"
                        onClick={async () => {
                          if (!selectedPrompt) return;
                          const confirmed = window.confirm(`确认删除“${selectedPrompt.name}”？此操作不可撤销。`);
                          if (!confirmed) return;
                          await deletePrompt(selectedPrompt.id);
                          setPrompts((prev) => prev.filter((p) => p.id !== selectedPrompt.id));
                          setSelectedPrompt(null);
                          const refreshedStats = await getPromptStatistics();
                          setStats(refreshedStats);
                        }}
                      >
                        删除
                      </button>
                    </li>
                  </ul>
                </div>
              </div>

              {/* Variables */}
              {selectedPrompt.variables.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">变量</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedPrompt.variables.map((variable, idx) => (
                      <code key={idx} className="px-2.5 py-1 bg-gray-100 text-gray-800 text-xs rounded font-mono">
                        {`{${variable}}`}
                      </code>
                    ))}
                  </div>
                </div>
              )}

              {/* Content */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-gray-900">提示词内容</h3>
                  <button className="btn btn-ghost btn-xs gap-1" onClick={() => copyToClipboard(selectedPrompt.content)}>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    复制
                  </button>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
                    {selectedPrompt.content}
                  </pre>
                </div>
              </div>

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                <div>
                  <div className="text-xs text-gray-500 mb-1">创建时间</div>
                  <div className="text-sm font-medium text-gray-900">
                    {new Date(selectedPrompt.createdAt).toLocaleDateString("zh-CN")}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">最后更新</div>
                  <div className="text-sm font-medium text-gray-900">
                    {new Date(selectedPrompt.updatedAt).toLocaleDateString("zh-CN")}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">使用次数</div>
                  <div className="text-sm font-medium text-gray-900">
                    {selectedPrompt.usageCount} 次
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">收藏状态</div>
                  <div className="text-sm font-medium text-gray-900">
                    {selectedPrompt.isFavorite ? '已收藏 ⭐' : '未收藏'}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-4 border-t border-gray-200">
                <button
                  className="btn btn-primary flex-1"
                  onClick={async () => {
                    const updated = await incrementPromptUsage(selectedPrompt.id);
                    setSelectedPrompt({ ...selectedPrompt, usageCount: updated.usage_count });
                    setPrompts((prev) =>
                      prev.map((p) => (p.id === selectedPrompt.id ? { ...p, usageCount: updated.usage_count } : p))
                    );
                  }}
                >
                  使用此提示词
                </button>
                <button className="btn btn-outline">
                  优化提示词
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
              <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">选择一个提示词</h3>
              <p className="text-gray-500 text-sm">点击左侧列表中的提示词查看详情</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Prompt Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-lg border border-gray-200 w-full max-w-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">创建提示词</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowCreate(false)}>关闭</button>
            </div>
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-sm mb-1">名称<span className="text-red-500">*</span></label>
                <input
                  className="input input-bordered w-full"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="请输入提示词名称"
                />
              </div>
              <div>
                <label className="block text-sm mb-1">描述</label>
                <input
                  className="input input-bordered w-full"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="简要描述"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm mb-1">分类<span className="text-red-500">*</span></label>
                  <select
                    className="select select-bordered w-full"
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value as PromptCategoryEnum })}
                  >
                    <option value={PromptCategoryEnum.SYSTEM}>系统</option>
                    <option value={PromptCategoryEnum.EVALUATION}>评估</option>
                    <option value={PromptCategoryEnum.SYNTHESIS}>合成</option>
                    <option value={PromptCategoryEnum.CUSTOM}>自定义</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm mb-1">版本</label>
                  <input
                    className="input input-bordered w-full"
                    value={form.version}
                    onChange={(e) => setForm({ ...form, version: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm mb-1">变量（逗号分隔）</label>
                <input
                  className="input input-bordered w-full"
                  value={form.variables}
                  onChange={(e) => setForm({ ...form, variables: e.target.value })}
                  placeholder="如：question,answer,context"
                />
              </div>
              <div>
                <label className="block text-sm mb-1">内容<span className="text-red-500">*</span></label>
                <textarea
                  className="textarea textarea-bordered w-full h-40 font-mono"
                  value={form.content}
                  onChange={(e) => setForm({ ...form, content: e.target.value })}
                  placeholder="请输入提示词内容"
                />
              </div>
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" className="checkbox checkbox-sm" checked={form.is_favorite} onChange={(e) => setForm({ ...form, is_favorite: e.target.checked })} />
                <span className="text-sm text-gray-700">设为收藏</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button className="btn" onClick={() => setShowCreate(false)}>取消</button>
              <button
                className="btn btn-primary"
                onClick={async () => {
                  if (!form.name.trim() || !form.content.trim()) return;
                  const variables = form.variables
                    .split(",")
                    .map((v) => v.trim())
                    .filter((v) => v.length > 0);
                  const created = await createPrompt({
                    name: form.name.trim(),
                    description: form.description.trim() || undefined,
                    category: form.category,
                    content: form.content,
                    variables,
                    version: form.version || undefined,
                    is_favorite: form.is_favorite,
                  });
                  const mapped = mapPrompt(created as unknown as PromptResponse);
                  setPrompts((prev) => [mapped, ...prev]);
                  setSelectedPrompt(mapped);
                  setShowCreate(false);
                  const refreshedStats = await getPromptStatistics();
                  setStats(refreshedStats);
                }}
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

