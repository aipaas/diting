import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  getEvaluators, 
  getDatasets, 
  createBatchEvaluationTask, 
  getTasks, 
  getMetrics,
  cancelTask,
  retryTask,
  deleteTask,
} from "@/api/client";
import type { EvaluatorResponse, DatasetResponse, TaskResponse, MetricResponse } from "@/types/api";

export default function EvaluationRun() {
  const navigate = useNavigate();
  const [evaluators, setEvaluators] = useState<EvaluatorResponse[]>([]);
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [metrics, setMetrics] = useState<MetricResponse[]>([]);
  const [recentTasks, setRecentTasks] = useState<TaskResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEvaluator, setSelectedEvaluator] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [actioningTask, setActioningTask] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError("");
      const [evaluatorsData, datasetsData, metricsData, tasksData] = await Promise.all([
        getEvaluators(1, 100),
        getDatasets(1, 20), // Reduced pageSize for better performance
        getMetrics(1, 100),
        getTasks(1, 5),
      ]);
      setEvaluators(evaluatorsData.items);
      setDatasets(datasetsData.items);
      setMetrics(metricsData.items);
      setRecentTasks(tasksData.items);
    } catch (err: any) {
      console.error("Failed to fetch data:", err);
      setError("加载数据失败");
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if (!selectedEvaluator || !datasetId) return;
    
    setIsRunning(true);
    try {
      await createBatchEvaluationTask({
        dataset_id: datasetId,
        evaluator_id: selectedEvaluator,
      });
      alert("评估任务已提交！请在任务列表中查看进度。");
      fetchData(); // 刷新最近任务
    } catch (err: any) {
      console.error("Failed to create evaluation task:", err);
      alert("创建任务失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setIsRunning(false);
    }
  };

  const selectedEvaluatorData = evaluators.find(e => e.id === selectedEvaluator);
  const selectedDatasetData = datasets.find(d => d.id === datasetId);
  
  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "刚刚";
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    return `${diffDays}天前`;
  };

  const getStatusConfig = (status: string) => {
    const configs = {
      completed: {
        label: "已完成",
        icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
        color: "text-green-600",
        bgColor: "bg-green-50",
        borderColor: "border-green-200",
        progressColor: "bg-green-500",
      },
      running: {
        label: "运行中",
        icon: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
        color: "text-blue-600",
        bgColor: "bg-blue-50",
        borderColor: "border-blue-200",
        progressColor: "bg-blue-500",
      },
      failed: {
        label: "失败",
        icon: "M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z",
        color: "text-red-600",
        bgColor: "bg-red-50",
        borderColor: "border-red-200",
        progressColor: "bg-red-500",
      },
      pending: {
        label: "等待中",
        icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
        color: "text-gray-600",
        bgColor: "bg-gray-50",
        borderColor: "border-gray-200",
        progressColor: "bg-gray-400",
      },
      cancelled: {
        label: "已取消",
        icon: "M6 18L18 6M6 6l12 12",
        color: "text-gray-600",
        bgColor: "bg-gray-50",
        borderColor: "border-gray-200",
        progressColor: "bg-gray-400",
      },
    };
    return configs[status as keyof typeof configs] || configs.pending;
  };

  const getTaskTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      evaluation: "单个评估",
      batch_evaluation: "批量评估",
      synthesis: "数据合成",
      negative_mining: "负样本挖掘",
    };
    return labels[type] || type;
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

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Quick Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div>
            <h3 className="text-sm font-semibold text-blue-900 mb-1">快速开始</h3>
            <p className="text-sm text-blue-700">选择一个评估器和数据集即可开始评估。评估器已预配置多个评估维度，无需重复设置。</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left Column - Configuration */}
        <div className="space-y-5">
          {/* Select Evaluator */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-green-600">1</span>
                </div>
                <h3 className="text-sm font-semibold text-gray-900">选择评估器</h3>
              </div>
            </div>
            <div className="p-5">
              {evaluators.length > 0 ? (
                <div className="space-y-3">
                  {evaluators.map((evaluator) => (
                    <label
                      key={evaluator.id}
                      className={`block p-4 rounded-lg border-2 cursor-pointer transition-all ${
                        selectedEvaluator === evaluator.id
                          ? "border-green-500 bg-green-50 shadow-sm"
                          : "border-gray-200 bg-white hover:border-green-300 hover:shadow-sm"
                      }`}
                    >
                      <input
                        type="radio"
                        name="evaluator"
                        value={evaluator.id}
                        checked={selectedEvaluator === evaluator.id}
                        onChange={(e) => setSelectedEvaluator(e.target.value)}
                        className="hidden"
                      />
                      <div className="flex items-start gap-3">
                        {/* Radio Indicator */}
                        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5 ${
                          selectedEvaluator === evaluator.id
                            ? "border-green-500 bg-green-500"
                            : "border-gray-300"
                        }`}>
                          {selectedEvaluator === evaluator.id && (
                            <div className="w-2 h-2 rounded-full bg-white"></div>
                          )}
                        </div>
                        
                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-semibold text-gray-900 text-sm">{evaluator.name}</h4>
                          </div>
                          {evaluator.description && (
                            <p className="text-xs text-gray-600 mb-2">{evaluator.description}</p>
                          )}
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs text-gray-500">
                              {evaluator.metric_ids.length} 个评估维度
                            </span>
                            <span className="text-gray-300">•</span>
                            <span className="text-xs text-gray-500">
                              使用 {evaluator.usage_count} 次
                            </span>
                          </div>
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500 text-sm">
                  <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <p>暂无评估器</p>
                  <p className="text-xs mt-1">请在"评估器"标签页创建评估器</p>
                </div>
              )}
            </div>
          </div>

          {/* Select Dataset */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-5 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-blue-600">2</span>
                </div>
                <h3 className="text-sm font-semibold text-gray-900">选择数据集</h3>
              </div>
            </div>
            <div className="p-5">
              {datasets.length > 0 ? (
                <select
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                  className={`w-full px-4 py-3 rounded-lg border-2 transition-all ${
                    datasetId
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 bg-white hover:border-blue-300"
                  } focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                >
                  <option value="">请选择数据集...</option>
                  {datasets.map((dataset) => (
                    <option key={dataset.id} value={dataset.id}>
                      {dataset.name} ({dataset.row_count} 行)
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-center py-8 text-gray-500 text-sm">
                  <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                  <p>暂无数据集</p>
                  <p className="text-xs mt-1">请在"数据集"页面创建数据集</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column - Preview & Action */}
        <div className="space-y-5">
          {/* Configuration Preview */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-5 py-4 border-b border-gray-200">
              <h3 className="text-sm font-semibold text-gray-900">评估配置预览</h3>
            </div>
            
            {selectedEvaluatorData ? (
              <div className="p-5 space-y-4">
                {/* Evaluator Info */}
                <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-4 border border-green-200">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-green-100 rounded-lg">
                      <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-gray-900 mb-1">{selectedEvaluatorData.name}</div>
                      {selectedEvaluatorData.description && (
                        <div className="text-xs text-gray-600">{selectedEvaluatorData.description}</div>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Metrics List */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-xs font-medium text-gray-700">评估维度</div>
                    <div className="text-xs text-gray-500">共 {selectedEvaluatorData.metric_ids.length} 个</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3 max-h-48 overflow-y-auto">
                    <div className="space-y-2">
                      {selectedEvaluatorData.metric_ids.map((metricId, idx) => {
                        const metricName = metrics.find(m => m.id === metricId)?.name;
                        return (
                          <div key={idx} className="flex items-center gap-2 text-sm bg-white rounded px-3 py-2">
                            <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                              <span className="text-xs font-semibold text-green-600">{idx + 1}</span>
                            </div>
                            <span className="text-gray-700 flex-1 truncate">{metricName || `${metricId.substring(0, 12)}...`}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Dataset Info */}
                <div className="border-t border-gray-200 pt-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs font-medium text-gray-700">数据集</div>
                    {selectedDatasetData && (
                      <div className="text-xs text-gray-500">{selectedDatasetData.row_count} 行数据</div>
                    )}
                  </div>
                  {datasetId ? (
                    <div className="flex items-center gap-2 bg-blue-50 rounded-lg px-3 py-2 border border-blue-200">
                      <svg className="w-4 h-4 text-blue-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                      </svg>
                      <span className="text-sm font-medium text-gray-900 flex-1 truncate">
                        {selectedDatasetData?.name || "未知"}
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-gray-400 bg-gray-50 rounded-lg px-3 py-2 border border-gray-200">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      <span>请选择数据集</span>
                    </div>
                  )}
                </div>

                {/* Action Button */}
                <div className="pt-2">
                  <button
                    onClick={handleRun}
                    disabled={!selectedEvaluator || !datasetId || isRunning}
                    className={`w-full py-3 px-4 rounded-lg font-medium text-sm transition-all ${
                      !selectedEvaluator || !datasetId || isRunning
                        ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                        : "bg-gradient-to-r from-green-600 to-green-700 text-white hover:from-green-700 hover:to-green-800 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                    }`}
                  >
                    {isRunning ? (
                      <div className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>任务提交中...</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center gap-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>开始评估</span>
                      </div>
                    )}
                  </button>
                  {(!selectedEvaluator || !datasetId) && (
                    <p className="mt-2 text-xs text-center text-gray-400">
                      请完成上方配置后开始评估
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div className="px-5 py-12 text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-gray-700 mb-1">请先选择评估器</p>
                <p className="text-xs text-gray-500">从左侧列表中选择一个评估器以查看配置预览</p>
              </div>
            )}
          </div>

          {/* Recent Tasks - Enhanced */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900">最近任务</h3>
              <button
                onClick={() => navigate("/tasks")}
                className="text-xs text-green-600 hover:text-green-700 font-medium flex items-center gap-1"
              >
                查看全部
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
            
            {recentTasks.length > 0 ? (
              <div className="divide-y divide-gray-100">
                {recentTasks.map((task) => {
                  const statusConfig = getStatusConfig(task.status);
                  const progress = Number(task.progress) || 0;
                  
                  return (
                    <div
                      key={task.id}
                      className="group px-5 py-4 hover:bg-gray-50 transition-colors cursor-pointer"
                      onClick={() => navigate(`/tasks/${task.id}`)}
                    >
                      <div className="flex items-start justify-between gap-3">
                        {/* Left: Task Info */}
                        <div className="flex-1 min-w-0">
                          {/* Header */}
                          <div className="flex items-center gap-2 mb-2">
                            <div className={`p-1.5 rounded-lg ${statusConfig.bgColor}`}>
                              <svg className={`w-4 h-4 ${statusConfig.color}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d={statusConfig.icon} />
                              </svg>
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-medium text-gray-500">
                                  {getTaskTypeLabel(task.task_type)}
                                </span>
                                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${statusConfig.bgColor} ${statusConfig.color}`}>
                                  {statusConfig.label}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Task ID */}
                          <div className="mb-2">
                            <span className="text-xs font-mono text-gray-400">ID: </span>
                            <span className="text-xs font-mono text-gray-600">{task.id.substring(0, 12)}...</span>
                          </div>

                          {/* Progress Bar (for running/pending) */}
                          {(task.status === "running" || task.status === "pending") && (
                            <div className="mb-2">
                              <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                                <span>进度</span>
                                <span className="font-medium">{progress.toFixed(1)}%</span>
                              </div>
                              <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className={`h-full ${statusConfig.progressColor} transition-all duration-300`}
                                  style={{ width: `${progress}%` }}
                                />
                              </div>
                            </div>
                          )}

                          {/* Error Message (for failed) */}
                          {task.status === "failed" && task.error && (
                            <div className="mb-2">
                              <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded truncate" title={task.error}>
                                {task.error}
                              </div>
                            </div>
                          )}

                          {/* Stats (for completed) */}
                          {task.status === "completed" && (
                            <div className="flex items-center gap-4 text-xs text-gray-600">
                              {task.total_tokens > 0 && (
                                <span className="flex items-center gap-1">
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                  </svg>
                                  {task.total_tokens.toLocaleString()} tokens
                                </span>
                              )}
                              {task.total_cost && Number(task.total_cost) > 0 && (
                                <span className="flex items-center gap-1">
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  ${Number(task.total_cost).toFixed(4)}
                                </span>
                              )}
                            </div>
                          )}

                          {/* Footer */}
                          <div className="mt-2 text-xs text-gray-500">
                            {formatTimeAgo(task.created_at)}
                          </div>
                        </div>

                        {/* Right: Action Buttons */}
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                          {task.status === "failed" && (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                if (!window.confirm("确定要重试这个任务吗？")) return;
                                setActioningTask(task.id);
                                try {
                                  await retryTask(task.id);
                                  fetchData();
                                } catch (err: any) {
                                  alert("重试失败：" + (err.response?.data?.detail || err.message));
                                } finally {
                                  setActioningTask(null);
                                }
                              }}
                              disabled={actioningTask === task.id}
                              className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-50 transition-colors"
                              title="重试"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                              </svg>
                            </button>
                          )}

                          {(task.status === "pending" || task.status === "running") && (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                if (!window.confirm("确定要取消这个任务吗？")) return;
                                setActioningTask(task.id);
                                try {
                                  await cancelTask(task.id);
                                  fetchData();
                                } catch (err: any) {
                                  alert("取消失败：" + (err.response?.data?.detail || err.message));
                                } finally {
                                  setActioningTask(null);
                                }
                              }}
                              disabled={actioningTask === task.id}
                              className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg disabled:opacity-50 transition-colors"
                              title="取消"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          )}

                          {task.status !== "running" && (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                if (!window.confirm("确定要删除这个任务吗？删除后无法恢复！")) return;
                                setActioningTask(task.id);
                                try {
                                  await deleteTask(task.id);
                                  fetchData();
                                } catch (err: any) {
                                  alert("删除失败：" + (err.response?.data?.detail || err.message));
                                } finally {
                                  setActioningTask(null);
                                }
                              }}
                              disabled={actioningTask === task.id}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50 transition-colors"
                              title="删除"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}

                          {/* View Details Button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/tasks/${task.id}`);
                            }}
                            className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                            title="查看详情"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="px-5 py-8 text-center">
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p className="text-sm text-gray-500">暂无任务记录</p>
                <p className="text-xs text-gray-400 mt-1">创建任务后，将显示在这里</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

