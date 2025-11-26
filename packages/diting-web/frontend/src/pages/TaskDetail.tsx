import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getTask,
  getEvaluationResults,
  getEvaluationSummary,
  exportEvaluationResults,
  retryTask,
  cancelTask,
  getEvaluator,
  // Synthesis
  getSynthesisResults,
  exportSynthesisResults,
  createDatasetFromSynthesisResults,
  // Negative Mining
  getNegativeMiningResults,
  exportNegativeMiningResults,
  createDatasetFromNegativeMiningResults,
} from "@/api/client";
import type { TaskResponse, EvaluatorResponse } from "@/types/api";

export default function TaskDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [results, setResults] = useState<any[]>([]); // evaluation results
  const [synthResults, setSynthResults] = useState<any[]>([]); // synthesis results
  const [negMiningResults, setNegMiningResults] = useState<any[]>([]); // negative mining results
  const [allNegMiningResults, setAllNegMiningResults] = useState<any[]>([]); // all negative mining results for pagination
  const [summary, setSummary] = useState<any>(null);
  const [evaluator, setEvaluator] = useState<EvaluatorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingResults, setLoadingResults] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [negMiningPage, setNegMiningPage] = useState(1);
  const [negMiningTotal, setNegMiningTotal] = useState(0);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"flat" | "pivot">("pivot");
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [expandedNegMiningCards, setExpandedNegMiningCards] = useState<Set<number>>(new Set());
  const [editingCardId, setEditingCardId] = useState<number | null>(null);
  const [editedQuestion, setEditedQuestion] = useState<string>("");
  const [editedAnswer, setEditedAnswer] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"overview" | "results">("overview");
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState<string>("all");
  const [allResults, setAllResults] = useState<any[]>([]);
  const [loadingAllResults, setLoadingAllResults] = useState(false);
  const pageSize = 20;
  const negMiningPageSize = 10;
  
  const toggleRowExpansion = (idx: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(idx)) {
      newExpanded.delete(idx);
    } else {
      newExpanded.add(idx);
    }
    setExpandedRows(newExpanded);
  };

  const toggleNegMiningCard = (idx: number) => {
    const newExpanded = new Set(expandedNegMiningCards);
    if (newExpanded.has(idx)) {
      newExpanded.delete(idx);
    } else {
      newExpanded.add(idx);
    }
    setExpandedNegMiningCards(newExpanded);
  };

  const handleEditCard = (idx: number, question: string, answer: string) => {
    setEditingCardId(idx);
    setEditedQuestion(question);
    setEditedAnswer(answer);
  };

  const handleSaveCard = (idx: number) => {
    const updatedResults = [...synthResults];
    updatedResults[idx] = {
      ...updatedResults[idx],
      question: editedQuestion,
      answer: editedAnswer,
    };
    setSynthResults(updatedResults);
    setEditingCardId(null);
  };

  const handleCancelEdit = () => {
    setEditingCardId(null);
    setEditedQuestion("");
    setEditedAnswer("");
  };

  useEffect(() => {
    if (taskId) {
      fetchTask();
    }
  }, [taskId]);

  useEffect(() => {
    if (!task) return;
    if (task.task_type === "evaluation" || task.task_type === "batch_evaluation") {
      fetchEvaluationData();
    } else if (task.task_type === "synthesis") {
      fetchSynthesisData();
    } else if (task.task_type === "negative_mining") {
      fetchNegativeMiningData();
    }
  }, [task, page, viewMode]);

  // Load results in batches when on overview tab with metric selection
  useEffect(() => {
    if (activeTab === "overview" && task && (task.task_type === "evaluation" || task.task_type === "batch_evaluation") && total > 0 && allResults.length === 0 && !loadingAllResults && selectedMetric !== "all") {
      const loadAllResults = async () => {
        try {
          setLoadingAllResults(true);
          // Load with a reasonable limit to avoid performance issues
          // For large datasets, use sampling instead of loading everything
          const maxLoadSize = Math.min(total, 1000); // Limit to 1000 records
          const allResultsData = await getEvaluationResults(taskId!, 1, maxLoadSize, true);
          setAllResults(allResultsData.items);
        } catch (err) {
          console.warn("Failed to fetch all results:", err);
        } finally {
          setLoadingAllResults(false);
        }
      };
      loadAllResults();
    }
  }, [activeTab, task, total, allResults.length, taskId, loadingAllResults, selectedMetric]);

  useEffect(() => {
    if (!task || task.task_type !== "negative_mining") return;
    // Update paginated results when page changes
    const startIndex = (negMiningPage - 1) * negMiningPageSize;
    const endIndex = startIndex + negMiningPageSize;
    setNegMiningResults(allNegMiningResults.slice(startIndex, endIndex));
  }, [negMiningPage, allNegMiningResults, task]);

  const fetchTask = async () => {
    try {
      setLoading(true);
      setError("");
      const taskData = await getTask(taskId!);
      setTask(taskData);
      
      // Fetch evaluator if evaluator_id exists in config
      if (taskData.config?.evaluator_id) {
        try {
          const evaluatorData = await getEvaluator(taskData.config.evaluator_id);
          setEvaluator(evaluatorData);
        } catch (err: any) {
          console.warn("Failed to fetch evaluator:", err);
          // Don't show error if evaluator not found, just leave it null
        }
      }
    } catch (err: any) {
      console.error("Failed to fetch task:", err);
      setError("加载任务失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchEvaluationData = async () => {
    try {
      setLoadingResults(true);
      const [resultsData, summaryData] = await Promise.all([
        getEvaluationResults(taskId!, page, pageSize, viewMode === "pivot"),
        getEvaluationSummary(taskId!),
      ]);
      setResults(resultsData.items);
      setTotal(resultsData.total);
      setSummary(summaryData);
    } catch (err: any) {
      console.error("Failed to fetch evaluation data:", err);
      // 如果任务还没完成,不显示错误
      if (task?.status === "completed") {
        setError("加载评估结果失败");
      }
    } finally {
      setLoadingResults(false);
    }
  };

  const fetchSynthesisData = async () => {
    try {
      setLoadingResults(true);
      const data = await getSynthesisResults(taskId!);
      const raw = Array.isArray(data) ? data : [];
      const fallback = Array.isArray((task as any)?.result?.results) ? (task as any).result.results : [];
      const enriched = raw.map((r: any, idx: number) => {
        const fb = fallback[idx] || {};
        const fbScore = fb?.metadata?.score ?? null;
        const fbCtx = fb?.context ?? null;
        return {
          ...r,
          quality_score: r?.quality_score ?? fbScore,
          source_context: r?.source_context ?? fbCtx,
        };
      });
      setSynthResults(enriched);
    } catch (err: any) {
      console.error("Failed to fetch synthesis data:", err);
      if (task?.status === "completed") {
        setError("加载合成结果失败");
      }
    } finally {
      setLoadingResults(false);
    }
  };

  const fetchNegativeMiningData = async () => {
    try {
      setLoadingResults(true);
      const data = await getNegativeMiningResults(taskId!);
      const resultsArray = Array.isArray(data) ? data : [];
      setAllNegMiningResults(resultsArray);
      setNegMiningTotal(resultsArray.length);
      // Set first page
      setNegMiningPage(1);
      const firstPageResults = resultsArray.slice(0, negMiningPageSize);
      setNegMiningResults(firstPageResults);
    } catch (err: any) {
      console.error("Failed to fetch negative mining data:", err);
      if (task?.status === "completed") {
        setError("加载负样本挖掘结果失败");
      }
    } finally {
      setLoadingResults(false);
    }
  };

  const handleExportSynthesis = async (format: "csv" | "jsonl" = "csv") => {
    if (!task) return;
    try {
      setActionLoading(`export-synth-${format}`);
      await exportSynthesisResults(task.id, format);
    } catch (err: any) {
      alert("导出失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  const handleExportNegativeMining = async (format: "json" | "jsonl" = "json") => {
    if (!task) return;
    try {
      setActionLoading(`export-negmining-${format}`);
      await exportNegativeMiningResults(task.id, format);
    } catch (err: any) {
      alert("导出失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateDatasetFromNegativeMining = async (name?: string, description?: string) => {
    if (!task) return;
    const datasetName = name || prompt("请输入数据集名称", "negative_mining_results");
    if (!datasetName) return;
    try {
      setActionLoading("create-dataset-negmining");
      await createDatasetFromNegativeMiningResults(task.id, datasetName, description);
      alert("数据集创建成功");
    } catch (err: any) {
      alert("创建数据集失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateDatasetFromSynthesis = async (name?: string, description?: string) => {
    if (!task) return;
    const datasetName = name || prompt("请输入数据集名称", "synthesis_results");
    if (!datasetName) return;
    try {
      setActionLoading("create-dataset");
      await createDatasetFromSynthesisResults(task.id, datasetName, description);
      alert("数据集创建成功");
    } catch (err: any) {
      alert("创建数据集失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  const handleRetry = async () => {
    if (!task || !window.confirm("确定要重试这个任务吗？")) return;

    setActionLoading("retry");
    try {
      await retryTask(task.id);
      alert("任务已重新提交！");
      fetchTask();
    } catch (err: any) {
      alert("重试失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  const handleCancel = async () => {
    if (!task || !window.confirm("确定要取消这个任务吗？")) return;

    setActionLoading("cancel");
    try {
      await cancelTask(task.id);
      alert("任务已取消！");
      fetchTask();
    } catch (err: any) {
      alert("取消失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };


  const handleExport = async (format: "csv" | "excel" | "jsonl") => {
    if (!task) return;

    setActionLoading(`export-${format}`);
    try {
      await exportEvaluationResults(task.id, format);
    } catch (err: any) {
      alert("导出失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("zh-CN");
  };

  const formatDuration = (start: string | null, end: string | null) => {
    if (!start || !end) return "-";
    const duration = new Date(end).getTime() - new Date(start).getTime();
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}小时${minutes % 60}分${seconds % 60}秒`;
    if (minutes > 0) return `${minutes}分${seconds % 60}秒`;
    return `${seconds}秒`;
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { label: "等待中", class: "bg-gray-100 text-gray-700" },
      running: { label: "运行中", class: "bg-blue-100 text-blue-700" },
      completed: { label: "已完成", class: "bg-green-100 text-green-700" },
      failed: { label: "失败", class: "bg-red-100 text-red-700" },
      cancelled: { label: "已取消", class: "bg-gray-100 text-gray-700" },
    };
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${config.class}`}>
        {config.label}
      </span>
    );
  };

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

  if (error || !task) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || "任务不存在"}
        </div>
      </div>
    );
  }

  const getTaskTypeLabel = (type: string) => {
    switch (type) {
      case "evaluation":
      case "batch_evaluation":
        return "评估";
      case "synthesis":
        return "数据合成";
      case "negative_mining":
        return "负例挖掘";
      default:
        return type;
    }
  };

  const isEvaluationTask = task.task_type === "evaluation" || task.task_type === "batch_evaluation";

  return (
    <div className="max-w-[1600px] mx-auto space-y-4 px-4 py-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {task.name || "任务详情"}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {task.status === "failed" && (
            <button
              onClick={handleRetry}
              disabled={actionLoading === "retry"}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {actionLoading === "retry" ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  重试中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  重试
                </>
              )}
            </button>
          )}

          {(task.status === "pending" || task.status === "running") && (
            <button
              onClick={handleCancel}
              disabled={actionLoading === "cancel"}
              className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 flex items-center gap-2"
            >
              {actionLoading === "cancel" ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  取消中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  取消任务
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Evaluation Results */}
      {isEvaluationTask && task.status === "completed" && (
        <div className="bg-white rounded-lg border border-gray-200">
          {/* Tabs Navigation */}
          <div className="border-b border-gray-200">
            <nav className="flex gap-2 px-6 pt-4">
              <button
                onClick={() => setActiveTab("overview")}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg font-medium text-sm transition-all ${
                  activeTab === "overview"
                    ? "bg-green-50 text-green-700 border-b-2 border-green-600"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                概览
              </button>
              <button
                onClick={() => setActiveTab("results")}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg font-medium text-sm transition-all ${
                  activeTab === "results"
                    ? "bg-green-50 text-green-700 border-b-2 border-green-600"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                评估结果 ({total})
              </button>
            </nav>
          </div>

          {/* Tab Contents */}
          <div className="p-4">
            {/* Overview Tab */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                {/* Basic Info */}
                <div className="bg-white rounded-lg border border-gray-200 px-4 py-3">
                  <h3 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    基本信息
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-8 gap-y-3.5 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">任务类型</span>
                      <span className="font-medium text-gray-900">{getTaskTypeLabel(task.task_type)}</span>
                    </div>
                    {(task.task_type === "batch_evaluation" || task.task_type === "evaluation") && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">{evaluator ? "评估器" : "指标"}</span>
                        <span className="font-medium text-gray-900 truncate ml-2" title={
                          evaluator
                            ? evaluator.name
                            : (summary && summary.metrics_summary && Object.keys(summary.metrics_summary).length > 0
                                ? Object.keys(summary.metrics_summary).join("、")
                                : (results[0]?.metric_name || "-"))
                        }>
                          {evaluator
                            ? evaluator.name
                            : (summary && summary.metrics_summary && Object.keys(summary.metrics_summary).length > 0
                                ? Object.keys(summary.metrics_summary).join("、")
                                : (results[0]?.metric_name || "-"))}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">状态</span>
                      <span>{getStatusBadge(task.status)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">进度</span>
                      <span className="font-medium text-gray-900">{Number(task.progress).toFixed(1)}%</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">创建时间</span>
                      <span className="font-medium text-gray-900">{formatDate(task.created_at)}</span>
                    </div>
                    {task.started_at && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">开始时间</span>
                        <span className="font-medium text-gray-900">{formatDate(task.started_at)}</span>
                      </div>
                    )}
                    {task.completed_at && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">完成时间</span>
                        <span className="font-medium text-gray-900">{formatDate(task.completed_at)}</span>
                      </div>
                    )}
                    {task.started_at && task.completed_at && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">耗时</span>
                        <span className="font-medium text-gray-900">
                          {formatDuration(task.started_at, task.completed_at)}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">Token 消耗</span>
                      <span className="font-medium text-gray-900">{task.total_tokens.toLocaleString()}</span>
                    </div>
                    {task.total_cost && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">成本</span>
                        <span className="font-medium text-gray-900">${Number(task.total_cost).toFixed(4)}</span>
                      </div>
                    )}
                  </div>

                  {task.error && (
                    <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs">
                      <span className="font-medium text-red-700">错误：</span>
                      <span className="text-red-600">{task.error}</span>
                    </div>
                  )}
                </div>

                {/* Score Distribution Section */}
                {summary && (
                  <div className="bg-white rounded-lg border border-gray-200 px-4 py-3">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                        <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        分数分布
                      </h3>
                      {/* Metric Selector */}
                      {summary.metrics_summary && Object.keys(summary.metrics_summary).length > 1 && (
                        <div className="flex items-center gap-2">
                          <label className="text-xs text-gray-600">按指标筛选：</label>
                          <select
                            value={selectedMetric}
                            onChange={(e) => setSelectedMetric(e.target.value)}
                            className="px-2 py-1 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                          >
                            <option value="all">全部指标</option>
                            {Object.keys(summary.metrics_summary).map((metric) => (
                              <option key={metric} value={metric}>
                                {metric.replace(/_/g, ' ')}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>

                    {loadingAllResults && selectedMetric !== "all" && allResults.length === 0 ? (
                      <div className="flex flex-col items-center justify-center p-6 gap-2">
                        <svg className="animate-spin h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span className="text-xs text-gray-500">加载完整数据中...</span>
                      </div>
                    ) : (() => {
                      // Calculate distribution based on selected metric
                      let displayDistribution: Record<string, number> = {
                        "0.0-0.2": 0,
                        "0.2-0.4": 0,
                        "0.4-0.6": 0,
                        "0.6-0.8": 0,
                        "0.8-1.0": 0,
                      };
                      let displayTotalCount = 0;
                      let displayAvgScore = 0;
                      let displayPassRate = 0;
                      let scoreSum = 0;
                      let passCount = 0;

                      if (selectedMetric === "all") {
                        // Use overall distribution
                        displayDistribution = summary.score_distribution || displayDistribution;
                        displayTotalCount = summary.total_count;
                        displayAvgScore = summary.average_score;
                        displayPassRate = summary.pass_rate;
                      } else {
                        // Calculate distribution from all results for specific metric
                        const dataSource = allResults.length > 0 ? allResults : results;
                        
                        dataSource.forEach((r: any) => {
                          if (r.metrics && r.metrics[selectedMetric]) {
                            const metricData = r.metrics[selectedMetric];
                            const score = metricData.score;
                            
                            if (score !== null && score !== undefined) {
                              displayTotalCount++;
                              scoreSum += score;
                              if (score >= 0.7) passCount++;

                              if (score < 0.2) {
                                displayDistribution["0.0-0.2"]++;
                              } else if (score < 0.4) {
                                displayDistribution["0.2-0.4"]++;
                              } else if (score < 0.6) {
                                displayDistribution["0.4-0.6"]++;
                              } else if (score < 0.8) {
                                displayDistribution["0.6-0.8"]++;
                              } else {
                                displayDistribution["0.8-1.0"]++;
                              }
                            }
                          }
                        });

                        displayAvgScore = displayTotalCount > 0 ? scoreSum / displayTotalCount : 0;
                        displayPassRate = displayTotalCount > 0 ? passCount / displayTotalCount : 0;
                      }

                      return displayTotalCount > 0 ? (
                        <>
                          <div className="space-y-3">
                            {Object.entries(displayDistribution).map(([range, count]) => (
                              <div key={range} className="flex items-center gap-3">
                                <div className="w-20 text-sm text-gray-700 font-semibold">{range}</div>
                                <div className="flex-1 h-10 bg-gray-100 rounded-lg overflow-hidden relative">
                                  <div
                                    className="h-full bg-gradient-to-r from-green-400 to-green-600 flex items-center transition-all duration-500"
                                    style={{
                                      width: `${((count as number) / displayTotalCount) * 100}%`,
                                    }}
                                  >
                                    {count as number > 0 && (
                                      <span className="ml-3 text-xs font-bold text-white">
                                        {count as number} 条
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="w-16 text-sm text-gray-700 font-semibold text-right">
                                  {(((count as number) / displayTotalCount) * 100).toFixed(1)}%
                                </div>
                              </div>
                            ))}
                          </div>
                          <div className="mt-5 pt-5 border-t border-gray-200">
                            <div className="grid grid-cols-3 gap-4 text-center">
                              <div>
                                <div className="text-xs text-gray-500 mb-1">总样本数</div>
                                <div className="text-lg font-bold text-gray-900">{displayTotalCount}</div>
                              </div>
                              <div>
                                <div className="text-xs text-gray-500 mb-1">平均分</div>
                                <div className="text-lg font-bold text-blue-600">
                                  {displayAvgScore !== null ? displayAvgScore.toFixed(2) : "-"}
                                </div>
                              </div>
                              <div>
                                <div className="text-xs text-gray-500 mb-1 flex items-center justify-center gap-1">
                                  <span>通过率</span>
                                  <div className="group relative">
                                    <svg className="w-3.5 h-3.5 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <div className="invisible group-hover:visible absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                                      分数 ≥ 0.7 的样本占比
                                      <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                                        <div className="border-4 border-transparent border-t-gray-900"></div>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                                <div className="text-lg font-bold text-green-600">
                                  {displayPassRate !== null ? (displayPassRate * 100).toFixed(1) + "%" : "-"}
                                </div>
                              </div>
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="text-center py-6 text-gray-500 text-sm">
                          暂无分数分布数据
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            )}

            {/* Results Tab */}
            {activeTab === "results" && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-semibold text-gray-900">评估结果 ({total})</h2>
                  <div className="flex items-center gap-2">
                    {/* Export Dropdown */}
                    <div className="relative">
                      <button
                        onClick={() => setShowExportMenu(!showExportMenu)}
                        className="px-2.5 py-1.5 text-xs font-medium bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors flex items-center gap-1.5"
                        disabled={actionLoading?.startsWith("export")}
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        导出
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                      {showExportMenu && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={() => setShowExportMenu(false)}></div>
                          <div className="absolute right-0 mt-1 w-32 bg-white rounded-md shadow-lg border border-gray-200 z-20">
                            <div className="py-1">
                              <button
                                onClick={() => {
                                  handleExport("csv");
                                  setShowExportMenu(false);
                                }}
                                disabled={actionLoading === "export-csv"}
                                className="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-gray-100 disabled:opacity-50 flex items-center gap-2"
                              >
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                导出 CSV
                              </button>
                              <button
                                onClick={() => {
                                  handleExport("excel");
                                  setShowExportMenu(false);
                                }}
                                disabled={actionLoading === "export-excel"}
                                className="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-gray-100 disabled:opacity-50 flex items-center gap-2"
                              >
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                                导出 Excel
                              </button>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                    <div className="w-px h-6 bg-gray-300"></div>
                    <button
                      onClick={() => setViewMode("flat")}
                      className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                        viewMode === "flat"
                          ? "bg-green-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      平铺视图
                    </button>
                    <button
                      onClick={() => setViewMode("pivot")}
                      className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                        viewMode === "pivot"
                          ? "bg-green-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      汇总视图
                    </button>
                  </div>
                </div>

                {loadingResults ? (
                  <div className="flex items-center justify-center p-8">
                    <svg className="animate-spin h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                ) : results.length > 0 ? (
                  <>
                    <div className="overflow-x-auto border border-gray-200 rounded-lg">
                      {viewMode === "flat" ? (
                        <table className="w-full">
                          <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                              <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">指标</th>
                              <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">分数</th>
                              <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">原因</th>
                              <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">输入</th>
                              <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">输出</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200">
                            {results.map((result, idx) => (
                              <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-sm font-medium text-gray-900">{result.metric_name}</td>
                                <td className="px-4 py-3">
                                  {result.score !== null && result.score !== undefined ? (
                                    <span className={`text-sm font-semibold ${
                                      result.score >= 0.7 ? "text-green-600" :
                                      result.score >= 0.5 ? "text-yellow-600" :
                                      "text-red-600"
                                    }`}>
                                      {result.score.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
                                      失败
                                    </span>
                                  )}
                                </td>
                                <td className={`px-4 py-3 text-sm max-w-md truncate ${
                                  result.score === null || result.score === undefined ? "text-red-600 font-medium" : "text-gray-600"
                                }`} title={result.reason}>
                                  {result.reason || "-"}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate" title={result.user_input}>
                                  {result.user_input || "-"}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate" title={result.actual_output}>
                                  {result.actual_output || "-"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <table className="w-full table-fixed">
                          <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                              <th className="w-10"></th>
                              <th className="w-[25%] px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">输入</th>
                              <th className="w-[25%] px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">输出</th>
                              {results.length > 0 && Object.keys(results[0].metrics || {}).map((metricName) => (
                                <th key={metricName} className="px-4 py-2.5 text-center text-xs font-medium text-gray-500 uppercase min-w-[120px]">
                                  <div className="flex flex-col items-center gap-1">
                                    <span className="text-center">{metricName.replace(/_/g, ' ')}</span>
                                  </div>
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200">
                            {results.map((result, idx) => (
                              <>
                                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                                  <td className="px-3 py-3">
                                    <button
                                      onClick={() => toggleRowExpansion(idx)}
                                      className="text-gray-400 hover:text-gray-600 transition-colors"
                                      title={expandedRows.has(idx) ? "收起详情" : "展开详情"}
                                    >
                                      <svg 
                                        className={`w-5 h-5 transition-transform ${expandedRows.has(idx) ? 'rotate-90' : ''}`} 
                                        fill="none" 
                                        stroke="currentColor" 
                                        viewBox="0 0 24 24"
                                      >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                                      </svg>
                                    </button>
                                  </td>
                                  <td className="px-4 py-3 text-sm text-gray-600 max-w-xs">
                                    <div className="truncate" title={result.user_input}>
                                      {result.user_input || "-"}
                                    </div>
                                  </td>
                                  <td className="px-4 py-3 text-sm text-gray-600 max-w-xs">
                                    <div className="truncate" title={result.actual_output}>
                                      {result.actual_output || "-"}
                                    </div>
                                  </td>
                                  {Object.entries(result.metrics || {}).map(([metricName, metricData]: [string, any]) => (
                                    <td key={metricName} className="px-4 py-3">
                                      <div className="flex flex-col items-center gap-2">
                                        {metricData?.score !== null && metricData?.score !== undefined ? (
                                          <>
                                            <div className="w-full px-2">
                                              <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                                                <div 
                                                  className={`h-full transition-all ${
                                                    metricData.score >= 0.7 ? "bg-green-500" :
                                                    metricData.score >= 0.5 ? "bg-yellow-500" :
                                                    "bg-red-500"
                                                  }`}
                                                  style={{ width: `${metricData.score * 100}%` }}
                                                />
                                              </div>
                                            </div>
                                            <span className={`text-base font-semibold ${
                                              metricData.score >= 0.7 ? "text-green-600" :
                                              metricData.score >= 0.5 ? "text-yellow-600" :
                                              "text-red-600"
                                            }`}>
                                              {metricData.score.toFixed(2)}
                                            </span>
                                          </>
                                        ) : (
                                          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
                                            失败
                                          </span>
                                        )}
                                      </div>
                                    </td>
                                  ))}
                                </tr>
                                {expandedRows.has(idx) && (
                                  <tr className="bg-gray-50">
                                    <td></td>
                                    <td colSpan={2} className="px-6 py-4">
                                      <div className="space-y-2">
                                        <div className="text-xs font-medium text-gray-500 uppercase">完整内容</div>
                                        <div className="space-y-2 text-sm">
                                          <div>
                                            <span className="font-medium text-gray-700">输入：</span>
                                            <div className="mt-1 text-gray-600 whitespace-pre-wrap">{result.user_input || "-"}</div>
                                          </div>
                                          <div>
                                            <span className="font-medium text-gray-700">输出：</span>
                                            <div className="mt-1 text-gray-600 whitespace-pre-wrap">{result.actual_output || "-"}</div>
                                          </div>
                                          {result.expected_output && (
                                            <div>
                                              <span className="font-medium text-gray-700">期望输出：</span>
                                              <div className="mt-1 text-gray-600 whitespace-pre-wrap">{result.expected_output}</div>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </td>
                                    <td colSpan={Object.keys(result.metrics || {}).length} className="px-6 py-4">
                                      <div className="space-y-3">
                                        <div className="text-xs font-medium text-gray-500 uppercase">评估详情</div>
                                        {Object.entries(result.metrics || {}).map(([metricName, metricData]: [string, any]) => (
                                          <div key={metricName} className="border-l-2 border-gray-300 pl-3 py-1">
                                            <div className="flex items-center gap-2 mb-1">
                                              <span className="text-sm font-medium text-gray-700">{metricName.replace(/_/g, ' ')}</span>
                                              {metricData?.score !== null && metricData?.score !== undefined && (
                                                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                                                  metricData.score >= 0.7 ? "bg-green-100 text-green-700" :
                                                  metricData.score >= 0.5 ? "bg-yellow-100 text-yellow-700" :
                                                  "bg-red-100 text-red-700"
                                                }`}>
                                                  {metricData.score.toFixed(2)}
                                                </span>
                                              )}
                                            </div>
                                            {metricData?.reason && (
                                              <div className="text-xs text-gray-600 whitespace-pre-wrap">
                                                {metricData.reason}
                                              </div>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </td>
                                  </tr>
                                )}
                              </>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>

                    {/* Pagination */}
                    {total > pageSize && (
                      <div className="mt-4 p-4 border border-gray-200 rounded-lg flex items-center justify-between">
                        <div className="text-sm text-gray-600">
                          显示 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} / 共 {total} 条
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
                          >
                            上一页
                          </button>
                          <span className="text-sm text-gray-600">
                            第 {page} / {Math.ceil(total / pageSize)} 页
                          </span>
                          <button
                            onClick={() => setPage(p => Math.min(Math.ceil(total / pageSize), p + 1))}
                            disabled={page >= Math.ceil(total / pageSize)}
                            className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
                          >
                            下一页
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="p-8 text-center text-gray-500">暂无评估结果</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Synthesis Results */}
      {task.task_type === "synthesis" && task.status === "completed" && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-6 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">合成结果 ({synthResults.length})</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleExportSynthesis("csv")}
                disabled={actionLoading === "export-synth-csv"}
                className="px-3 py-1.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50"
              >
                {actionLoading === "export-synth-csv" ? "导出中..." : "导出 CSV"}
              </button>
              <button
                onClick={() => handleExportSynthesis("jsonl")}
                disabled={actionLoading === "export-synth-jsonl"}
                className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {actionLoading === "export-synth-jsonl" ? "导出中..." : "导出 JSONL"}
              </button>
              <button
                onClick={() => handleCreateDatasetFromSynthesis()}
                disabled={actionLoading === "create-dataset"}
                className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {actionLoading === "create-dataset" ? "创建中..." : "导入为数据集"}
              </button>
            </div>
          </div>

          {loadingResults ? (
            <div className="flex items-center justify-center p-8">
              <svg className="animate-spin h-8 w-8 text-brand-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          ) : synthResults.length > 0 ? (
            <div className="p-6 grid grid-cols-1 gap-3">
              {synthResults.map((item, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all bg-gray-50 hover:bg-white">
                  {editingCardId === idx ? (
                    // 编辑模式
                    <div className="space-y-3">
                      <textarea
                        value={editedQuestion}
                        onChange={(e) => setEditedQuestion(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none text-gray-900 font-medium"
                        rows={2}
                        placeholder="问题"
                      />
                      <textarea
                        value={editedAnswer}
                        onChange={(e) => setEditedAnswer(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none text-gray-600"
                        rows={2}
                        placeholder="答案"
                      />
                      <div className="flex items-center justify-between pt-1">
                        <div className="text-sm text-gray-500">
                          质量分: <span className="font-semibold text-gray-700">{item.quality_score ?? '-'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleCancelEdit()}
                            className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                          >
                            取消
                          </button>
                          <button
                            onClick={() => handleSaveCard(idx)}
                            className="px-3 py-1.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
                          >
                            保存
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    // 查看模式
                    <div className="space-y-2.5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0 text-[14px] leading-relaxed text-gray-900 font-semibold whitespace-pre-wrap break-words">
                          {item.question}
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {item.quality_score !== null && item.quality_score !== undefined && (
                            <div className="px-2 py-0.5 bg-brand-50 rounded">
                              <span className="text-xs font-semibold text-brand-700">{item.quality_score}</span>
                            </div>
                          )}
                          <button
                            onClick={() => handleEditCard(idx, item.question, item.answer)}
                            className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-brand-50 rounded transition-colors"
                            title="编辑"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      <div className="text-[14px] leading-relaxed text-gray-600 whitespace-pre-wrap break-words">
                        {item.answer}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">暂无合成结果</div>
          )}
        </div>
      )}
      
      {/* Negative Mining Results */}
      {task.task_type === "negative_mining" && task.status === "completed" && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="p-6 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">负样本挖掘结果 (共 {negMiningTotal} 条)</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleExportNegativeMining("json")}
                disabled={actionLoading === "export-negmining-json"}
                className="px-3 py-1.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50"
              >
                {actionLoading === "export-negmining-json" ? "导出中..." : "导出 JSON"}
              </button>
              <button
                onClick={() => handleExportNegativeMining("jsonl")}
                disabled={actionLoading === "export-negmining-jsonl"}
                className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {actionLoading === "export-negmining-jsonl" ? "导出中..." : "导出 JSONL"}
              </button>
              <button
                onClick={() => handleCreateDatasetFromNegativeMining()}
                disabled={actionLoading === "create-dataset-negmining"}
                className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {actionLoading === "create-dataset-negmining" ? "创建中..." : "导入为数据集"}
              </button>
            </div>
          </div>

          {loadingResults ? (
            <div className="flex items-center justify-center p-8">
              <svg className="animate-spin h-8 w-8 text-brand-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          ) : negMiningResults.length > 0 ? (
            <>
              <div className="p-6 space-y-3">
                {negMiningResults.map((item: any, idx: number) => {
                  const globalIdx = (negMiningPage - 1) * negMiningPageSize + idx;
                  const isExpanded = expandedNegMiningCards.has(globalIdx);
                  
                  return (
                    <div 
                      key={idx} 
                      className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-all bg-white"
                    >
                      {/* Card Header - Always Visible */}
                      <div 
                        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                        onClick={() => toggleNegMiningCard(globalIdx)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3">
                              <div className={`transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                                </svg>
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium text-gray-900 truncate" title={item.query}>
                                  {item.query}
                                </div>
                                <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                                  <span className="flex items-center gap-1">
                                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                    正样本: {item.pos?.length || 0}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                    负样本: {item.neg?.length || 0}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                          <div className="ml-4 text-xs text-gray-400">
                            {isExpanded ? '点击收起' : '点击展开'}
                          </div>
                        </div>
                      </div>

                      {/* Card Details - Expandable */}
                      {isExpanded && (
                        <div className="border-t border-gray-200 bg-gray-50 p-4">
                          <div className="space-y-4">
                            {/* Query Full Text */}
                            <div>
                              <div className="text-xs font-semibold text-gray-500 mb-2">查询 (Query)</div>
                              <div className="text-sm text-gray-900 bg-white p-3 rounded border border-gray-200 whitespace-pre-wrap">
                                {item.query}
                              </div>
                            </div>
                            
                            {/* Positive samples */}
                            {item.pos && item.pos.length > 0 && (
                              <div>
                                <div className="text-xs font-semibold text-green-600 mb-2">
                                  正样本 ({item.pos.length})
                                </div>
                                <div className="space-y-2">
                                  {item.pos.map((pos: string, posIdx: number) => (
                                    <div key={posIdx} className="text-sm text-gray-700 bg-green-50 p-3 rounded border border-green-200 whitespace-pre-wrap">
                                      {pos}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Negative samples */}
                            {item.neg && item.neg.length > 0 && (
                              <div>
                                <div className="text-xs font-semibold text-red-600 mb-2">
                                  负样本 ({item.neg.length})
                                </div>
                                <div className="space-y-2">
                                  {item.neg.map((neg: string, negIdx: number) => (
                                    <div key={negIdx} className="text-sm text-gray-700 bg-red-50 p-3 rounded border border-red-200 whitespace-pre-wrap">
                                      {neg}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              
              {/* Pagination */}
              {negMiningTotal > negMiningPageSize && (
                <div className="px-6 pb-6 flex items-center justify-between border-t border-gray-200 pt-4">
                  <div className="text-sm text-gray-600">
                    显示第 {(negMiningPage - 1) * negMiningPageSize + 1} - {Math.min(negMiningPage * negMiningPageSize, negMiningTotal)} 条，共 {negMiningTotal} 条
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setNegMiningPage(Math.max(1, negMiningPage - 1))}
                      disabled={negMiningPage === 1}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
                    >
                      上一页
                    </button>
                    <span className="text-sm text-gray-600">
                      第 {negMiningPage} / {Math.ceil(negMiningTotal / negMiningPageSize)} 页
                    </span>
                    <button
                      onClick={() => setNegMiningPage(Math.min(Math.ceil(negMiningTotal / negMiningPageSize), negMiningPage + 1))}
                      disabled={negMiningPage >= Math.ceil(negMiningTotal / negMiningPageSize)}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="p-8 text-center text-gray-500">
              暂无负样本挖掘结果
            </div>
          )}
        </div>
      )}
    </div>
  );
}

