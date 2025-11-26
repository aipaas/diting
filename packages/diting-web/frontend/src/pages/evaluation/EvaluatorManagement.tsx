import { useState, useEffect } from "react";
import { getEvaluators, deleteEvaluator, createEvaluator, updateEvaluator, getEvaluator, getMetrics, getModels } from "@/api/client";
import type { EvaluatorResponse, MetricResponse, ModelConfigForMetric, MetricModelConfig, ModelResponse } from "@/types/api";
import Pagination from "@/components/Pagination";

export default function EvaluatorManagement() {
  const [evaluators, setEvaluators] = useState<EvaluatorResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingEvaluatorId, setEditingEvaluatorId] = useState<string | null>(null);
  
  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const [total, setTotal] = useState(0);
  
  // Create/Edit form state
  const [metrics, setMetrics] = useState<MetricResponse[]>([]);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    metric_ids: [] as string[],
  });
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);
  
  // Model configuration state
  const [advancedMode, setAdvancedMode] = useState(false);
  const [llmModels, setLlmModels] = useState<ModelResponse[]>([]);
  const [embeddingModels, setEmbeddingModels] = useState<ModelResponse[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [defaultLlmConfig, setDefaultLlmConfig] = useState<ModelConfigForMetric>({ name: "" });
  const [defaultEmbeddingConfig, setDefaultEmbeddingConfig] = useState<ModelConfigForMetric>({ name: "" });
  const [metricModelConfigs, setMetricModelConfigs] = useState<Record<string, MetricModelConfig>>({});

  useEffect(() => {
    fetchEvaluators();
    fetchMetrics();
    fetchModels();
  }, [page, pageSize]);

  const fetchEvaluators = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getEvaluators(page, pageSize);
      setEvaluators(data.items);
      setTotal(data.total);
    } catch (err: any) {
      console.error("Failed to fetch evaluators:", err);
      setError("获取评估器失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      const data = await getMetrics(1, 100);
      setMetrics(data.items);
    } catch (err: any) {
      console.error("Failed to fetch metrics:", err);
    }
  };

  const fetchModels = async () => {
    try {
      setModelsLoading(true);
      const data = await getModels(1, 100);
      const llms = data.items.filter((m) => m.model_type === "llm");
      const embeddings = data.items.filter((m) => m.model_type === "embedding");
      
      setLlmModels(llms);
      setEmbeddingModels(embeddings);
      
      // Set default to the first default model or first model
      const defaultLlm = llms.find((m) => m.is_default) || llms[0];
      const defaultEmbedding = embeddings.find((m) => m.is_default) || embeddings[0];
      
      if (defaultLlm) {
        setDefaultLlmConfig({ name: defaultLlm.name });
      }
      if (defaultEmbedding) {
        setDefaultEmbeddingConfig({ name: defaultEmbedding.name });
      }
    } catch (err: any) {
      console.error("Failed to fetch models:", err);
    } finally {
      setModelsLoading(false);
    }
  };

  const handleDelete = async (evaluatorId: string) => {
    if (!confirm("确定要删除这个评估器吗？")) return;
    
    try {
      await deleteEvaluator(evaluatorId);
      fetchEvaluators();
    } catch (err: any) {
      console.error("Failed to delete evaluator:", err);
      alert("删除失败：" + (err.response?.data?.detail || err.message));
    }
  };

  const handleEdit = async (evaluatorId: string) => {
    try {
      const evaluator = await getEvaluator(evaluatorId);
      
      // Fill form with evaluator data
      setFormData({
        name: evaluator.name,
        description: evaluator.description || "",
        metric_ids: evaluator.metric_ids,
      });
      
      // Set model configs
      if (evaluator.config) {
        // Set default configs
        if (evaluator.config.default_llm_config) {
          setDefaultLlmConfig(evaluator.config.default_llm_config);
        }
        if (evaluator.config.default_embedding_config) {
          setDefaultEmbeddingConfig(evaluator.config.default_embedding_config);
        }
        
        // Set advanced mode if metric_model_configs exist
        if (evaluator.config.metric_model_configs && evaluator.config.metric_model_configs.length > 0) {
          setAdvancedMode(true);
          const configs: Record<string, MetricModelConfig> = {};
          evaluator.config.metric_model_configs.forEach((cfg) => {
            configs[cfg.metric_id] = cfg;
          });
          setMetricModelConfigs(configs);
        } else {
          setAdvancedMode(false);
          setMetricModelConfigs({});
        }
      }
      
      setEditingEvaluatorId(evaluatorId);
      setShowCreateModal(true);
    } catch (err: any) {
      console.error("Failed to fetch evaluator:", err);
      alert("加载评估器失败：" + (err.response?.data?.detail || err.message));
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      metric_ids: [],
    });
    setAdvancedMode(false);
    setMetricModelConfigs({});
    
    // Reset to default models
    const defaultLlm = llmModels.find((m) => m.is_default) || llmModels[0];
    const defaultEmbedding = embeddingModels.find((m) => m.is_default) || embeddingModels[0];
    setDefaultLlmConfig({ name: defaultLlm?.name || "" });
    setDefaultEmbeddingConfig({ name: defaultEmbedding?.name || "" });
    
    setEditingEvaluatorId(null);
  };

  const handleCreate = async () => {
    if (!formData.name.trim()) {
      alert("请输入评估器名称");
      return;
    }
    if (formData.metric_ids.length === 0) {
      alert("请至少选择一个评估维度");
      return;
    }

    try {
      setCreating(true);
      
      // Build config based on mode
      const metric_model_configs_array = Object.values(metricModelConfigs);
      
      await createEvaluator({
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        metric_ids: formData.metric_ids,
        config: {
          metric_model_configs: advancedMode && metric_model_configs_array.length > 0 ? metric_model_configs_array : undefined,
          default_llm_config: defaultLlmConfig.name ? defaultLlmConfig : undefined,
          default_embedding_config: defaultEmbeddingConfig.name ? defaultEmbeddingConfig : undefined,
        },
      });
      
      resetForm();
      setShowCreateModal(false);
      fetchEvaluators();
    } catch (err: any) {
      console.error("Failed to create evaluator:", err);
      alert("创建失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setCreating(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingEvaluatorId) return;
    if (!formData.name.trim()) {
      alert("请输入评估器名称");
      return;
    }
    if (formData.metric_ids.length === 0) {
      alert("请至少选择一个评估维度");
      return;
    }

    try {
      setUpdating(true);
      
      // Build config based on mode
      const metric_model_configs_array = Object.values(metricModelConfigs);
      
      await updateEvaluator(editingEvaluatorId, {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        metric_ids: formData.metric_ids,
        config: {
          metric_model_configs: advancedMode && metric_model_configs_array.length > 0 ? metric_model_configs_array : undefined,
          default_llm_config: defaultLlmConfig.name ? defaultLlmConfig : undefined,
          default_embedding_config: defaultEmbeddingConfig.name ? defaultEmbeddingConfig : undefined,
        },
      });
      
      resetForm();
      setShowCreateModal(false);
      fetchEvaluators();
    } catch (err: any) {
      console.error("Failed to update evaluator:", err);
      alert("更新失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setUpdating(false);
    }
  };

  const toggleMetricSelection = (metricId: string) => {
    setFormData(prev => ({
      ...prev,
      metric_ids: prev.metric_ids.includes(metricId)
        ? prev.metric_ids.filter(id => id !== metricId)
        : [...prev.metric_ids, metricId],
    }));
    
    // Initialize model config for this metric in advanced mode
    if (advancedMode && !formData.metric_ids.includes(metricId)) {
      const metric = metrics.find(m => m.id === metricId);
      if (metric) {
        setMetricModelConfigs(prev => ({
          ...prev,
          [metricId]: {
            metric_id: metricId,
            llm_config: metric.llm_required ? { name: "gpt-3.5-turbo" } : undefined,
            embedding_config: metric.embedding_required ? { name: "text-embedding-ada-002" } : undefined,
          }
        }));
      }
    } else if (formData.metric_ids.includes(metricId)) {
      // Remove config when unchecking
      setMetricModelConfigs(prev => {
        const newConfigs = { ...prev };
        delete newConfigs[metricId];
        return newConfigs;
      });
    }
  };

  const updateMetricModelConfig = (metricId: string, type: 'llm' | 'embedding', field: string, value: any) => {
    setMetricModelConfigs(prev => {
      const config = prev[metricId] || { metric_id: metricId };
      const modelConfigKey = type === 'llm' ? 'llm_config' : 'embedding_config';
      const currentConfig = config[modelConfigKey] || { name: '' };
      
      return {
        ...prev,
        [metricId]: {
          ...config,
          [modelConfigKey]: {
            ...currentConfig,
            [field]: value,
          }
        }
      };
    });
  };

  // Filter evaluators by search query (client-side filtering for current page)
  const filteredEvaluators = evaluators.filter(evaluator =>
    evaluator.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (evaluator.description?.toLowerCase() || "").includes(searchQuery.toLowerCase())
  );

  // Handle search - reset to page 1 when search query changes
  useEffect(() => {
    if (searchQuery) {
      setPage(1);
    }
  }, [searchQuery]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-green-100 border-t-green-600 rounded-full animate-spin"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-8 h-8 bg-green-50 rounded-full"></div>
            </div>
          </div>
          <div className="text-center">
            <p className="text-slate-700 font-medium">加载中...</p>
            <p className="text-slate-500 text-sm mt-1">正在获取评估器列表</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gradient-to-r from-red-50 to-rose-50 border border-red-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center">
            <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-red-800 font-semibold mb-1">加载失败</h3>
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header Section */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center justify-between gap-4">
            {/* Left: Title and Search */}
            <div className="flex items-center gap-6">
              <h2 className="text-lg font-bold text-gray-900">
                评估器
              </h2>

              {/* Search Box */}
              <div className="relative w-80">
                <input
                  type="text"
                  placeholder="搜索评估器..."
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

            {/* Right: Actions */}
            <div className="flex items-center gap-3">
              {/* Create Evaluator Button */}
              <button
                onClick={() => {
                  resetForm();
                  setShowCreateModal(true);
                }}
                className="px-4 py-2 bg-gradient-to-r from-brand-500 to-violet-500 text-white text-sm font-medium rounded-lg hover:from-brand-600 hover:to-violet-600 transition-all flex items-center gap-2 shadow-sm hover:shadow whitespace-nowrap"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                创建评估器
              </button>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="p-4">
          {/* Evaluators List */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filteredEvaluators.map((evaluator) => (
              <div 
                key={evaluator.id} 
                className="bg-white rounded-lg border border-slate-200/60 p-4 shadow-sm hover:shadow-md hover:border-green-300/50 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-semibold text-slate-900 group-hover:text-green-600 transition-colors truncate">
                      {evaluator.name}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1.5 ml-2 flex-shrink-0">
                    <button 
                      onClick={() => handleEdit(evaluator.id)}
                      className="w-8 h-8 rounded-lg text-blue-600 hover:bg-blue-50 hover:text-blue-700 transition-all duration-200 flex items-center justify-center"
                      title="编辑"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button 
                      onClick={() => handleDelete(evaluator.id)}
                      className="w-8 h-8 rounded-lg text-red-600 hover:bg-red-50 hover:text-red-700 transition-all duration-200 flex items-center justify-center"
                      title="删除"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Metrics and Stats in one line */}
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-1.5 flex-wrap flex-1 min-w-0">
                    {evaluator.metric_ids.slice(0, 2).map((metricId, idx) => {
                      const metricName = metrics.find(m => m.id === metricId)?.name;
                      return (
                        <span 
                          key={idx} 
                          className="px-2 py-1 bg-gradient-to-r from-green-50 to-emerald-50 text-green-700 text-xs font-medium rounded border border-green-200/60 whitespace-nowrap"
                        >
                          {metricName || `${metricId.substring(0, 8)}...`}
                        </span>
                      );
                    })}
                    {evaluator.metric_ids.length > 2 && (
                      <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded">
                        +{evaluator.metric_ids.length - 2}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="px-2 py-1 bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 text-xs font-semibold rounded border border-blue-200/60 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                        </svg>
                        使用 {evaluator.usage_count} 次
                      </span>
                    </span>
                  </div>
                </div>

                {/* Stats */}
                <div className="flex items-center gap-4 text-xs text-slate-500 pt-3 border-t border-slate-100">
                  {evaluator.created_by_username && (
                    <div className="flex items-center gap-1.5">
                      <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                      <span>{evaluator.created_by_username}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span>{new Date(evaluator.created_at).toLocaleDateString("zh-CN")}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {total > 0 && (
            <div className="mt-4">
              <Pagination
                page={page}
                pageSize={pageSize}
                total={total}
                onPageChange={(p) => setPage(p)}
                onPageSizeChange={(ps) => {
                  setPageSize(ps);
                  setPage(1);
                }}
              />
            </div>
          )}

          {filteredEvaluators.length === 0 && !loading && (
            <div className="bg-white rounded-2xl border border-slate-200/60 p-16 text-center shadow-sm">
              <div className="w-24 h-24 bg-gradient-to-br from-slate-100 to-slate-200 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-inner">
                <svg className="w-12 h-12 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">没有找到评估器</h3>
              <p className="text-slate-500 text-sm mb-8 max-w-sm mx-auto leading-relaxed">
                {searchQuery ? '尝试调整搜索条件，或创建新的评估器' : '还没有创建任何评估器，立即创建一个开始评估吧'}
              </p>
              <button 
                onClick={() => {
                  resetForm();
                  setShowCreateModal(true);
                }} 
                className="px-6 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-xl font-medium shadow-sm hover:shadow-md transition-all duration-200 flex items-center gap-2 mx-auto"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                </svg>
                创建评估器
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowCreateModal(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="relative border-b border-gray-200 px-6 py-4 bg-white">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {editingEvaluatorId ? "编辑评估器" : "创建评估器"}
                  </h3>
                  <p className="text-sm text-gray-500 mt-0.5">配置评估维度和模型参数</p>
                </div>
              </div>
              <button 
                onClick={() => {
                  resetForm();
                  setShowCreateModal(false);
                }} 
                className="absolute top-4 right-4 w-8 h-8 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 flex items-center justify-center transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="space-y-5">
              {/* Name Input */}
              <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                  评估器名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="例如：RAG 质量评估器"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100 transition-all"
                  maxLength={100}
                />
              </div>

              {/* Description Input */}
              <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                  描述
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="简要描述评估器的用途和适用场景（可选）"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100 transition-all resize-none"
                  rows={3}
                />
              </div>

              {/* Metrics Selection */}
              <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-sm font-medium text-gray-700">
                  选择评估维度 <span className="text-red-500">*</span>
                    </label>
                    <span className={`px-2.5 py-1 rounded-md text-xs font-medium ${
                      formData.metric_ids.length > 0 
                        ? 'bg-green-50 text-green-700 border border-green-200' 
                        : 'bg-gray-50 text-gray-600 border border-gray-200'
                    }`}>
                      已选择 {formData.metric_ids.length} 个
                  </span>
                  </div>
                  
                  {metrics.length === 0 ? (
                    <div className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center">
                      <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                        </svg>
                      </div>
                      <p className="text-gray-600 font-medium text-sm">暂无可用的评估维度</p>
                      <p className="text-sm text-gray-500 mt-1">请先创建评估维度</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-72 overflow-y-auto pr-2">
                      {metrics.map((metric) => (
                        <label
                          key={metric.id}
                          className={`relative flex items-start gap-3 p-3.5 rounded-lg border-2 cursor-pointer transition-all ${
                            formData.metric_ids.includes(metric.id)
                              ? 'border-green-400 bg-green-50'
                              : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={formData.metric_ids.includes(metric.id)}
                            onChange={() => toggleMetricSelection(metric.id)}
                            className="mt-0.5 w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <span className="font-medium text-gray-900 text-sm">{metric.name}</span>
                              <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${
                                metric.type === 'builtin' 
                                  ? 'bg-blue-100 text-blue-700' 
                                  : 'bg-purple-100 text-purple-700'
                              }`}>
                                {metric.type === 'builtin' ? '内置' : '自定义'}
                              </span>
                            </div>
                            {metric.description && (
                              <p className="text-xs text-gray-600 line-clamp-2">{metric.description}</p>
                            )}
                            <div className="flex gap-1.5 mt-1.5">
                              {metric.llm_required && (
                                <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-orange-50 text-orange-700 border border-orange-200">
                                  LLM
                                </span>
                              )}
                              {metric.embedding_required && (
                                <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-cyan-50 text-cyan-700 border border-cyan-200">
                                  Embedding
                                </span>
                              )}
                            </div>
                          </div>
                          {formData.metric_ids.includes(metric.id) && (
                            <div className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center shadow-sm">
                              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                              </svg>
                            </div>
                          )}
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                {/* Configuration Mode Toggle */}
                {formData.metric_ids.length > 0 && (
                  <div className="border-t border-gray-200 pt-5">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium text-gray-700">模型配置</h4>
                      <button
                        type="button"
                        onClick={() => {
                          const newMode = !advancedMode;
                          setAdvancedMode(newMode);
                          
                          // 切换到高级模式时，为已选择的维度初始化配置
                          if (newMode && formData.metric_ids.length > 0) {
                            const newConfigs: Record<string, MetricModelConfig> = {};
                            formData.metric_ids.forEach(metricId => {
                              const metric = metrics.find(m => m.id === metricId);
                              if (metric && !metricModelConfigs[metricId]) {
                                newConfigs[metricId] = {
                                  metric_id: metricId,
                                  llm_config: metric.llm_required ? { name: "gpt-3.5-turbo" } : undefined,
                                  embedding_config: metric.embedding_required ? { name: "text-embedding-ada-002" } : undefined,
                                };
                              }
                            });
                            if (Object.keys(newConfigs).length > 0) {
                              setMetricModelConfigs(prev => ({ ...prev, ...newConfigs }));
                            }
                          }
                        }}
                        className="text-xs text-green-600 hover:text-green-700 font-medium flex items-center gap-1"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {advancedMode ? '简化模式' : '高级模式（按维度配置）'}
                      </button>
                    </div>

                    {!advancedMode ? (
                      /* 简化模式：全局配置 */
                      <div className="space-y-3 bg-gray-50 rounded-lg p-4">
                        <p className="text-xs text-gray-600">
                          为所有维度配置默认模型（如需为不同维度配置不同模型，请切换到高级模式）
                        </p>
                        
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1.5">
                            默认 LLM 模型
                          </label>
                          {modelsLoading ? (
                            <div className="flex items-center gap-2 text-xs text-gray-500 py-2">
                              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              加载模型中...
                            </div>
                          ) : (
                            <select
                              value={defaultLlmConfig.name}
                              onChange={(e) => setDefaultLlmConfig(prev => ({ ...prev, name: e.target.value }))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100"
                            >
                              <option value="">请选择模型</option>
                              {llmModels.map((model) => (
                                <option key={model.id} value={model.name}>
                                  {model.name} {model.is_default && "(默认)"}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1.5">
                            默认 Embedding 模型
                          </label>
                          {modelsLoading ? (
                            <div className="flex items-center gap-2 text-xs text-gray-500 py-2">
                              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              加载模型中...
                            </div>
                          ) : (
                            <select
                              value={defaultEmbeddingConfig.name}
                              onChange={(e) => setDefaultEmbeddingConfig(prev => ({ ...prev, name: e.target.value }))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100"
                            >
                              <option value="">请选择模型</option>
                              {embeddingModels.map((model) => (
                                <option key={model.id} value={model.name}>
                                  {model.name} {model.is_default && "(默认)"}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                      </div>
                    ) : (
                      /* 高级模式：按维度配置 */
                      <div className="space-y-3">
                        <p className="text-xs text-gray-600">
                          为每个维度单独配置模型，实现成本优化或使用专用模型
                        </p>
                        
                        {formData.metric_ids.map(metricId => {
                          const metric = metrics.find(m => m.id === metricId);
                          if (!metric) return null;

                          const config = metricModelConfigs[metricId];
                          
                          return (
                            <div key={metricId} className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                            <div className="flex items-center gap-2 mb-2.5">
                              <span className="font-medium text-sm text-gray-900">{metric.name}</span>
                              {metric.llm_required && (
                                <span className="px-1.5 py-0.5 text-[10px] rounded bg-orange-50 text-orange-700 border border-orange-200">需要LLM</span>
                              )}
                              {metric.embedding_required && (
                                <span className="px-1.5 py-0.5 text-[10px] rounded bg-cyan-50 text-cyan-700 border border-cyan-200">需要Embedding</span>
                              )}
                            </div>

                            <div className="space-y-2">
                              {metric.llm_required && (
                                <div>
                                  <label className="block text-xs font-medium text-gray-700 mb-1">
                                    LLM 模型
                                  </label>
                                  {modelsLoading ? (
                                    <div className="text-xs text-gray-500 py-1">加载中...</div>
                                  ) : (
                                    <select
                                      value={config?.llm_config?.name || ''}
                                      onChange={(e) => updateMetricModelConfig(metricId, 'llm', 'name', e.target.value)}
                                      className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-100"
                                    >
                                      <option value="">请选择模型</option>
                                      {llmModels.map((model) => (
                                        <option key={model.id} value={model.name}>
                                          {model.name} {model.is_default && "(默认)"}
                                        </option>
                                      ))}
                                    </select>
                                  )}
                                </div>
                              )}

                              {metric.embedding_required && (
                                <div>
                                  <label className="block text-xs font-medium text-gray-700 mb-1">
                                    Embedding 模型
                                  </label>
                                  {modelsLoading ? (
                                    <div className="text-xs text-gray-500 py-1">加载中...</div>
                                  ) : (
                                    <select
                                      value={config?.embedding_config?.name || ''}
                                      onChange={(e) => updateMetricModelConfig(metricId, 'embedding', 'name', e.target.value)}
                                      className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-100"
                                    >
                                      <option value="">请选择模型</option>
                                      {embeddingModels.map((model) => (
                                        <option key={model.id} value={model.name}>
                                          {model.name} {model.is_default && "(默认)"}
                                        </option>
                                      ))}
                                    </select>
                                  )}
                                </div>
                              )}
                              
                              {!metric.llm_required && !metric.embedding_required && (
                                <p className="text-xs text-gray-500 italic">此维度不需要配置模型</p>
                              )}
                            </div>
                          </div>
                        );
                      })}

                      {/* 全局兜底配置 */}
                      <div className="border-t border-gray-200 pt-3 mt-3">
                        <p className="text-xs text-gray-600 mb-2.5">
                          兜底配置（未单独配置的维度将使用以下默认值）
                        </p>
                        
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1.5">
                              默认 LLM
                            </label>
                            {modelsLoading ? (
                              <div className="text-xs text-gray-500 py-1">加载中...</div>
                            ) : (
                              <select
                                value={defaultLlmConfig.name}
                                onChange={(e) => setDefaultLlmConfig(prev => ({ ...prev, name: e.target.value }))}
                                className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-100"
                              >
                                <option value="">请选择模型</option>
                                {llmModels.map((model) => (
                                  <option key={model.id} value={model.name}>
                                    {model.name} {model.is_default && "(默认)"}
                                  </option>
                                ))}
                              </select>
                            )}
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1.5">
                              默认 Embedding
                            </label>
                            {modelsLoading ? (
                              <div className="text-xs text-gray-500 py-1">加载中...</div>
                            ) : (
                              <select
                                value={defaultEmbeddingConfig.name}
                                onChange={(e) => setDefaultEmbeddingConfig(prev => ({ ...prev, name: e.target.value }))}
                                className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-100"
                              >
                                <option value="">请选择模型</option>
                                {embeddingModels.map((model) => (
                                  <option key={model.id} value={model.name}>
                                    {model.name} {model.is_default && "(默认)"}
                                  </option>
                                ))}
                              </select>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  </div>
                )}
              </div>
            </div>

            {/* Footer Actions */}
            <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex justify-end gap-3">
              <button 
                onClick={() => {
                  resetForm();
                  setShowCreateModal(false);
                }} 
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg font-medium transition-colors"
                disabled={creating || updating}
              >
                取消
              </button>
              <button 
                onClick={editingEvaluatorId ? handleUpdate : handleCreate}
                disabled={(creating || updating) || !formData.name.trim() || formData.metric_ids.length === 0}
                className="px-5 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors flex items-center gap-2"
              >
                {(creating || updating) && (
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {creating ? "创建中..." : updating ? "更新中..." : editingEvaluatorId ? "更新评估器" : "创建评估器"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

