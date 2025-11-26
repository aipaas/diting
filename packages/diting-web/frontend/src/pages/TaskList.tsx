import { useState, useEffect } from "react";
import Pagination from "@/components/Pagination";
import { useNavigate } from "react-router-dom";
import {
  getTasks,
  getDatasets,
  getEvaluators,
  getMetrics,
  cancelTask,
  retryTask,
  deleteTask,
  createBatchEvaluationTask,
} from "@/api/client";
import type { 
  TaskResponse, 
  DatasetResponse, 
  EvaluatorResponse,
  MetricResponse,
  TaskStatus 
} from "@/types/api";
import { TaskType } from "@/types/api";

export default function TaskList() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [evaluators, setEvaluators] = useState<EvaluatorResponse[]>([]);
  const [metrics, setMetrics] = useState<MetricResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filterStatus, setFilterStatus] = useState<TaskStatus | "">("");
  const [searchQuery, setSearchQuery] = useState("");
  const [actioningTask, setActioningTask] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [taskName, setTaskName] = useState("");
  const [selectedEvaluator, setSelectedEvaluator] = useState("");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set());
  const [pageSize, setPageSize] = useState(10);

  // 设计系统样式类（与数据增强页面保持一致）
  const baseFieldClass = "w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300";
  const sectionCardClass = "rounded-2xl border border-slate-200/60 bg-white p-4 shadow-sm hover:shadow-md transition-shadow duration-200";
  const sectionTitleClass = "text-base font-semibold text-slate-900 mb-3 flex items-center gap-2";
  const labelClass = "mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5";

  useEffect(() => {
    fetchData();
  }, [page, filterStatus, searchQuery]);

  // Lazy load datasets, evaluators, and metrics only when create modal is opened
  // Removed initial loading to improve performance

  // Auto-refresh for running tasks with Page Visibility API optimization
  useEffect(() => {
    const hasRunningTasks = tasks.some(t => t.status === 'running' || t.status === 'pending');
    if (!hasRunningTasks) return;
    
    // Only refresh when page is visible
    const handleVisibilityChange = () => {
      if (!document.hidden && hasRunningTasks) {
        fetchData();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    const interval = setInterval(() => {
      // Only refresh if page is visible
      if (!document.hidden) {
        fetchData();
      }
    }, 5000); // Refresh every 5 seconds
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      clearInterval(interval);
    };
  }, [tasks]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError("");
      // Only fetch evaluation-related tasks (evaluation and batch_evaluation)
      // Note: We fetch batch_evaluation which covers both single and batch evaluations
      const data = await getTasks(
        page,
        pageSize,
        TaskType.BATCH_EVALUATION, // Only show batch_evaluation tasks (which includes single evaluations)
        filterStatus || undefined
      );
      setTasks(data.items);
      setTotal(data.total);
    } catch (err: any) {
      console.error("Failed to fetch tasks:", err);
      setError("加载任务列表失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchDatasets = async () => {
    try {
      const data = await getDatasets(1, 100);
      setDatasets(data.items);
    } catch (err: any) {
      console.error("Failed to fetch datasets:", err);
    }
  };

  const fetchEvaluators = async () => {
    try {
      const data = await getEvaluators(1, 100);
      setEvaluators(data.items);
    } catch (err: any) {
      console.error("Failed to fetch evaluators:", err);
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

  const handleCreateTask = async () => {
    if (!selectedEvaluator || !selectedDataset) return;

    setIsCreating(true);
    try {
      await createBatchEvaluationTask({
        name: taskName || undefined,  // 如果为空，后端会自动生成
        dataset_id: selectedDataset,
        evaluator_id: selectedEvaluator,
      });
      setShowCreateModal(false);
      setTaskName("");
      setSelectedEvaluator("");
      setSelectedDataset("");
      // 创建成功后统一跳转到任务列表
      navigate("/evaluation/tasks");
      // 触发一次刷新（在任务列表页生效）
      fetchData();
      alert("评估任务已创建！");
    } catch (err: any) {
      alert("创建任务失败：" + (err.response?.data?.detail || err.message));
    } finally {
      setIsCreating(false);
    }
  };

  const handleAction = async (
    action: "cancel" | "retry" | "delete",
    task: TaskResponse
  ) => {
    const confirmMsg =
      action === "delete"
        ? "确定要删除这个任务吗？删除后无法恢复！"
        : action === "cancel"
        ? "确定要取消这个任务吗？"
        : "确定要重试这个任务吗？";

    if (!window.confirm(confirmMsg)) return;

    setActioningTask(task.id);
    try {
      if (action === "cancel") await cancelTask(task.id);
      else if (action === "retry") await retryTask(task.id);
      else if (action === "delete") await deleteTask(task.id);

      fetchData();
      const successMsg =
        action === "delete"
          ? "任务已删除"
          : action === "cancel"
          ? "任务已取消"
          : "任务已重新提交";
      alert(successMsg);
    } catch (err: any) {
      alert(
        `${action === "delete" ? "删除" : action === "cancel" ? "取消" : "重试"}失败：` +
          (err.response?.data?.detail || err.message)
      );
    } finally {
      setActioningTask(null);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedTasks.size === 0) return;
    
    if (!window.confirm(`确定要删除选中的 ${selectedTasks.size} 个任务吗？删除后无法恢复！`)) return;

    const deletePromises = Array.from(selectedTasks).map(taskId => deleteTask(taskId));
    
    try {
      await Promise.all(deletePromises);
      setSelectedTasks(new Set());
      fetchData();
      alert(`成功删除 ${selectedTasks.size} 个任务`);
    } catch (err: any) {
      alert("批量删除失败：" + (err.response?.data?.detail || err.message));
    }
  };

  const toggleTaskSelection = (taskId: string) => {
    const newSelected = new Set(selectedTasks);
    if (newSelected.has(taskId)) {
      newSelected.delete(taskId);
    } else {
      newSelected.add(taskId);
    }
    setSelectedTasks(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedTasks.size === filteredTasks.length) {
      setSelectedTasks(new Set());
    } else {
      setSelectedTasks(new Set(filteredTasks.map(t => t.id)));
    }
  };

  // Lazy load data when opening create modal
  const handleOpenCreateModal = () => {
    setShowCreateModal(true);
    // Load data only when modal is opened
    if (datasets.length === 0) fetchDatasets();
    if (evaluators.length === 0) fetchEvaluators();
    if (metrics.length === 0) fetchMetrics();
  };

  const getStatusConfig = (status: string) => {
    const configs = {
      completed: {
        label: "已完成",
        color: "text-green-700",
        bgColor: "bg-green-100",
        dotColor: "bg-green-500",
      },
      running: {
        label: "运行中",
        color: "text-blue-700",
        bgColor: "bg-blue-100",
        dotColor: "bg-blue-500",
      },
      failed: {
        label: "失败",
        color: "text-red-700",
        bgColor: "bg-red-100",
        dotColor: "bg-red-500",
      },
      pending: {
        label: "等待中",
        color: "text-gray-700",
        bgColor: "bg-gray-100",
        dotColor: "bg-gray-400",
      },
      cancelled: {
        label: "已取消",
        color: "text-gray-700",
        bgColor: "bg-gray-100",
        dotColor: "bg-gray-400",
      },
    };
    return configs[status as keyof typeof configs] || configs.pending;
  };


  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDuration = (start: string | null, end: string | null) => {
    if (!start || !end) return "-";
    const duration = new Date(end).getTime() - new Date(start).getTime();
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  if (loading && tasks.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <svg
            className="animate-spin h-10 w-10 text-green-600"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          <span className="text-gray-600">加载中...</span>
        </div>
      </div>
    );
  }

  // Filter tasks by search query
  const filteredTasks = searchQuery
    ? tasks.filter(task => 
        task.name && task.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : tasks;

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg">
          {error}
        </div>
      )}

      {/* Tasks Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* Header - Always visible */}
        <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
              <div className="flex items-center justify-between gap-4">
                {/* Left: Title and Search */}
                <div className="flex items-center gap-6">
                  <h2 className="text-lg font-bold text-gray-900">
                    任务列表
                  </h2>

                  {/* Search Box */}
                  <div className="relative w-80">
                    <input
                      type="text"
                      placeholder="搜索任务名称..."
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setPage(1);
                      }}
                      className="w-full pl-10 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all"
                    />
                    <svg className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    {searchQuery && (
                      <button
                        onClick={() => {
                          setSearchQuery("");
                          setPage(1);
                        }}
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
                  {/* Status Filter */}
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium text-gray-600 whitespace-nowrap">状态筛选</label>
                    <select
                      value={filterStatus}
                      onChange={(e) => {
                        setFilterStatus(e.target.value as TaskStatus | "");
                        setPage(1);
                      }}
                      className="pl-3 pr-8 py-2 text-sm border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 cursor-pointer transition-all"
                    >
                      <option value="">全部</option>
                      <option value="pending">等待中</option>
                      <option value="running">运行中</option>
                      <option value="completed">已完成</option>
                      <option value="failed">失败</option>
                      <option value="cancelled">已取消</option>
                    </select>
                  </div>

                  {/* Batch Delete Button */}
                  {selectedTasks.size > 0 && (
                    <button
                      onClick={handleBatchDelete}
                      className="px-3 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2 shadow-sm hover:shadow"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      删除 ({selectedTasks.size})
                    </button>
                  )}

                  {/* New Task Button */}
                  <button
                    onClick={handleOpenCreateModal}
                    className="px-4 py-2 bg-gradient-to-r from-brand-500 to-violet-500 text-white text-sm font-medium rounded-lg hover:from-brand-600 hover:to-violet-600 transition-all flex items-center gap-2 shadow-sm hover:shadow whitespace-nowrap"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    新建任务
                  </button>
                </div>
              </div>
        </div>

        {/* Content - Show table or empty state */}
        {tasks.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full table-fixed">
                <colgroup>
                  <col className="w-12" />
                  <col className="w-[30%]" />
                  <col className="w-[15%]" />
                  <col className="w-[15%]" />
                  <col className="w-[10%]" />
                  <col className="w-[12%]" />
                  <col className="w-[18%]" />
                </colgroup>
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-3 py-2.5 text-left">
                      <input
                        type="checkbox"
                        checked={filteredTasks.length > 0 && selectedTasks.size === filteredTasks.length}
                        onChange={toggleSelectAll}
                        className="w-4 h-4 text-brand-600 border-gray-300 rounded focus:ring-brand-500 cursor-pointer"
                      />
                    </th>
                    <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">
                      评估任务
                    </th>
                    <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">
                      状态
                    </th>
                    <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">
                      创建时间
                    </th>
                    <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">
                      耗时
                    </th>
                    <th className="px-3 py-2.5 text-right text-xs font-medium text-gray-500 uppercase">
                      Token/成本
                    </th>
                    <th className="px-3 py-2.5 text-right text-xs font-medium text-gray-500 uppercase">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredTasks.map((task) => {
                    const statusConfig = getStatusConfig(task.status);
                    const progress = Number(task.progress) || 0;

                    return (
                      <tr
                        key={task.id}
                        className="hover:bg-brand-50 transition-colors"
                      >
                        {/* Checkbox */}
                        <td 
                          className="px-3 py-2.5"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={selectedTasks.has(task.id)}
                            onChange={() => toggleTaskSelection(task.id)}
                            className="w-4 h-4 text-brand-600 border-gray-300 rounded focus:ring-brand-500 cursor-pointer"
                          />
                        </td>

                        {/* Task */}
                        <td 
                          className="px-3 py-2.5 cursor-pointer"
                          onClick={() => navigate(`/tasks/${task.id}`)}
                        >
                          <div className="text-sm font-medium text-gray-900 truncate">
                            {task.name || `任务 ${task.id.substring(0, 8)}`}
                          </div>
                        </td>

                        {/* Status */}
                        <td 
                          className="px-3 py-2.5 cursor-pointer"
                          onClick={() => navigate(`/tasks/${task.id}`)}
                        >
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-2">
                              <div
                                className={`w-2 h-2 rounded-full ${statusConfig.dotColor}`}
                              ></div>
                              <span
                                className={`text-xs font-semibold ${statusConfig.color}`}
                              >
                                {statusConfig.label}
                              </span>
                            </div>
                            {(task.status === "running" || task.status === "pending") && (
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden max-w-[100px]">
                                  <div
                                    className={`h-full ${statusConfig.dotColor.replace(
                                      "bg-",
                                      "bg-"
                                    )} transition-all`}
                                    style={{ width: `${progress}%` }}
                                  />
                                </div>
                                <span className="text-xs text-gray-500">
                                  {progress.toFixed(0)}%
                                </span>
                              </div>
                            )}
                            {task.status === "failed" && task.error && (
                              <div
                                className="text-xs text-red-600 truncate max-w-xs"
                                title={task.error}
                              >
                                {task.error}
                              </div>
                            )}
                          </div>
                        </td>

                        {/* Created At */}
                        <td 
                          className="px-3 py-2.5 cursor-pointer"
                          onClick={() => navigate(`/tasks/${task.id}`)}
                        >
                          <div className="text-sm text-gray-700">
                            {formatDate(task.created_at)}
                          </div>
                        </td>

                        {/* Duration */}
                        <td 
                          className="px-3 py-2.5 cursor-pointer"
                          onClick={() => navigate(`/tasks/${task.id}`)}
                        >
                          <div className="text-sm text-gray-700">
                            {formatDuration(task.started_at, task.completed_at)}
                          </div>
                        </td>

                        {/* Tokens/Cost */}
                        <td 
                          className="px-3 py-2.5 text-right cursor-pointer"
                          onClick={() => navigate(`/tasks/${task.id}`)}
                        >
                          <div className="text-sm text-gray-700">
                            {task.total_tokens > 0
                              ? task.total_tokens.toLocaleString()
                              : "-"}
                          </div>
                          {task.total_cost && Number(task.total_cost) > 0 && (
                            <div className="text-xs text-gray-500">
                              ${Number(task.total_cost).toFixed(4)}
                            </div>
                          )}
                        </td>

                        {/* Actions */}
                        <td
                          className="px-3 py-2.5 text-right"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="inline-flex items-center justify-end gap-1">
                            {/* View Details - Always visible */}
                            <button
                              onClick={() => navigate(`/tasks/${task.id}`)}
                              className="p-1.5 text-gray-600 hover:bg-gray-100 rounded transition-colors"
                              title="查看详情"
                            >
                              <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                />
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                                />
                              </svg>
                            </button>

                            {/* Retry / Cancel - Fixed width placeholder */}
                            {task.status === "failed" ? (
                              <button
                                onClick={() => handleAction("retry", task)}
                                disabled={actioningTask === task.id}
                                className="p-1.5 text-blue-600 hover:bg-blue-50 rounded disabled:opacity-50 transition-colors"
                                title="重试"
                              >
                                <svg
                                  className="w-4 h-4"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth="2"
                                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                  />
                                </svg>
                              </button>
                            ) : (task.status === "pending" || task.status === "running") ? (
                              <button
                                onClick={() => handleAction("cancel", task)}
                                disabled={actioningTask === task.id}
                                className="p-1.5 text-yellow-600 hover:bg-yellow-50 rounded disabled:opacity-50 transition-colors"
                                title="取消"
                              >
                                <svg
                                  className="w-4 h-4"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth="2"
                                    d="M6 18L18 6M6 6l12 12"
                                  />
                                </svg>
                              </button>
                            ) : (
                              <div className="w-[28px]"></div>
                            )}

                            {/* Delete - Fixed width placeholder */}
                            {task.status !== "running" ? (
                              <button
                                onClick={() => handleAction("delete", task)}
                                disabled={actioningTask === task.id}
                                className="p-1.5 text-red-600 hover:bg-red-50 rounded disabled:opacity-50 transition-colors"
                                title="删除"
                              >
                                <svg
                                  className="w-4 h-4"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth="2"
                                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                  />
                                </svg>
                              </button>
                            ) : (
                              <div className="w-[28px]"></div>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Unified Pagination */}
            {total > 0 && (
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
            )}
          </>
        ) : (
          <div className="py-16">
            {filterStatus ? (
              // 筛选结果为空
              <div className="text-center">
                <svg
                  className="w-16 h-16 mx-auto text-gray-300 mb-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                <p className="text-sm font-medium text-gray-700 mb-2">没有符合筛选条件的任务</p>
                <p className="text-sm text-gray-500 mb-4">请尝试调整筛选条件</p>
              </div>
            ) : (
              // 初始空状态 - 显示引导信息
              <div className="max-w-2xl mx-auto">
                <div className="text-center mb-8">
                  <svg
                    className="w-16 h-16 mx-auto text-gray-300 mb-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                  <p className="text-lg font-medium text-gray-900 mb-2">暂无任务</p>
                  <p className="text-sm text-gray-500 mb-6">
                    还没有创建任何任务，开始创建您的第一个评估任务吧
                  </p>
                  <button
                    onClick={handleOpenCreateModal}
                    className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors inline-flex items-center gap-2 font-medium shadow-sm hover:shadow-md"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    创建第一个任务
                  </button>
                </div>

                {/* 快速开始指南 */}
                <div className="mt-8 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100 p-6">
                  <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    快速开始
                  </h3>
                  <div className="space-y-3 text-sm text-gray-700">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-semibold mt-0.5">
                        1
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">准备数据集</p>
                        <p className="text-gray-600 mt-0.5">在"数据集"页面创建或导入您的测试数据集</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-semibold mt-0.5">
                        2
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">创建评估器</p>
                        <p className="text-gray-600 mt-0.5">在"自评估器"页面配置评估维度和模型</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-semibold mt-0.5">
                        3
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">创建评估任务</p>
                        <p className="text-gray-600 mt-0.5">选择数据集和评估器，开始批量评估</p>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-blue-200">
                    <button
                      onClick={() => navigate("/datasets")}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
                    >
                      前往数据集页面
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create Task Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-6 transition-opacity duration-200">
          <div className="relative max-w-2xl w-full transform transition-all duration-200 scale-100">
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
              {/* Modal Header */}
              <div className="sticky top-0 z-10 border-b border-slate-200/80 px-6 py-4 bg-white flex items-center justify-between shadow-sm">
                <div className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                  <svg className="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                  </svg>
                  新建评估任务
                </div>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setTaskName("");
                    setSelectedEvaluator("");
                    setSelectedDataset("");
                  }}
                  aria-label="关闭"
                  className="p-2 rounded-xl text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-all duration-200"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 space-y-4 overflow-y-auto flex-1">
                {/* Task Name */}
                <div className={sectionCardClass}>
                  <h2 className={sectionTitleClass}>
                    <svg className="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    基本信息
                  </h2>
                  <div>
                    <label className={labelClass}>
                      <span>任务名称</span>
                      <span className="text-slate-400 font-normal">(可选)</span>
                    </label>
                    <input
                      type="text"
                      value={taskName}
                      onChange={(e) => setTaskName(e.target.value)}
                      placeholder="例如：批量评估 - 知识库问答"
                      className={baseFieldClass}
                      maxLength={200}
                    />
                    <p className="mt-1.5 text-xs text-slate-500 leading-relaxed">
                      为任务设置一个便于识别的名称，留空则使用任务ID
                    </p>
                  </div>
                </div>

                {/* Step 1: Select Evaluator */}
                <div className={sectionCardClass}>
                  <h2 className={sectionTitleClass}>
                    <svg className="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                    </svg>
                    选择评估器
                  </h2>

                  {evaluators.length > 0 ? (
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {evaluators.map((evaluator) => (
                        <label
                          key={evaluator.id}
                          className={`block p-3 rounded-xl border-2 cursor-pointer transition-all ${
                            selectedEvaluator === evaluator.id
                              ? "border-brand-500 bg-brand-50"
                              : "border-slate-200 hover:border-brand-500/60"
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
                            <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5 ${
                              selectedEvaluator === evaluator.id
                                ? "border-brand-500 bg-brand-500"
                                : "border-slate-300"
                            }`}>
                              {selectedEvaluator === evaluator.id && (
                                <div className="w-1.5 h-1.5 rounded-full bg-white"></div>
                              )}
                            </div>
                            <div className="flex-1">
                              <div className="text-sm font-medium text-slate-900">{evaluator.name}</div>
                              {evaluator.description && (
                                <div className="text-xs text-slate-600 mt-0.5">{evaluator.description}</div>
                              )}
                              <div className="text-xs text-slate-500 mt-1">
                                {evaluator.metric_ids.length} 个评估维度
                              </div>
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-slate-500 text-sm bg-slate-50 rounded-xl">
                      暂无评估器，请先在"评估器"标签页创建评估器
                    </div>
                  )}
                </div>

                {/* Step 2: Select Dataset */}
                <div className={sectionCardClass}>
                  <h2 className={sectionTitleClass}>
                    <svg className="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    选择数据集
                  </h2>

                  {datasets.length > 0 ? (
                    <select
                      value={selectedDataset}
                      onChange={(e) => setSelectedDataset(e.target.value)}
                      className={baseFieldClass}
                    >
                      <option value="">请选择数据集...</option>
                      {datasets.map((dataset) => (
                        <option key={dataset.id} value={dataset.id}>
                          {dataset.name} ({dataset.row_count} 行)
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="text-center py-6 text-slate-500 text-sm bg-slate-50 rounded-xl">
                      暂无数据集，请先在"数据集"页面创建数据集
                    </div>
                  )}
                </div>

                {/* Preview */}
                {selectedEvaluator && selectedDataset && (() => {
                  const selectedEvaluatorData = evaluators.find(e => e.id === selectedEvaluator);
                  return selectedEvaluatorData ? (
                    <div className={sectionCardClass}>
                      <h2 className={sectionTitleClass}>
                        <svg className="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        配置预览
                      </h2>
                      <div className="bg-slate-50 rounded-xl p-4 space-y-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-600">评估器</span>
                          <span className="font-medium text-slate-900">{selectedEvaluatorData.name}</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-600">评估维度</span>
                          <span className="font-medium text-slate-900">{selectedEvaluatorData.metric_ids.length} 个</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-600">数据集</span>
                          <span className="font-medium text-slate-900">
                            {datasets.find(d => d.id === selectedDataset)?.name}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-600">数据行数</span>
                          <span className="font-medium text-slate-900">
                            {datasets.find(d => d.id === selectedDataset)?.row_count} 行
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : null;
                })()}
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-4 border-t border-slate-200/80 flex items-center justify-end gap-3 bg-white">
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setTaskName("");
                    setSelectedEvaluator("");
                    setSelectedDataset("");
                  }}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleCreateTask}
                  disabled={!selectedEvaluator || !selectedDataset || isCreating}
                  className={`px-6 py-2 rounded-lg font-medium transition-colors disabled:bg-slate-300 disabled:cursor-not-allowed flex items-center gap-2 ${
                    !selectedEvaluator || !selectedDataset || isCreating
                      ? "bg-slate-300 text-slate-500"
                      : "bg-brand-600 hover:bg-brand-700 text-white shadow-sm hover:shadow-md"
                  }`}
                >
                  {isCreating ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>创建中...</span>
                    </>
                  ) : (
                    "创建任务"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
