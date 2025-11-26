// ============= Common Types =============
export interface APIResponse<T = any> {
  code: number;
  msg: string;
  data: T;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ============= Auth Types =============
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
}

export interface AdminUserResponse {
  id: string;
  username: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

// ============= User Types (v3.0 Simplified) =============
export interface UserResponse {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  is_admin: boolean;
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  is_admin: boolean;
}

export interface UserUpdate {
  full_name?: string;
  email?: string;
  is_active?: boolean;
  is_admin?: boolean;
}

// ============= Model Configuration =============
export interface ModelConfig {
  name: string;
  api_key?: string;
  base_url?: string;
  parameters?: Record<string, any>;
  timeout?: number;
}

// ============= Dataset Types =============
export interface DatasetCreate {
  name: string;
  description?: string;
}

export interface DatasetResponse {
  id: string;
  name: string;
  description: string | null;
  project_id?: string | null;
  created_by: string;
  creator?: {
    id: string;
    username: string;
    email: string;
  } | null;
  file_path: string | null;
  file_size: number | null;
  file_type: string | null;
  row_count: number;
  columns: { columns: string[] } | null;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DatasetPreviewResponse {
  columns: string[];
  data_types: Record<string, string>;
  preview_data: any[];
  row_count: number;
  column_count: number;
}

export interface DatasetDataUpdate {
  preview_data: any[];
  row_count?: number;
}

export interface AnnotationColumn {
  column_name: string;
  column_type: string;
  description?: string | null;
  options?: string[] | null;
}

export interface AnnotationColumnCreate {
  column_name: string;
  column_type: string;
  description?: string;
  options?: string[];
}

export interface AnnotationColumnUpdate {
  old_column_name: string;
  new_column_name: string;
  column_type?: string;
  description?: string;
  options?: string[];
}

export interface AnnotationColumnDelete {
  column_name: string;
}

// ============= Metric Types =============
export enum EvalMetricTypeEnum {
  BUILTIN = "builtin",
  CUSTOM = "custom",
}

/**
 * 创建自定义维度请求 - 仅需三要素：名称、描述、提示词
 * 用户创建的维度自动设置为 CUSTOM 类型
 */
export interface MetricCreate {
  name: string;                           // 指标名称（必填）
  description?: string;                   // 描述（可选）
  prompt?: string;                        // 提示词（可选）
}

/**
 * 更新自定义维度 - 仅能修改三要素
 */
export interface MetricUpdate {
  name?: string;                          // 指标名称
  description?: string;                   // 描述
  prompt?: string;                        // 提示词
}

export interface MetricResponse {
  id: string;
  name: string;                           // 指标名称
  description: string | null;             // 描述
  type: EvalMetricTypeEnum;               // 指标类型
  prompt: string | null;                  // 提示词
  user_input_required: boolean;           // 是否需要用户输入
  actual_output_required: boolean;        // 是否需要实际输出
  expected_output_required: boolean;      // 是否需要期望输出
  context_required: boolean;              // 是否需要上下文
  retrieval_context_required: boolean;    // 是否需要检索上下文
  embedding_required: boolean;            // 是否需要嵌入模型
  llm_required: boolean;                  // 是否需要大语言模型
  created_by?: string | null;             // 创建者ID（系统内置维度为NULL）
  creator?: {                              // 创建者信息
    id: string;
    username: string;
    email: string;
  } | null;
  created_at: string;                     // 创建时间
  updated_at: string;                     // 更新时间
}

// ============= Evaluator Types =============
export interface ModelConfigForMetric {
  name: string;
  api_key?: string;
  base_url?: string;
  parameters?: Record<string, any>;
  timeout?: number;
}

export interface MetricModelConfig {
  metric_id: string;
  llm_config?: ModelConfigForMetric;
  embedding_config?: ModelConfigForMetric;
}

export interface EvaluatorConfigStructure {
  metric_model_configs?: MetricModelConfig[];
  default_llm_config?: ModelConfigForMetric;
  default_embedding_config?: ModelConfigForMetric;
}

export interface EvaluatorCreate {
  name: string;
  description?: string;
  metric_ids: string[];
  config?: EvaluatorConfigStructure;
}

export interface EvaluatorUpdate {
  name?: string;
  description?: string;
  metric_ids?: string[];
  config?: EvaluatorConfigStructure;
}

export interface EvaluatorResponse {
  id: string;
  name: string;
  description: string | null;
  metric_ids: string[];
  config: EvaluatorConfigStructure;
  created_by: string;
  created_by_username?: string | null;
  usage_count: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

// ============= Task Types =============
export enum TaskType {
  EVALUATION = "evaluation",
  SYNTHESIS = "synthesis",
  BATCH_EVALUATION = "batch_evaluation",
  NEGATIVE_MINING = "negative_mining",
}

export enum TaskStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export interface MetricConfig {
  metric_name: string;
  metric_type: string;
  prompt?: string;
}

export interface EvalCase {
  user_input?: string;
  actual_output?: string;
  expected_output?: string;
  context?: string[];
  retrieval_context?: string[];
  metadata?: Record<string, any>;
}

export interface CreateEvaluationTaskRequest {
  evaluator_id: string;
  llm_config?: ModelConfig;
  embedding_config?: ModelConfig;
  eval_case: EvalCase;
}

export interface SynthesizerConfig {
  synthesizer_name: string;
  config?: Record<string, any>;
}

export interface InputData {
  // Mode 1: Manual input
  context?: string[];
  themes?: string[];
  
  // Mode 2: Dataset import
  dataset_id?: string;
  context_field?: string;
  theme_field?: string;
  
  // Mode 3: File upload
  file_content?: string;  // Base64 encoded
  file_name?: string;
  file_type?: string;  // csv/jsonl/xlsx
  file_context_field?: string;
  file_theme_field?: string;
}

export interface CreateSynthesisTaskRequest {
  llm_config?: ModelConfig;
  embedding_config?: ModelConfig;
  synthesizer_config: SynthesizerConfig;
  input_data: InputData;
  metadata?: Record<string, any>;
}

export interface CreateBatchEvaluationTaskRequest {
  name?: string;
  dataset_id: string;
  evaluator_id?: string;
  metric_config?: MetricConfig;
  llm_config?: ModelConfig;
  embedding_config?: ModelConfig;
}

export interface NegativeMiningInputData {
  // Mode 1: Manual train_data input
  train_data?: Array<{
    query: string;
    pos: string[];
    neg?: string[];
  }>;
  candidate_pool?: string[];
  
  // Mode 2: Dataset import with field mapping
  dataset_id?: string;
  query_field?: string;
  pos_field?: string;
  neg_field?: string;
}

export interface CreateNegativeMiningTaskRequest {
  embedding_config: ModelConfig;
  input_data: NegativeMiningInputData;
  sample_range?: string;
  negative_number?: number;
  use_gpu?: boolean;
  embedding_batch_size?: number;
  metadata?: Record<string, any>;
}

export interface TaskResponse {
  id: string;
  name?: string | null;
  task_type: TaskType;
  status: TaskStatus;
  progress: number;
  dataset_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  result: Record<string, any> | null;
  error: string | null;
  total_tokens: number;
  total_cost: number;
  config?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface TaskCreateResponse {
  task_id: string;
  status: TaskStatus;
  created_at: string;
  estimated_time: number | null;
}

export interface EvaluationResultResponse {
  id: string;
  task_id: string;
  metric_name: string;
  score: number | null;
  reason: string | null;
  user_input: string | null;
  actual_output: string | null;
  expected_output: string | null;
  context: string[] | null;
  retrieval_context: string[] | null;
  usages: any[] | null;
  created_at: string;
}

export interface SynthesisResultResponse {
  id: string;
  task_id: string;
  question: string;
  answer: string;
  source_context: string[] | null;
  quality_score: number | null;
  usages: any[] | null;
  created_at: string;
}

// ============= Statistics Types =============
export interface DashboardStatisticsResponse {
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  success_rate: number;
  total_tokens: number;
  total_cost: number;
  recent_tasks: TaskResponse[];
}

// ============= Model Management Types =============
export enum ModelType {
  LLM = "llm",
  EMBEDDING = "embedding",
}

export interface ModelCreate {
  name: string;
  model_type: ModelType;
  provider?: string;
  model_name?: string;
  api_key?: string;
  base_url?: string;
  parameters?: Record<string, any>;
  timeout?: number;
  description?: string;
  is_default?: boolean;
}

export interface ModelUpdate {
  name?: string;
  provider?: string | null;
  model_name?: string | null;
  api_key?: string | null;
  base_url?: string | null;
  parameters?: Record<string, any>;
  timeout?: number;
  description?: string | null;
  is_default?: boolean;
}

export interface ModelResponse {
  id: string;
  name: string;
  model_type: ModelType;
  provider?: string | null;
  model_name?: string | null;
  api_key?: string;
  base_url?: string;
  parameters: Record<string, any>;
  timeout: number;
  description: string | null;
  is_default: boolean;
  usage_count: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

// ============= Health Check =============
export interface HealthzData {
  version: string;
  status: string;
  timestamp: string;
}

export interface HealthzResponse {
  code: number;
  msg: string;
  data: HealthzData;
}

// ============= Prompts (提示词) Types =============
export enum PromptCategoryEnum {
  SYSTEM = "系统",
  EVALUATION = "评估",
  SYNTHESIS = "合成",
  CUSTOM = "自定义",
}

export interface PromptCreate {
  name: string;
  description?: string;
  category: PromptCategoryEnum;
  content: string;
  variables?: string[];
  version?: string;
  is_favorite?: boolean;
}

export interface PromptUpdate {
  name?: string;
  description?: string;
  category?: PromptCategoryEnum;
  content?: string;
  variables?: string[];
  version?: string;
  is_favorite?: boolean;
}

export interface PromptResponse {
  id: string;
  name: string;
  description: string | null;
  category: PromptCategoryEnum;
  content: string;
  variables: string[];
  version: string;
  is_favorite: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface PromptStatisticsResponse {
  total_prompts: number;
  favorite_count: number;
  total_usage_count: number;
  category_count: number;
}

