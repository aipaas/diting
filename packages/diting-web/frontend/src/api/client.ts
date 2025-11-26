import axios, { AxiosError } from "axios";
import type {
  APIResponse,
  PaginatedResponse,
  LoginRequest,
  TokenResponse,
  UserResponse,
  UserCreate,
  UserUpdate,
  HealthzResponse,
  DatasetResponse,
  DatasetPreviewResponse,
  DatasetDataUpdate,
  AnnotationColumnCreate,
  AnnotationColumnUpdate,
  AnnotationColumnDelete,
  MetricResponse,
  MetricCreate,
  MetricUpdate,
  EvalMetricTypeEnum,
  EvaluatorResponse,
  EvaluatorCreate,
  EvaluatorUpdate,
  TaskResponse,
  TaskCreateResponse,
  CreateEvaluationTaskRequest,
  CreateSynthesisTaskRequest,
  CreateNegativeMiningTaskRequest,
  CreateBatchEvaluationTaskRequest,
  DashboardStatisticsResponse,
  TaskType,
  TaskStatus,
  ModelResponse,
  ModelCreate,
  ModelUpdate,
  ModelType,
  SynthesisResultResponse,
  // Prompts
  PromptResponse,
  PromptCreate,
  PromptUpdate,
  PromptStatisticsResponse,
  PromptCategoryEnum,
} from "@/types/api";

export type { UserResponse };

// Create axios instance
const api = axios.create({
  baseURL: "/api/v1",
  timeout: 600_000,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Add auth token (try both keys for compatibility)
    const token = localStorage.getItem("token") || localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Try to refresh token
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const { data } = await axios.post("/api/v1/auth/refresh", {}, {
            headers: { Authorization: `Bearer ${refreshToken}` },
          });
          const newAccessToken = data.data.access_token;
          localStorage.setItem("access_token", newAccessToken);
          
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed - redirect to login
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("isAuthenticated");
          window.location.href = "/login";
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token - redirect to login
        localStorage.removeItem("access_token");
        localStorage.removeItem("isAuthenticated");
        window.location.href = "/login";
      }
    }
    
    return Promise.reject(error);
  }
);

// ============= Auth APIs (v3.0 Simplified) =============

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  const { data } = await api.post<APIResponse<TokenResponse>>("/auth/login", payload);
  return data.data;
}

export async function refreshToken(): Promise<{ access_token: string; token_type: string; expires_in: number }> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }
  
  const { data } = await axios.post("/api/v1/auth/refresh", {}, {
    headers: { Authorization: `Bearer ${refreshToken}` },
  });
  return data.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const { data } = await api.get<APIResponse<UserResponse>>("/auth/me");
  return data.data;
}

// ============= User Management APIs (Admin Only) =============

export async function getUsers(params?: {
  page?: number;
  page_size?: number;
  is_admin?: boolean;
  is_active?: boolean;
  search?: string;
}): Promise<PaginatedResponse<UserResponse>> {
  const { data } = await api.get<APIResponse<PaginatedResponse<UserResponse>>>(
    "/users",
    { params }
  );
  return data.data;
}

export async function getUser(userId: string): Promise<UserResponse> {
  const { data } = await api.get<APIResponse<UserResponse>>(`/users/${userId}`);
  return data.data;
}

export async function createUser(payload: UserCreate): Promise<UserResponse> {
  const { data } = await api.post<APIResponse<UserResponse>>("/users", payload);
  return data.data;
}

export async function updateUser(
  userId: string,
  payload: UserUpdate
): Promise<UserResponse> {
  const { data } = await api.put<APIResponse<UserResponse>>(
    `/users/${userId}`,
    payload
  );
  return data.data;
}

export async function deleteUser(userId: string): Promise<void> {
  await api.delete(`/users/${userId}`);
}

export async function resetUserPassword(
  userId: string,
  new_password: string
): Promise<void> {
  await api.post(`/users/${userId}/reset-password`, null, {
    params: { new_password }
  });
}

// ============= Health Check APIs =============
export async function getHealthz(): Promise<HealthzResponse> {
  const { data } = await api.get<HealthzResponse>("/healthz");
  return data;
}

// ============= Dataset APIs =============
export async function uploadDataset(
  formData: FormData
): Promise<DatasetResponse> {
  const { data } = await api.post<APIResponse<DatasetResponse>>("/datasets", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data.data;
}

export async function getDatasets(
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<DatasetResponse>> {
  const { data } = await api.get<APIResponse<PaginatedResponse<DatasetResponse>>>(
    "/datasets",
    {
      params: { page, page_size: pageSize },
    }
  );
  return data.data;
}

export async function getDataset(datasetId: string): Promise<DatasetResponse> {
  const { data } = await api.get<APIResponse<DatasetResponse>>(
    `/datasets/${datasetId}`
  );
  return data.data;
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await api.delete(`/datasets/${datasetId}`);
}

export async function getDatasetDownloadUrl(
  datasetId: string
): Promise<string> {
  const { data } = await api.get<APIResponse<{ download_url: string }>>(
    `/datasets/${datasetId}/download/original`
  );
  return data.data.download_url;
}

export async function exportDataset(datasetId: string, format: 'csv' | 'jsonl' = 'csv'): Promise<void> {
  const response = await api.get(`/datasets/${datasetId}/export?format=${format}`, {
    responseType: "blob",
  });
  
  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers["content-disposition"];
  let filename = `dataset_export.${format}`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/);
    if (match) {
      filename = match[1];
    }
  }
  
  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function previewDataset(
  datasetId: string,
  page: number = 1,
  pageSize: number = 20,
  search?: string
): Promise<DatasetPreviewResponse> {
  const params: Record<string, any> = {
    page,
    page_size: pageSize,
  };
  if (search) {
    params.search = search;
  }
  const { data } = await api.get<APIResponse<DatasetPreviewResponse>>(
    `/datasets/${datasetId}/preview`,
    { params }
  );
  return data.data;
}

export async function updateDatasetData(
  datasetId: string,
  payload: DatasetDataUpdate
): Promise<DatasetResponse> {
  const { data } = await api.put<APIResponse<DatasetResponse>>(
    `/datasets/${datasetId}/data`,
    payload
  );
  return data.data;
}

export async function updateDatasetRow(
  datasetId: string,
  rowIndex: number,
  rowData: Record<string, any>
): Promise<DatasetResponse> {
  const { data } = await api.put<APIResponse<DatasetResponse>>(
    `/datasets/${datasetId}/data/row`,
    { row_index: rowIndex, data: rowData }
  );
  return data.data;
}

export async function deleteDatasetRow(
  datasetId: string,
  rowIndex: number
): Promise<DatasetResponse> {
  const { data } = await api.delete<APIResponse<DatasetResponse>>(
    `/datasets/${datasetId}/data/row`,
    { data: { row_index: rowIndex } }
  );
  return data.data;
}

export async function addAnnotationColumn(
  datasetId: string,
  payload: AnnotationColumnCreate
): Promise<DatasetResponse> {
  const { data } = await api.post<APIResponse<DatasetResponse>>(
    `/datasets/${datasetId}/annotations/columns`,
    payload
  );
  return data.data;
}

export async function updateAnnotationColumn(
  datasetId: string,
  payload: AnnotationColumnUpdate
): Promise<DatasetResponse> {
  const { data } = await api.put<APIResponse<DatasetResponse>>(
    `/datasets/${datasetId}/annotations/columns`,
    payload
  );
  return data.data;
}

export async function deleteAnnotationColumn(
  datasetId: string,
  payload: AnnotationColumnDelete
): Promise<DatasetResponse> {
  const { data } = await api.delete<APIResponse<DatasetResponse>>(
    `/datasets/${datasetId}/annotations/columns`,
    { data: payload }
  );
  return data.data;
}

// ============= Metric APIs =============
export async function createMetric(payload: MetricCreate): Promise<MetricResponse> {
  const { data } = await api.post<APIResponse<MetricResponse>>("/metrics", payload);
  return data.data;
}

export async function getMetrics(
  page: number = 1,
  pageSize: number = 20,
  metricType?: EvalMetricTypeEnum
): Promise<PaginatedResponse<MetricResponse>> {
  const { data } = await api.get<APIResponse<PaginatedResponse<MetricResponse>>>(
    "/metrics",
    {
      params: { page, page_size: pageSize, metric_type: metricType },
    }
  );
  return data.data;
}

export async function getMetric(metricId: string): Promise<MetricResponse> {
  const { data } = await api.get<APIResponse<MetricResponse>>(`/metrics/${metricId}`);
  return data.data;
}

export async function updateMetric(
  metricId: string,
  payload: MetricUpdate
): Promise<MetricResponse> {
  const { data } = await api.put<APIResponse<MetricResponse>>(
    `/metrics/${metricId}`,
    payload
  );
  return data.data;
}

export async function deleteMetric(metricId: string): Promise<void> {
  await api.delete(`/metrics/${metricId}`);
}

// ============= Evaluator APIs =============
export async function createEvaluator(
  payload: EvaluatorCreate
): Promise<EvaluatorResponse> {
  const { data } = await api.post<APIResponse<EvaluatorResponse>>(
    "/evaluators",
    payload
  );
  return data.data;
}

export async function getEvaluators(
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<EvaluatorResponse>> {
  const { data } = await api.get<APIResponse<PaginatedResponse<EvaluatorResponse>>>(
    "/evaluators",
    {
      params: { page, page_size: pageSize },
    }
  );
  return data.data;
}

export async function getEvaluator(evaluatorId: string): Promise<EvaluatorResponse> {
  const { data } = await api.get<APIResponse<EvaluatorResponse>>(
    `/evaluators/${evaluatorId}`
  );
  return data.data;
}

export async function updateEvaluator(
  evaluatorId: string,
  payload: EvaluatorUpdate
): Promise<EvaluatorResponse> {
  const { data } = await api.put<APIResponse<EvaluatorResponse>>(
    `/evaluators/${evaluatorId}`,
    payload
  );
  return data.data;
}

export async function deleteEvaluator(evaluatorId: string): Promise<void> {
  await api.delete(`/evaluators/${evaluatorId}`);
}

// ============= Task APIs =============
export async function createEvaluationTask(
  payload: CreateEvaluationTaskRequest
): Promise<TaskCreateResponse> {
  const { data } = await api.post<APIResponse<TaskCreateResponse>>(
    "/tasks/evaluations",
    payload
  );
  return data.data;
}

export async function createSynthesisTask(
  payload: CreateSynthesisTaskRequest
): Promise<TaskCreateResponse> {
  const { data } = await api.post<APIResponse<TaskCreateResponse>>(
    "/tasks/synthesis",
    payload
  );
  return data.data;
}

export async function createNegativeMiningTask(
  payload: CreateNegativeMiningTaskRequest
): Promise<TaskCreateResponse> {
  const { data } = await api.post<APIResponse<TaskCreateResponse>>(
    "/tasks/negative-mining",
    payload
  );
  return data.data;
}

export async function createBatchEvaluationTask(
  payload: CreateBatchEvaluationTaskRequest
): Promise<TaskCreateResponse> {
  const { data } = await api.post<APIResponse<TaskCreateResponse>>(
    "/tasks/batch-evaluations",
    payload
  );
  return data.data;
}

export async function getTask(taskId: string): Promise<TaskResponse> {
  const { data } = await api.get<APIResponse<TaskResponse>>(`/tasks/${taskId}`);
  return data.data;
}

export async function getTasks(
  page: number = 1,
  pageSize: number = 20,
  taskType?: TaskType,
  status?: TaskStatus
): Promise<PaginatedResponse<TaskResponse>> {
  const { data } = await api.get<APIResponse<PaginatedResponse<TaskResponse>>>(
    "/tasks",
    {
      params: { 
        page, 
        page_size: pageSize, 
        task_type: taskType, 
        status_param: status 
      },
    }
  );
  return data.data;
}

export async function cancelTask(taskId: string): Promise<TaskResponse> {
  const { data} = await api.post<APIResponse<TaskResponse>>(
    `/tasks/${taskId}/cancel`
  );
  return data.data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await api.delete(`/tasks/${taskId}`);
}

export async function retryTask(taskId: string): Promise<TaskResponse> {
  const { data } = await api.post<APIResponse<TaskResponse>>(
    `/tasks/${taskId}/retry`
  );
  return data.data;
}

// ============= Evaluation Results APIs =============
export async function getEvaluationResults(
  taskId: string,
  page: number = 1,
  pageSize: number = 100,
  pivot?: boolean
): Promise<PaginatedResponse<any>> {
  const { data } = await api.get<APIResponse<PaginatedResponse<any>>>(
    `/tasks/${taskId}/evaluation-results`,
    {
      params: { page, page_size: pageSize, ...(typeof pivot === "boolean" ? { pivot } : {}) },
    }
  );
  return data.data;
}

export async function getEvaluationSummary(taskId: string): Promise<any> {
  const { data } = await api.get<APIResponse<any>>(
    `/tasks/${taskId}/evaluation-results/summary`
  );
  return data.data;
}

export async function exportEvaluationResults(
  taskId: string,
  format: "csv" | "excel" | "jsonl" = "csv"
): Promise<void> {
  const response = await api.get(
    `/tasks/${taskId}/evaluation-results/export?format=${format}`,
    {
      responseType: "blob",
    }
  );

  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers["content-disposition"];
  const extension = format === "excel" ? "xlsx" : format;
  let filename = `evaluation_results_${taskId}.${extension}`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/);
    if (match) {
      filename = match[1];
    }
  }

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

// ============= Synthesis Results APIs =============
export async function getSynthesisResults(taskId: string): Promise<SynthesisResultResponse[]> {
  const { data } = await api.get<APIResponse<SynthesisResultResponse[]>>(
    `/tasks/${taskId}/synthesis-results`
  );
  return data.data;
}

export async function exportSynthesisResults(taskId: string, format: "csv" | "jsonl" = "csv"): Promise<void> {
  const response = await api.get(`/tasks/${taskId}/synthesis-results/export?format=${format}`, {
    responseType: "blob",
  });
  
  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers["content-disposition"];
  let filename = `synthesis_results_${taskId}.${format}`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/);
    if (match) {
      filename = match[1];
    }
  }
  
  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function createDatasetFromSynthesisResults(
  taskId: string,
  name: string,
  description?: string
): Promise<DatasetResponse> {
  const { data } = await api.post<APIResponse<DatasetResponse>>(
    `/tasks/${taskId}/synthesis-results/create-dataset`,
    { name, description }
  );
  return data.data;
}

// ============= Negative Mining Results APIs =============
export async function getNegativeMiningResults(taskId: string): Promise<any[]> {
  const { data } = await api.get<APIResponse<any[]>>(
    `/tasks/${taskId}/negative-mining-results`
  );
  return data.data;
}

export async function exportNegativeMiningResults(taskId: string, format: "json" | "jsonl" = "json"): Promise<void> {
  const response = await api.get(`/tasks/${taskId}/negative-mining-results/export?format=${format}`, {
    responseType: "blob",
  });
  
  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers["content-disposition"];
  let filename = `negative_mining_results_${taskId}.${format}`;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/);
    if (match) {
      filename = match[1];
    }
  }
  
  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function createDatasetFromNegativeMiningResults(
  taskId: string,
  name: string,
  description?: string
): Promise<DatasetResponse> {
  const { data } = await api.post<APIResponse<DatasetResponse>>(
    `/tasks/${taskId}/negative-mining-results/create-dataset`,
    { name, description }
  );
  return data.data;
}

// ============= Statistics APIs =============
export async function getDashboardStatistics(): Promise<DashboardStatisticsResponse> {
  const { data } = await api.get<APIResponse<DashboardStatisticsResponse>>(
    "/statistics/dashboard"
  );
  return data.data;
}

// ============= Model Management APIs =============
export async function createModel(payload: ModelCreate): Promise<ModelResponse> {
  const { data } = await api.post<APIResponse<ModelResponse>>("/models", payload);
  return data.data;
}

export async function getModels(
  page: number = 1,
  pageSize: number = 20,
  modelType?: ModelType
): Promise<PaginatedResponse<ModelResponse>> {
  const { data } = await api.get<APIResponse<PaginatedResponse<ModelResponse>>>(
    "/models",
    {
      params: { page, page_size: pageSize, model_type: modelType },
    }
  );
  return data.data;
}

export async function getModel(modelId: string): Promise<ModelResponse> {
  const { data } = await api.get<APIResponse<ModelResponse>>(`/models/${modelId}`);
  return data.data;
}

export async function updateModel(
  modelId: string,
  payload: ModelUpdate
): Promise<ModelResponse> {
  const { data } = await api.put<APIResponse<ModelResponse>>(
    `/models/${modelId}`,
    payload
  );
  return data.data;
}

export async function deleteModel(modelId: string): Promise<void> {
  await api.delete(`/models/${modelId}`);
}

export async function setDefaultModel(
  modelId: string
): Promise<ModelResponse> {
  const { data } = await api.post<APIResponse<ModelResponse>>(
    `/models/${modelId}/set-default`
  );
  return data.data;
}

export async function testModelConnection(
  modelId: string
): Promise<{ success: boolean; message: string; response_preview?: string }> {
  const { data } = await api.post<APIResponse<{ success: boolean; message: string; response_preview?: string }>>(
    `/models/${modelId}/test-connection`,
    {},
    { timeout: 30000 } // 30秒超时，专门用于测试连接
  );
  return data.data;
}

// ============= Prompts APIs =============
export async function createPrompt(payload: PromptCreate): Promise<PromptResponse> {
  const { data } = await api.post<APIResponse<PromptResponse>>("/prompts", payload);
  return data.data;
}

export async function getPrompts(
  page: number = 1,
  pageSize: number = 50,
  category?: PromptCategoryEnum,
  search?: string,
  favoriteOnly?: boolean
): Promise<PaginatedResponse<PromptResponse>> {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (category) params.category = category;
  if (typeof favoriteOnly === "boolean") params.favorite_only = favoriteOnly;
  if (search) params.search = search;
  const { data } = await api.get<APIResponse<PaginatedResponse<PromptResponse>>>(
    "/prompts",
    { params }
  );
  return data.data;
}

export async function getPrompt(promptId: string): Promise<PromptResponse> {
  const { data } = await api.get<APIResponse<PromptResponse>>(`/prompts/${promptId}`);
  return data.data;
}

export async function updatePrompt(
  promptId: string,
  payload: PromptUpdate
): Promise<PromptResponse> {
  const { data } = await api.put<APIResponse<PromptResponse>>(`/prompts/${promptId}`, payload);
  return data.data;
}

export async function deletePrompt(promptId: string): Promise<void> {
  await api.delete(`/prompts/${promptId}`);
}

export async function togglePromptFavorite(promptId: string): Promise<PromptResponse> {
  const { data } = await api.post<APIResponse<PromptResponse>>(`/prompts/${promptId}/toggle-favorite`);
  return data.data;
}

export async function incrementPromptUsage(promptId: string): Promise<PromptResponse> {
  const { data } = await api.post<APIResponse<PromptResponse>>(`/prompts/${promptId}/increment-usage`);
  return data.data;
}

export async function getPromptStatistics(): Promise<PromptStatisticsResponse> {
  const { data } = await api.get<APIResponse<PromptStatisticsResponse>>("/prompts/statistics");
  return data.data;
}

