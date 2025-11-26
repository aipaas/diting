import { useState, useEffect } from "react";
import { getMetrics, createMetric, updateMetric, deleteMetric, getPrompts } from "@/api/client";
import { MetricResponse, MetricCreate, MetricUpdate, EvalMetricTypeEnum, PromptResponse, PromptCategoryEnum } from "@/types/api";
import Pagination from "@/components/Pagination";

export default function MetricManagement() {
  const [metrics, setMetrics] = useState<MetricResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"all" | "builtin" | "custom">("all");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [editingMetric, setEditingMetric] = useState<MetricResponse | null>(null);
  const [detailMetric, setDetailMetric] = useState<MetricResponse | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [formData, setFormData] = useState<MetricCreate>({
    name: "",
    description: "",
    prompt: "",
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(6);
  const [total, setTotal] = useState(0);

  // Prompt templates for quick insertion
  const [promptTemplates, setPromptTemplates] = useState<PromptResponse[]>([]);
  const [promptTemplatesLoading, setPromptTemplatesLoading] = useState(false);
  const [promptTemplatesError, setPromptTemplatesError] = useState("");

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };

  useEffect(() => {
    fetchMetrics();
  }, [page, pageSize, filterType]);

  // Load prompt templates when create modal opens
  useEffect(() => {
    if (!showCreateModal) return;
    (async () => {
      try {
        setPromptTemplatesLoading(true);
        setPromptTemplatesError("");
        const data = await getPrompts(1, 100, PromptCategoryEnum.EVALUATION);
        setPromptTemplates(data.items);
      } catch (err: any) {
        console.error("Failed to fetch prompt templates:", err);
        setPromptTemplatesError("提示词模板加载失败");
      } finally {
        setPromptTemplatesLoading(false);
      }
    })();
  }, [showCreateModal]);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError("");
      const typeParam = filterType === "all" ? undefined : (filterType === "builtin" ? EvalMetricTypeEnum.BUILTIN : EvalMetricTypeEnum.CUSTOM);
      const data = await getMetrics(page, pageSize, typeParam);
      setMetrics(data.items);
      setTotal(data.total);
    } catch (err: any) {
      console.error("Failed to fetch metrics:", err);
      setError("获取评估维度失败");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateMetric = async () => {
    try {
      await createMetric(formData);
      setShowCreateModal(false);
      setFormData({ name: "", description: "", prompt: "" });
      await fetchMetrics();
    } catch (err: any) {
      console.error("Failed to create metric:", err);
      alert("创建维度失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleEditMetric = async () => {
    if (!editingMetric) return;
    try {
      const updateData: MetricUpdate = {
        name: formData.name,
        description: formData.description,
        prompt: formData.prompt,
      };
      await updateMetric(editingMetric.id, updateData);
      setShowEditModal(false);
      setEditingMetric(null);
      setFormData({ name: "", description: "", prompt: "" });
      await fetchMetrics();
    } catch (err: any) {
      console.error("Failed to update metric:", err);
      alert("更新维度失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleDeleteMetric = async (metricId: string) => {
    if (!confirm("确定要删除这个维度吗？")) return;
    try {
      await deleteMetric(metricId);
      await fetchMetrics();
    } catch (err: any) {
      console.error("Failed to delete metric:", err);
      alert("删除维度失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const openEditModal = (metric: MetricResponse) => {
    setEditingMetric(metric);
    setFormData({
      name: metric.name,
      description: metric.description || "",
      prompt: metric.prompt || "",
    });
    setShowEditModal(true);
  };

  // Filter metrics by search query (client-side filtering for current page only)
  // Note: For full-text search across all pages, this should be moved to backend
  const filteredMetrics = metrics.filter(metric => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return metric.name.toLowerCase().includes(query) ||
      (metric.description?.toLowerCase() || "").includes(query);
  });
  
  // Use filtered metrics directly - backend already sorts by is_global.desc(), created_at.desc()
  // No need to sort again on frontend as it would only sort current page data
  const sortedMetrics = filteredMetrics;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-gray-600">加载中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header Actions */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center justify-between gap-4">
            {/* Left: Title and Search */}
            <div className="flex items-center gap-6">
              <h2 className="text-lg font-bold text-gray-900">
                评估维度
              </h2>

              {/* Search Box */}
              <div className="relative w-80">
                <input
                  type="text"
                  placeholder="搜索评估维度..."
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

            {/* Right: Filters and Actions */}
            <div className="flex items-center gap-3">
              {/* Type Filter */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-600 whitespace-nowrap">类型筛选</label>
                <select
                  value={filterType}
                  onChange={(e) => {
                    setFilterType(e.target.value as "all" | "builtin" | "custom");
                    setPage(1);
                  }}
                  className="pl-3 pr-8 py-2 text-sm border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 cursor-pointer transition-all"
                >
                  <option value="all">全部</option>
                  <option value="builtin">内置</option>
                  <option value="custom">自定义</option>
                </select>
              </div>

              {/* Create Dimension Button */}
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-gradient-to-r from-brand-500 to-violet-500 text-white text-sm font-medium rounded-lg hover:from-brand-600 hover:to-violet-600 transition-all flex items-center gap-2 shadow-sm hover:shadow whitespace-nowrap"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                创建维度
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Grid - 2 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sortedMetrics.map((metric) => (
          <div
            key={metric.id}
            className="group relative bg-white rounded-lg border border-gray-200 p-4 hover:border-green-400 hover:shadow-lg hover:shadow-green-50 transition-all duration-200 cursor-pointer h-full flex flex-col"
            onClick={() => {
              setDetailMetric(metric);
              setShowDetailModal(true);
              setOpenMenuId(null);
            }}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <h3 className="text-base font-semibold text-gray-900 truncate group-hover:text-green-600 transition-colors">
                  {metric.name}
                </h3>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    metric.type === EvalMetricTypeEnum.BUILTIN
                      ? "bg-blue-50 text-blue-700"
                      : "bg-orange-50 text-orange-700"
                  }`}
                >
                  {metric.type === EvalMetricTypeEnum.BUILTIN ? "内置" : "自定义"}
                </span>
              </div>
              {metric.type === EvalMetricTypeEnum.CUSTOM && (
                <div className="relative" onClick={(e) => e.stopPropagation()}>
                  <button
                    className="btn btn-ghost btn-sm btn-circle text-gray-500 hover:text-gray-700"
                    onClick={() => setOpenMenuId(openMenuId === metric.id ? null : metric.id)}
                    aria-label="更多操作"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.75a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 6a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 6a1.5 1.5 0 110-3 1.5 1.5 0 010 3z" />
                    </svg>
                  </button>
                  {openMenuId === metric.id && (
                    <div className="absolute right-0 mt-2 w-28 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
                      <button
                        className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                        onClick={() => { setOpenMenuId(null); openEditModal(metric); }}
                      >编辑</button>
                      <button
                        className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                        onClick={() => { setOpenMenuId(null); handleDeleteMetric(metric.id); }}
                      >删除</button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Description */}
            <p className="text-sm text-gray-600 leading-relaxed mb-3 min-h-[1.5rem]">
              {metric.description || "暂无描述"}
            </p>

            {/* Footer */}
            <div className="mt-auto flex items-center justify-between pt-2 border-top border-gray-100">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <div>{formatDate(metric.created_at)}</div>
                {metric.creator && (
                  <>
                    <span>•</span>
                    <div className="flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                      <span>{metric.creator.username}</span>
                    </div>
                  </>
                )}
              </div>
              
              {/* actions moved to overflow menu */}
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="bg-white rounded-lg border border-gray-200">
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={(p) => setPage(p)}
            onPageSizeChange={(ps) => {
              setPageSize(ps);
              setPage(1);
            }}
            pageSizeOptions={[6, 12, 24, 48]}
          />
        </div>
      )}

      {filteredMetrics.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">没有找到评估维度</h3>
          <p className="text-gray-500 text-sm mb-6">尝试调整搜索条件或分类筛选，或新建一个维度</p>
          <button 
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary"
          >
            创建维度
          </button>
        </div>
      )}

      {/* Details Modal */}
      {showDetailModal && detailMetric && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setShowDetailModal(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="text-lg font-semibold text-gray-900">{detailMetric.name}</h2>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                    detailMetric.type === EvalMetricTypeEnum.BUILTIN
                      ? "bg-blue-50 text-blue-700 border-blue-200"
                      : "bg-orange-50 text-orange-700 border-orange-200"
                  }`}>
                    {detailMetric.type === EvalMetricTypeEnum.BUILTIN ? "内置" : "自定义"}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{detailMetric.description || "无描述"}</p>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowDetailModal(false)}>关闭</button>
            </div>

            {detailMetric.prompt ? (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="text-xs font-medium text-gray-500 mb-1">提示词</div>
                <pre className="text-sm text-gray-800 whitespace-pre-wrap leading-6">{detailMetric.prompt}</pre>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-gray-200 p-6 text-center text-gray-500 text-sm">
                暂无提示词
              </div>
            )}

            <div className="flex justify-end gap-2 mt-6">
              {detailMetric.type === EvalMetricTypeEnum.CUSTOM && (
                <>
                  <button
                    className="btn btn-ghost"
                    onClick={() => { setShowDetailModal(false); openEditModal(detailMetric); }}
                  >编辑</button>
                  <button
                    className="btn btn-error text-white"
                    onClick={() => { setShowDetailModal(false); handleDeleteMetric(detailMetric.id); }}
                  >删除</button>
                </>
              )}
              <button className="btn" onClick={() => setShowDetailModal(false)}>好的</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Metric Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => { setShowCreateModal(false); }}>
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="relative px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">创建自定义维度</h3>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="w-8 h-8 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 flex items-center justify-center transition-colors"
                  aria-label="关闭"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="space-y-5">
                {/* Name */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700">
                      名称 <span className="text-red-500">*</span>
                    </label>
                    <span className="text-xs text-gray-400">{formData.name.length}/100</span>
                  </div>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="例如：custom_accuracy"
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100 transition-all"
                    maxLength={100}
                    required
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    描述 <span className="text-xs text-gray-400 font-normal">(可选)</span>
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="描述这个维度的用途，帮助团队成员理解其评估目标..."
                    rows={3}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100 transition-all resize-none"
                  />
                </div>

                {/* Prompt */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-gray-700">
                      提示词 <span className="text-xs text-gray-400 font-normal">(可选)</span>
                    </label>
                    <select
                      defaultValue=""
                      onChange={(e) => {
                        const id = e.target.value;
                        const tpl = promptTemplates.find((p) => p.id === id);
                        if (tpl) {
                          setFormData({ ...formData, prompt: tpl.content });
                        }
                      }}
                      className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-green-100"
                    >
                      <option value="">{promptTemplatesLoading ? "加载中..." : "从模板插入"}</option>
                      {promptTemplates.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                  {promptTemplatesError && (
                    <p className="mb-2 text-xs text-red-600">{promptTemplatesError}</p>
                  )}
                  <textarea
                    value={formData.prompt}
                    onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                    placeholder="用于评估的提示词，支持从模板快速插入..."
                    rows={8}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100 transition-all font-mono text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-100 px-6 py-4 bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => { setShowCreateModal(false); setFormData({ name: "", description: "", prompt: "" }); }}
                className="px-5 py-2 text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg font-medium transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleCreateMetric}
                disabled={!formData.name.trim()}
                className="px-5 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Metric Modal */}
      {showEditModal && editingMetric && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">编辑自定义维度</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input input-bordered w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="textarea textarea-bordered w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">提示词</label>
                <textarea
                  value={formData.prompt}
                  onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                  rows={4}
                  className="textarea textarea-bordered w-full"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setEditingMetric(null);
                  setFormData({ name: "", description: "", prompt: "" });
                }}
                className="btn btn-ghost flex-1"
              >
                取消
              </button>
              <button
                onClick={handleEditMetric}
                disabled={!formData.name.trim()}
                className="btn btn-primary flex-1"
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

