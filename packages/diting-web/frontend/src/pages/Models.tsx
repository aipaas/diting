import { useEffect, useMemo, useState, useCallback, type FormEvent, type ReactNode, type ChangeEvent } from "react";
import { getModels, createModel, updateModel, deleteModel, setDefaultModel, testModelConnection } from "@/api/client";
import type { ModelResponse, ModelCreate, ModelUpdate } from "@/types/api";
import { ModelType } from "@/types/api";

const BASE_FIELD_CLASS =
  "w-full rounded-xl border border-slate-200 bg-white/90 px-3 py-2.5 text-sm text-slate-700 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-100 placeholder:text-slate-400";
const TEXT_AREA_CLASS = `${BASE_FIELD_CLASS} min-h-[120px] resize-none leading-relaxed`;
const SECTION_CARD_CLASS = "rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-sm backdrop-blur";
const SECTION_TITLE_CLASS = "text-sm font-semibold text-slate-900";
const LABEL_CLASS = "mb-1 text-xs font-semibold text-slate-500";

type ModelFormState = {
  name: string;
  model_type: ModelType;
  provider: string;
  model_name: string;
  api_key: string;
  base_url: string;
  description: string;
  timeout: number;
  is_default: boolean;
};

type ModelFormSubmitPayload = {
  formState: ModelFormState;
  parameters?: Record<string, any>;
};

interface ModelFormProps {
  mode: "create" | "edit";
  defaultToggleId: string;
  initialFormState: ModelFormState;
  initialParametersInput: string;
  initialShowAdvanced: boolean;
  onSubmit: (payload: ModelFormSubmitPayload) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
}

const ModelForm = ({
  mode,
  defaultToggleId,
  initialFormState,
  initialParametersInput,
  initialShowAdvanced,
  onSubmit,
  onCancel,
  submitLabel,
}: ModelFormProps) => {
  const [formState, setFormState] = useState<ModelFormState>(initialFormState);
  const [parametersInput, setParametersInput] = useState(initialParametersInput);
  const [parametersError, setParametersError] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(initialShowAdvanced);

  useEffect(() => {
    setFormState(initialFormState);
    setParametersInput(initialParametersInput);
    setShowAdvanced(initialShowAdvanced);
    setParametersError("");
  }, [initialFormState, initialParametersInput, initialShowAdvanced]);

  const updateField = useCallback(<K extends keyof ModelFormState>(key: K, value: ModelFormState[K]) => {
    setFormState((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleParametersChange = useCallback((event: ChangeEvent<HTMLTextAreaElement>) => {
    setParametersInput(event.target.value);
    if (parametersError) {
      setParametersError("");
    }
  }, [parametersError]);

  const toggleAdvanced = useCallback(() => {
    setShowAdvanced((prev) => !prev);
    if (parametersError) {
      setParametersError("");
    }
  }, [parametersError]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setParametersError("");

    let parsedParameters: Record<string, any> | undefined;
    if (parametersInput.trim()) {
      try {
        const parsed = JSON.parse(parametersInput);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          parsedParameters = Object.keys(parsed).length > 0 ? parsed : undefined;
        } else {
          setParametersError("请提供一个合法的 JSON 对象");
          return;
        }
      } catch (err) {
        console.error("Failed to parse parameters JSON:", err);
        setParametersError("高级参数 JSON 无法解析，请检查格式");
        return;
      }
    }

    await onSubmit({ formState, parameters: parsedParameters });
  };

  return (
    <form onSubmit={handleSubmit} className="flex max-h-[75vh] flex-col">
      <div className="overflow-y-auto px-6 py-6">
        <div className="space-y-6">
          <section className={SECTION_CARD_CLASS}>
            <div className="mb-5 flex items-start justify-between">
              <div>
                <h3 className={SECTION_TITLE_CLASS}>基础信息</h3>
                <p className="mt-1 text-xs text-slate-500">填写模型名称、类型与提供商</p>
              </div>
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-600/10 px-3 py-1 text-xs font-medium text-blue-600">
                <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <circle cx="10" cy="10" r="10" />
                </svg>
                必填
              </span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={`${LABEL_CLASS} flex items-center gap-1`}>
                  <span>模型名称</span>
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formState.name}
                  onChange={(event) => updateField("name", event.target.value)}
                  className={BASE_FIELD_CLASS}
                  placeholder="例如：数智助手 GPT-4"
                  required
                />
                <p className="mt-1 text-xs text-slate-400">用于在系统中展示的名称</p>
              </div>
              <div>
                <label className={`${LABEL_CLASS} flex items-center gap-1`}>
                  <span>模型类型</span>
                  <span className="text-red-500">*</span>
                </label>
                <select
                  value={formState.model_type}
                  onChange={(event) => updateField("model_type", event.target.value as ModelType)}
                  className={`${BASE_FIELD_CLASS} appearance-none`}
                  disabled={mode === "edit"}
                >
                  <option value="llm">LLM</option>
                  <option value="embedding">Embedding</option>
                </select>
                <p className="mt-1 text-xs text-slate-400">新建后不可修改，如需变更请重新创建</p>
              </div>
              <div>
                <label className={LABEL_CLASS}>提供商</label>
                <input
                  type="text"
                  value={formState.provider}
                  onChange={(event) => updateField("provider", event.target.value)}
                  className={BASE_FIELD_CLASS}
                  placeholder="例如：OpenAI、Azure、Anthropic（可选）"
                  autoComplete="off"
                />
                <p className="mt-1 text-xs text-slate-400">建议与实际供应商名称保持一致</p>
              </div>
              <div>
                <label className={LABEL_CLASS}>模型标识</label>
                <input
                  type="text"
                  value={formState.model_name}
                  onChange={(event) => updateField("model_name", event.target.value)}
                  className={BASE_FIELD_CLASS}
                  placeholder="例如：gpt-4, text-embedding-3-small（可选）"
                  autoComplete="off"
                />
                <p className="mt-1 text-xs text-slate-400">对应供应商中的模型名称</p>
              </div>
            </div>
          </section>

          <section className={SECTION_CARD_CLASS}>
            <div className="mb-5">
              <h3 className={SECTION_TITLE_CLASS}>连接配置</h3>
              <p className="mt-1 text-xs text-slate-500">可覆盖系统默认的密钥和调用地址</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={LABEL_CLASS}>API Key</label>
                <input
                  type="password"
                  value={formState.api_key}
                  onChange={(event) => updateField("api_key", event.target.value)}
                  className={BASE_FIELD_CLASS}
                  placeholder="留空则继承平台配置"
                  autoComplete="new-password"
                />
                <p className="mt-1 text-xs text-slate-400">可针对单个模型设置独立密钥</p>
              </div>
              <div>
                <label className={LABEL_CLASS}>Base URL</label>
                <input
                  type="text"
                  value={formState.base_url}
                  onChange={(event) => updateField("base_url", event.target.value)}
                  className={BASE_FIELD_CLASS}
                  placeholder="例如：https://api.openai.com/v1"
                  autoComplete="off"
                />
                <p className="mt-1 text-xs text-slate-400">可用于代理或私有化部署地址</p>
              </div>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <label className={LABEL_CLASS}>超时时间（秒）</label>
                <input
                  type="number"
                  min={1}
                  value={formState.timeout}
                  onChange={(event) => updateField("timeout", parseInt(event.target.value, 10) || 60)}
                  className={BASE_FIELD_CLASS}
                />
                <p className="mt-1 text-xs text-slate-400">默认 60 秒，可根据模型响应时间做适当调整</p>
              </div>
              <label
                htmlFor={defaultToggleId}
                className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white/90 px-4 py-3 shadow-sm transition hover:border-blue-200"
              >
                <span
                  className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition ${
                    formState.is_default ? "bg-blue-600" : "bg-slate-200"
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition ${
                      formState.is_default ? "translate-x-5" : "translate-x-1"
                    }`}
                  />
                </span>
                <div>
                  <p className="text-sm font-medium text-slate-700">设为默认模型</p>
                </div>
                <input
                  id={defaultToggleId}
                  type="checkbox"
                  checked={formState.is_default}
                  onChange={(event) => updateField("is_default", event.target.checked)}
                  className="sr-only"
                />
              </label>
            </div>
          </section>

          <section className={SECTION_CARD_CLASS}>
            <div className="flex items-center justify-between">
              <div>
                <h3 className={SECTION_TITLE_CLASS}>高级配置</h3>
                <p className="mt-1 text-xs text-slate-500">可选：描述信息与自定义参数</p>
              </div>
              <button
                type="button"
                onClick={toggleAdvanced}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition hover:border-blue-300 hover:text-blue-600"
              >
                <svg
                  className={`h-3.5 w-3.5 transition-transform ${showAdvanced ? "rotate-45" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v14m7-7H5" />
                </svg>
                {showAdvanced ? "收起" : "展开"}
              </button>
            </div>
            {showAdvanced ? (
              <div className="mt-5 space-y-4">
                <div>
                  <label className={LABEL_CLASS}>模型描述</label>
                  <textarea
                    value={formState.description}
                    onChange={(event) => updateField("description", event.target.value)}
                    className={TEXT_AREA_CLASS}
                    placeholder="补充模型用途、版本或限制等信息"
                  />
                </div>
                <div>
                  <label className={LABEL_CLASS}>自定义参数（JSON）</label>
                  <textarea
                    value={parametersInput}
                    onChange={handleParametersChange}
                    className={`${TEXT_AREA_CLASS} font-mono text-xs`}
                    placeholder={`例如：
{
  "temperature": 0.3,
  "top_p": 0.9
}`}
                  />
                  <p className="mt-1 text-xs text-slate-400">以 JSON 对象形式配置模型请求的额外参数</p>
                  {parametersError ? (
                    <p className="mt-2 text-xs font-medium text-red-500">{parametersError}</p>
                  ) : null}
                </div>
              </div>
            ) : (
              <p className="mt-4 text-xs text-slate-400">如需补充描述或下发额外参数时再展开配置。</p>
            )}
          </section>
        </div>
      </div>
      <div className="flex items-center justify-end gap-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-blue-200 hover:text-blue-600"
        >
          取消
        </button>
        <button
          type="submit"
          className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2 text-sm font-medium text-white shadow-sm transition hover:shadow-md"
        >
          {submitLabel}
        </button>
      </div>
    </form>
  );
};

const EMPTY_FORM_STATE: ModelFormState = {
  name: "",
  model_type: ModelType.LLM,
  provider: "",
  model_name: "",
  api_key: "",
  base_url: "",
  description: "",
  timeout: 60,
  is_default: false,
};

const mapModelToFormState = (model: ModelResponse): ModelFormState => ({
  name: model.name,
  model_type: model.model_type,
  provider: model.provider || "",
  model_name: model.model_name || "",
  api_key: model.api_key || "",
  base_url: model.base_url || "",
  description: model.description || "",
  timeout: model.timeout,
  is_default: model.is_default,
});

const getInitialParameters = (model?: ModelResponse | null): string => {
  if (model?.parameters && Object.keys(model.parameters).length > 0) {
    return JSON.stringify(model.parameters, null, 2);
  }
  return "";
};

const shouldShowAdvanced = (formState: ModelFormState, parametersInput: string): boolean => {
  return Boolean(formState.description || parametersInput.trim().length > 0);
};

const Models = () => {
  const [models, setModels] = useState<ModelResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"all" | "llm" | "embedding">("all");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelResponse | null>(null);
  const [testingModels, setTestingModels] = useState<Set<string>>(new Set());
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string; response_preview?: string }>>({});

  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;

  const tabs = useMemo(
    () => [
      { key: "all" as const, label: "全部模型" },
      { key: "llm" as const, label: "LLM 模型" },
      { key: "embedding" as const, label: "Embedding 模型" },
    ],
    [],
  );

  useEffect(() => {
    void fetchModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, activeTab]);

  const fetchModels = async () => {
    try {
      setLoading(true);
      setError("");
      const filterType = activeTab === "all" ? undefined : (activeTab as ModelType);
      const data = await getModels(currentPage, pageSize, filterType);
      setModels(data.items);
      setTotal(data.total);
    } catch (err: any) {
      console.error("Failed to fetch models:", err);
      setError("获取模型列表失败");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSubmit = async ({ formState, parameters }: ModelFormSubmitPayload) => {
    try {
      const payload: ModelCreate = {
        name: formState.name,
        model_type: formState.model_type,
        provider: formState.provider || undefined,
        model_name: formState.model_name || undefined,
        api_key: formState.api_key || undefined,
        base_url: formState.base_url || undefined,
        description: formState.description || undefined,
        timeout: formState.timeout,
        is_default: formState.is_default,
        parameters,
      };
      await createModel(payload);
      setShowCreateModal(false);
      await fetchModels();
    } catch (err: any) {
      console.error("Failed to create model:", err);
      alert("创建模型失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleEditSubmit = async ({ formState, parameters }: ModelFormSubmitPayload) => {
    if (!editingModel) return;
    try {
      const payload: ModelUpdate = {
        name: formState.name,
        provider: formState.provider === "" ? null : formState.provider || undefined,
        model_name: formState.model_name === "" ? null : formState.model_name || undefined,
        api_key: formState.api_key === "" ? null : formState.api_key || undefined,
        base_url: formState.base_url === "" ? null : formState.base_url || undefined,
        description: formState.description === "" ? null : formState.description || undefined,
        timeout: formState.timeout,
        is_default: formState.is_default,
        parameters,
      };
      await updateModel(editingModel.id, payload);
      setShowEditModal(false);
      setEditingModel(null);
      await fetchModels();
    } catch (err: any) {
      console.error("Failed to update model:", err);
      alert("更新模型失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleDelete = async (modelId: string) => {
    if (!confirm("确定要删除这个模型吗？")) return;
    try {
      await deleteModel(modelId);
      await fetchModels();
    } catch (err: any) {
      console.error("Failed to delete model:", err);
      alert("删除模型失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleSetDefault = async (modelId: string) => {
    try {
      await setDefaultModel(modelId);
      await fetchModels();
    } catch (err: any) {
      console.error("Failed to set default model:", err);
      alert("设置默认模型失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleTestConnection = async (modelId: string) => {
    if (testingModels.has(modelId)) return;

    setTestingModels((prev) => {
      const next = new Set(prev);
      next.add(modelId);
      return next;
    });

    setTestResults((prev) => {
      const next = { ...prev };
      delete next[modelId];
      return next;
    });

    try {
      const result = await testModelConnection(modelId);
      setTestResults((prev) => ({ ...prev, [modelId]: result }));
    } catch (err: any) {
      console.error("Failed to test connection:", err);
      setTestResults((prev) => ({
        ...prev,
        [modelId]: {
          success: false,
          message: "测试连接失败：" + (err.response?.data?.msg || err.message),
        },
      }));
    } finally {
      setTestingModels((prev) => {
        const next = new Set(prev);
        next.delete(modelId);
        return next;
      });
    }
  };

  const openEditModal = (model: ModelResponse) => {
    setEditingModel(model);
    setShowEditModal(true);
  };

  const closeCreateModal = () => setShowCreateModal(false);
  const closeEditModal = () => {
    setShowEditModal(false);
    setEditingModel(null);
  };

  const getProviderBadgeColor = (provider?: string | null) => {
    if (!provider) {
      return "bg-gray-50 text-gray-700 border-gray-200";
    }
    switch (provider.toLowerCase()) {
      case "openai":
        return "bg-green-50 text-green-700 border-green-200";
      case "azure":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "anthropic":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "google":
        return "bg-red-50 text-red-700 border-red-200";
      case "cohere":
        return "bg-orange-50 text-orange-700 border-orange-200";
      default:
        return "bg-gray-50 text-gray-700 border-gray-200";
    }
  };

  const ModalShell = ({
    title,
    subtitle,
    onClose,
    children,
  }: {
    title: string;
    subtitle?: string;
    onClose: () => void;
    children: ReactNode;
  }) => (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-8">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} />
      <div
        className="relative w-full max-w-3xl overflow-hidden rounded-3xl border border-white/60 bg-white/95 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-100 bg-gradient-to-r from-blue-600/10 via-transparent to-indigo-500/10 px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-transparent p-2 text-slate-400 transition hover:border-slate-200 hover:text-slate-600"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );

  const renderModalForm = () => {
    if (showEditModal && editingModel) {
      return (
        <ModelForm
          mode="edit"
          defaultToggleId={`model-default-toggle-edit-${editingModel.id}`}
          initialFormState={mapModelToFormState(editingModel)}
          initialParametersInput={getInitialParameters(editingModel)}
          initialShowAdvanced={shouldShowAdvanced(
            mapModelToFormState(editingModel),
            getInitialParameters(editingModel),
          )}
          submitLabel="保存"
          onSubmit={handleEditSubmit}
          onCancel={closeEditModal}
        />
      );
    }

    if (showCreateModal) {
      return (
        <ModelForm
          mode="create"
          defaultToggleId="model-default-toggle-create"
          initialFormState={EMPTY_FORM_STATE}
          initialParametersInput=""
          initialShowAdvanced={false}
          submitLabel="创建"
          onSubmit={handleCreateSubmit}
          onCancel={closeCreateModal}
        />
      );
    }

    return null;
  };

  return (
    <div className="relative pb-8">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-36 bg-gradient-to-br from-blue-100/60 via-white to-purple-100/50 -z-10" />
      <div className="relative mx-auto max-w-[1600px] space-y-4 px-4 py-3">
        <div className="rounded-2xl border border-white/70 bg-white/90 shadow-sm backdrop-blur">
          <div className="px-5 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
            <div className="flex items-center justify-between gap-4">
              {/* Left: Title and Filter Tabs */}
              <div className="flex items-center gap-6">
                <h2 className="text-lg font-bold text-slate-900">
                  模型中心
                </h2>

                {/* Filter Tabs */}
                <div className="flex items-center gap-2">
                  {tabs.map((tab) => (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => {
                        setActiveTab(tab.key);
                        setCurrentPage(1);
                      }}
                      aria-pressed={activeTab === tab.key}
                      className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                        activeTab === tab.key
                          ? "bg-blue-600 text-white shadow-sm"
                          : "border border-slate-200 text-slate-500 hover:border-blue-200 hover:text-blue-600"
                      }`}
                    >
                      <span>{tab.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Right: Add Button */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(true)}
                  className="px-4 py-2 bg-gradient-to-r from-brand-500 to-violet-500 text-white text-sm font-medium rounded-lg hover:from-brand-600 hover:to-violet-600 transition-all flex items-center gap-2 shadow-sm hover:shadow whitespace-nowrap"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                  </svg>
                  添加模型
                </button>
              </div>
            </div>
          </div>

          {/* Content Section */}
          <div className="p-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-100 border-t-blue-500" />
              <p className="text-sm text-slate-500">加载模型配置中...</p>
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-red-100 bg-red-50/80 px-6 py-5 text-sm text-red-600 shadow-inner">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-red-100 text-red-600">!</span>
                <span>{error}</span>
              </div>
            </div>
          ) : models.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-5 py-16 text-center">
              <div className="flex h-20 w-20 items-center justify-center rounded-3xl border border-dashed border-slate-200 bg-white text-slate-300">
                <svg className="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 5v14m7-7H5" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-600">暂未配置模型</p>
                <p className="mt-1 text-xs text-slate-400">创建第一个模型，开始构建评测能力</p>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-600 transition hover:border-blue-300 hover:bg-blue-100"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v14m7-7H5" />
                </svg>
                添加第一个模型
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {models.map((model) => {
                const modelInitial = (model.name?.charAt(0) || model.provider?.charAt(0) || "?").toUpperCase();
                const typeBadgeClass =
                  model.model_type === "llm"
                    ? "border-emerald-200 bg-emerald-50 text-emerald-600"
                    : "border-violet-200 bg-violet-50 text-violet-600";

                return (
                  <div
                    key={model.id}
                    className="group rounded-2xl border border-slate-200/80 bg-white/95 p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-lg"
                  >
                    <div className="flex flex-col gap-4">
                      {/* Main content area */}
                      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                        <div className="flex flex-1 gap-4">
                          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/15 via-blue-500/5 to-indigo-500/15 text-base font-semibold text-blue-600 shadow-inner">
                            {modelInitial}
                          </div>
                          <div className="flex-1 space-y-4">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="text-lg font-semibold text-slate-900">{model.name}</h3>
                              {model.is_default ? (
                                <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-600">
                                  <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.801 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.802-2.035a1 1 0 00-1.176 0l-2.802 2.035c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.293z" />
                                  </svg>
                                  默认
                                </span>
                              ) : null}
                              <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${typeBadgeClass}`}>
                                {model.model_type.toUpperCase()}
                              </span>
                              {model.provider ? (
                                <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${getProviderBadgeColor(model.provider)}`}>
                                  {model.provider}
                                </span>
                              ) : null}
                            </div>
                            <div className="grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
                              {model.model_name ? (
                                <div className="flex items-center gap-2">
                                  <span className="text-slate-500">模型标识</span>
                                  <span className="truncate font-mono text-xs text-slate-700" title={model.model_name}>
                                    {model.model_name}
                                  </span>
                                </div>
                              ) : null}
                              <div className="flex items-center gap-2">
                                <span className="text-slate-500">超时</span>
                                <span>{model.timeout} 秒</span>
                              </div>
                              {model.base_url ? (
                                <div className="flex items-center gap-2">
                                  <span className="text-slate-500">Base URL</span>
                                  <span className="truncate text-xs text-slate-700" title={model.base_url}>
                                    {model.base_url}
                                  </span>
                                </div>
                              ) : null}
                              <div className="flex items-center gap-2">
                                <span className="text-slate-500">使用次数</span>
                                <span>{model.usage_count}</span>
                              </div>
                            </div>
                            {model.description ? (
                              <p className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                                {model.description}
                              </p>
                            ) : null}
                          </div>
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-2 sm:flex-col sm:items-end sm:gap-3">
                          {!model.is_default ? (
                            <button
                              type="button"
                              onClick={() => handleSetDefault(model.id)}
                              className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-600 transition hover:border-blue-300 hover:bg-blue-100"
                            >
                              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M5 13l4 4L19 7" />
                              </svg>
                              设为默认
                            </button>
                          ) : null}
                          <button
                            type="button"
                            onClick={() => handleTestConnection(model.id)}
                            disabled={testingModels.has(model.id)}
                            className="inline-flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-3 py-1.5 text-sm font-medium text-green-600 transition hover:border-green-300 hover:bg-green-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {testingModels.has(model.id) ? (
                              <>
                                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-green-600 border-t-transparent" />
                                测试中...
                              </>
                            ) : (
                              <>
                                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                测试连接
                              </>
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => openEditModal(model)}
                            className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:border-blue-200 hover:text-blue-600"
                          >
                            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M16.862 3.487a1.5 1.5 0 012.121 2.121L7.62 16.971a2 2 0 01-.878.515l-2.743.762a.5.5 0 01-.62-.62l.762-2.743a2 2 0 01.515-.878L16.862 3.487z" />
                            </svg>
                            编辑
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(model.id)}
                            className="inline-flex items-center gap-2 rounded-full border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 transition hover:border-red-300 hover:bg-red-50"
                          >
                            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.75 9.75v6.75m4.5-6.75v6.75M5.25 6.75l.66 11.22A2.25 2.25 0 008.155 20.25h7.69a2.25 2.25 0 002.245-2.28l.66-11.22M4.5 6.75h15m-9-3h3a1.5 1.5 0 011.5 1.5V6.75h-6V5.25A1.5 1.5 0 0110.5 3.75z" />
                            </svg>
                            删除
                          </button>
                        </div>
                      </div>
                      
                      {/* Test result area - separate from button group */}
                      {testResults[model.id] ? (
                        <div
                          className={`rounded-xl border px-4 py-3 text-sm ${
                            testResults[model.id].success
                              ? "border-green-200 bg-green-50 text-green-700"
                              : "border-red-200 bg-red-50 text-red-700"
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            {testResults[model.id].success ? (
                              <svg className="h-5 w-5 shrink-0 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            ) : (
                              <svg className="h-5 w-5 shrink-0 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            )}
                            <div className="flex-1">
                              <p className="font-medium">{testResults[model.id].message}</p>
                              {testResults[model.id].response_preview ? (
                                <p className="mt-1 text-xs opacity-80">{testResults[model.id].response_preview}</p>
                              ) : null}
                            </div>
                            <button
                              type="button"
                              onClick={() =>
                                setTestResults((prev) => {
                                  const next = { ...prev };
                                  delete next[model.id];
                                  return next;
                                })
                              }
                              className="shrink-0 text-slate-400 hover:text-slate-600"
                            >
                              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {!loading && models.length > 0 ? (
            <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-5">
              <div className="text-sm text-slate-500">共 {total} 个模型</div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300"
                >
                  上一页
                </button>
                <span className="inline-flex items-center rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600">
                  第 {currentPage} 页
                </span>
                <button
                  type="button"
                  onClick={() => setCurrentPage((prev) => prev + 1)}
                  disabled={currentPage * pageSize >= total}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-blue-200 hover:text-blue-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300"
                >
                  下一页
                </button>
              </div>
            </div>
          ) : null}
          </div>
        </div>
      </div>

      {(showCreateModal || showEditModal) && (
        <ModalShell
          title={showEditModal ? "编辑模型" : "添加模型"}
          subtitle={showEditModal && editingModel ? `更新 ${editingModel.name} 的配置信息` : "创建新的模型接入配置"}
          onClose={showEditModal ? closeEditModal : closeCreateModal}
        >
          {renderModalForm()}
        </ModalShell>
      )}
    </div>
  );
};

export default Models;

