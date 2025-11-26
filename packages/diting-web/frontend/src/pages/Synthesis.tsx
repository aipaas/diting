import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Pagination from "@/components/Pagination";
import { createSynthesisTask, createNegativeMiningTask, getModels, exportSynthesisResults, createDatasetFromSynthesisResults, getDatasets, previewDataset, getTasks, deleteTask, retryTask } from "@/api/client";
import type { CreateSynthesisTaskRequest, CreateNegativeMiningTaskRequest, TaskCreateResponse, ModelResponse, TaskResponse, DatasetResponse, DatasetPreviewResponse, InputData, TaskType } from "@/types/api";
import { ModelType } from "@/types/api";

type TabType = "generation" | "hard_negative" | "distillation";

interface SynthesisProps {
  defaultTab?: TabType;
}

export default function Synthesis({ defaultTab = "generation" }: SynthesisProps) {
  const navigate = useNavigate();
  useLocation();
  const [activeTab, setActiveTab] = useState<TabType>(defaultTab);
  const [form, setForm] = useState({
    taskName: "",
    llmName: "",
    llmBaseUrl: "",
    llmApiKey: "",
    synthesizerName: "qa_synthesizer",
    themes: "",
    context: "",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TaskCreateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<ModelResponse[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [showApiKey, setShowApiKey] = useState(false);
  const [useModelSelection, setUseModelSelection] = useState(true);
  const [taskDetails] = useState<TaskResponse | null>(null);
  const [synthesisResults] = useState<any[]>([]);
  const [showCreateDatasetModal, setShowCreateDatasetModal] = useState(false);
  const [datasetName, setDatasetName] = useState("");
  const [datasetDescription, setDatasetDescription] = useState("");
  const [creatingDataset, setCreatingDataset] = useState(false);
  const [showCreateTaskModal, setShowCreateTaskModal] = useState(false);
  
  // Input mode states (manual / dataset / file)
  const [inputMode, setInputMode] = useState<'manual' | 'dataset' | 'file'>('manual');
  
  // Dataset import states
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [datasetPreview, setDatasetPreview] = useState<DatasetPreviewResponse | null>(null);
  const [contextField, setContextField] = useState("");
  const [themeField, setThemeField] = useState("");
  const [loadingDataset, setLoadingDataset] = useState(false);
  const [loadingAllData, setLoadingAllData] = useState(false);
  
  // File upload states
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [_filePreview, setFilePreview] = useState<{columns: string[], preview_data: any[]} | null>(null);
  const [fileContextField, setFileContextField] = useState("");
  const [fileThemeField, setFileThemeField] = useState("");
  const [_parsingFile, _setParsingFile] = useState(false);

  // Negative mining specific states
  const [embeddingModels, setEmbeddingModels] = useState<ModelResponse[]>([]);
  const [embeddingModelsLoading, setEmbeddingModelsLoading] = useState(true);
  const [useEmbeddingModelSelection, setUseEmbeddingModelSelection] = useState(true);
  const [showEmbeddingApiKey, setShowEmbeddingApiKey] = useState(false);
  const [negativeMiningForm, setNegativeMiningForm] = useState({
    taskName: "",
    embeddingName: "",
    embeddingBaseUrl: "",
    embeddingApiKey: "",
    trainDataJson: "",
    sampleRange: "10-210",
    negativeNumber: 15,
    useGpu: false,
    embeddingBatchSize: 32,
  });
  const [negativeMiningResults, _setNegativeMiningResults] = useState<any[]>([]);
  const [_useJsonInput, _setUseJsonInput] = useState(true);
  const [_showCreateDatasetFromMiningModal, _setShowCreateDatasetFromMiningModal] = useState(false);
  
  // Recent tasks (history) with pagination
  const [recentTasks, setRecentTasks] = useState<TaskResponse[]>([]);
  const [recentLoading, setRecentLoading] = useState(false);
  const [taskPage, setTaskPage] = useState(1);
  const [taskPageSize, setTaskPageSize] = useState(10);
  const [taskTotal, setTaskTotal] = useState(0);
  const [taskSearchQuery, setTaskSearchQuery] = useState("");
  const [taskFilterStatus, setTaskFilterStatus] = useState<string>("");
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set());
  
  // Negative mining dataset import states
  const [useNegativeMiningDatasetImport, setUseNegativeMiningDatasetImport] = useState(false);
  const [negativeMiningSelectedDatasetId, setNegativeMiningSelectedDatasetId] = useState("");
  const [negativeMiningDatasetPreview, setNegativeMiningDatasetPreview] = useState<DatasetPreviewResponse | null>(null);
  const [queryField, setQueryField] = useState("");
  const [posField, setPosField] = useState("");
  const [negField, setNegField] = useState("");
  const [loadingNegativeMiningDataset, setLoadingNegativeMiningDataset] = useState(false);
  const [_loadingNegativeMiningAllData, _setLoadingNegativeMiningAllData] = useState(false);

  const tabs = [
    { 
      key: "generation" as TabType, 
      label: "智能生成", 
      icon: "M12 4v16m8-8H4" 
    },
    { 
      key: "hard_negative" as TabType, 
      label: "负样本挖掘", 
      icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
    },
    { 
      key: "distillation" as TabType, 
      label: "数据蒸馏", 
      icon: "M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" 
    },
  ];

  // 设计系统样式类
  const baseFieldClass = "w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300";
  const textAreaClass = `${baseFieldClass} min-h-[100px] resize-none leading-relaxed`;
  const sectionCardClass = "rounded-2xl border border-slate-200/60 bg-white p-4 shadow-sm hover:shadow-md transition-shadow duration-200";
  const sectionTitleClass = "text-base font-semibold text-slate-900 mb-3 flex items-center gap-2";
  const labelClass = "mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5";

  // Set active tab from defaultTab prop
  useEffect(() => {
    setActiveTab(defaultTab);
  }, [defaultTab]);

  // 获取模型列表
  useEffect(() => {
    const fetchModels = async () => {
      try {
        setModelsLoading(true);
        const data = await getModels(1, 100, ModelType.LLM);
        setModels(data.items);
        // 设置默认模型
        const defaultModel = data.items.find(m => m.is_default) || data.items[0];
        if (defaultModel) {
          setForm(prev => ({ ...prev, llmName: defaultModel.name }));
        }
      } catch (err) {
        console.error("Failed to fetch models:", err);
      } finally {
        setModelsLoading(false);
      }
    };
    fetchModels();
  }, []);

  // 获取embedding模型列表
  useEffect(() => {
    const fetchEmbeddingModels = async () => {
      try {
        setEmbeddingModelsLoading(true);
        const data = await getModels(1, 100, ModelType.EMBEDDING);
        setEmbeddingModels(data.items);
        // 设置默认embedding模型
        const defaultModel = data.items.find(m => m.is_default) || data.items[0];
        if (defaultModel) {
          setNegativeMiningForm(prev => ({ ...prev, embeddingName: defaultModel.name }));
        }
      } catch (err) {
        console.error("Failed to fetch embedding models:", err);
      } finally {
        setEmbeddingModelsLoading(false);
      }
    };
    fetchEmbeddingModels();
  }, []);

  // Reset page when switching tabs
  useEffect(() => {
    setTaskPage(1);
  }, [activeTab]);

  // Load recent tasks per active tab
  useEffect(() => {
    const loadRecentTasks = async () => {
      try {
        setRecentLoading(true);
        // Map tab -> task type
        let taskType: TaskType | undefined = undefined;
        if (activeTab === 'generation') taskType = 'synthesis' as TaskType;
        else if (activeTab === 'hard_negative') taskType = 'negative_mining' as TaskType;
        else if (activeTab === 'distillation') {
          // 暂无任务类型，直接显示空
          setRecentTasks([]);
          setTaskTotal(0);
          return;
        }
        const data = await getTasks(taskPage, taskPageSize, taskType);
        setRecentTasks(data.items || []);
        setTaskTotal(data.total || 0);
      } catch (err) {
        // ignore silently
        setRecentTasks([]);
        setTaskTotal(0);
      } finally {
        setRecentLoading(false);
      }
    };
    loadRecentTasks();
  }, [activeTab, taskPage, taskPageSize]);

  // 获取数据集列表（智能生成使用）
  useEffect(() => {
    const fetchDatasetsForSynthesis = async () => {
      try {
        const data = await getDatasets(1, 100);
        setDatasets(data.items);
      } catch (err) {
        console.error("Failed to fetch datasets:", err);
      }
    };
    if (inputMode === 'dataset') {
      fetchDatasetsForSynthesis();
    }
  }, [inputMode]);

  // 获取数据集列表（负样本挖掘使用）
  useEffect(() => {
    const fetchDatasetsForNegativeMining = async () => {
      try {
        const data = await getDatasets(1, 100);
        setDatasets(data.items);
      } catch (err) {
        console.error("Failed to fetch datasets:", err);
      }
    };
    if (useNegativeMiningDatasetImport) {
      fetchDatasetsForNegativeMining();
    }
  }, [useNegativeMiningDatasetImport]);

  // 当选择数据集时，加载预览数据（负样本挖掘）
  useEffect(() => {
    const loadNegativeMiningDatasetPreview = async () => {
      if (!negativeMiningSelectedDatasetId) {
        setNegativeMiningDatasetPreview(null);
        setQueryField("");
        setPosField("");
        setNegField("");
        return;
      }

      try {
        setLoadingNegativeMiningDataset(true);
        // 只获取前5条用于预览，减少数据传输
        const preview = await previewDataset(negativeMiningSelectedDatasetId, 1, 5);
        setNegativeMiningDatasetPreview(preview);
        
        // 自动识别字段映射
        const columns = preview.columns;
        const queryCandidates = columns.filter(col => 
          col.toLowerCase().includes('query') || 
          col.toLowerCase().includes('question') ||
          col.toLowerCase().includes('q')
        );
        const posCandidates = columns.filter(col => 
          col.toLowerCase().includes('pos') || 
          col.toLowerCase().includes('positive') ||
          col.toLowerCase().includes('answer') ||
          col.toLowerCase().includes('correct')
        );
        const negCandidates = columns.filter(col => 
          col.toLowerCase().includes('neg') || 
          col.toLowerCase().includes('negative') ||
          col.toLowerCase().includes('wrong')
        );
        
        if (queryCandidates.length > 0) {
          setQueryField(queryCandidates[0]);
        }
        if (posCandidates.length > 0) {
          setPosField(posCandidates[0]);
        }
        if (negCandidates.length > 0) {
          setNegField(negCandidates[0]);
        }
      } catch (err) {
        console.error("Failed to load dataset preview:", err);
        setError("加载数据集预览失败");
      } finally {
        setLoadingNegativeMiningDataset(false);
      }
    };

    loadNegativeMiningDatasetPreview();
  }, [negativeMiningSelectedDatasetId]);


  // 当选择数据集时，加载预览数据
  useEffect(() => {
    const loadDatasetPreview = async () => {
      if (!selectedDatasetId) {
        setDatasetPreview(null);
        setContextField("");
        setThemeField("");
        return;
      }

      try {
        setLoadingDataset(true);
        const preview = await previewDataset(selectedDatasetId, 1, 10);
        setDatasetPreview(preview);
        
        // 自动识别字段映射
        const columns = preview.columns;
        // 尝试自动匹配常见字段名
        const contextCandidates = columns.filter(col => 
          col.toLowerCase().includes('context') || 
          col.toLowerCase().includes('content') || 
          col.toLowerCase().includes('text') ||
          col.toLowerCase().includes('document')
        );
        const themeCandidates = columns.filter(col => 
          col.toLowerCase().includes('theme') || 
          col.toLowerCase().includes('topic') ||
          col.toLowerCase().includes('category')
        );
        
        if (contextCandidates.length > 0) {
          setContextField(contextCandidates[0]);
        }
        if (themeCandidates.length > 0) {
          setThemeField(themeCandidates[0]);
        }
      } catch (err) {
        console.error("Failed to load dataset preview:", err);
        setError("加载数据集预览失败");
      } finally {
        setLoadingDataset(false);
      }
    };

    loadDatasetPreview();
  }, [selectedDatasetId]);

  // 当字段映射改变时，更新form数据
  useEffect(() => {
    if (!datasetPreview || !selectedDatasetId || (!contextField && !themeField)) {
      return;
    }

    const selectedDataset = datasets.find(d => d.id === selectedDatasetId);
    if (!selectedDataset) return;

    // 从预览数据中提取context和themes（暂时只使用预览数据，避免性能问题）
    const contexts: string[] = [];
    const themes: Set<string> = new Set();

    datasetPreview.preview_data.forEach(row => {
      // 提取context
      if (contextField && row[contextField]) {
        const contextValue = Array.isArray(row[contextField]) 
          ? row[contextField].join('\n')
          : String(row[contextField]);
        if (contextValue.trim()) {
          contexts.push(contextValue.trim());
        }
      }

      // 提取themes
      if (themeField && row[themeField]) {
        const themeValue = String(row[themeField]);
        if (themeValue.trim()) {
          // 如果是逗号分隔的字符串，拆分成多个主题
          themeValue.split(',').forEach(t => {
            const trimmed = t.trim();
            if (trimmed) {
              themes.add(trimmed);
            }
          });
        }
      }
    });

    // 如果数据集很大，只使用预览数据；否则可以加载全部数据
    const shouldLoadAllData = selectedDataset.row_count <= 100 && selectedDataset.row_count > datasetPreview.preview_data.length;
    
    if (shouldLoadAllData && (contextField || themeField)) {
      // 加载全部数据
      const loadAllData = async () => {
        try {
          setLoadingAllData(true);
          const allPreview = await previewDataset(selectedDatasetId, 1, selectedDataset.row_count);
          
          // 重新提取全部数据
          const allContexts: string[] = [];
          const allThemes: Set<string> = new Set();

          allPreview.preview_data.forEach(row => {
            if (contextField && row[contextField]) {
              const contextValue = Array.isArray(row[contextField]) 
                ? row[contextField].join('\n')
                : String(row[contextField]);
              if (contextValue.trim()) {
                allContexts.push(contextValue.trim());
              }
            }

            if (themeField && row[themeField]) {
              const themeValue = String(row[themeField]);
              if (themeValue.trim()) {
                themeValue.split(',').forEach(t => {
                  const trimmed = t.trim();
                  if (trimmed) {
                    allThemes.add(trimmed);
                  }
                });
              }
            }
          });

          setForm(prev => ({
            ...prev,
            context: allContexts.join('\n'),
            themes: Array.from(allThemes).join(', ')
          }));
        } catch (err) {
          console.error("Failed to load all data:", err);
          // 失败时使用预览数据
          setForm(prev => ({
            ...prev,
            context: contexts.join('\n'),
            themes: Array.from(themes).join(', ')
          }));
        } finally {
          setLoadingAllData(false);
        }
      };

      loadAllData();
    } else {
      // 使用预览数据
      setForm(prev => ({
        ...prev,
        context: contexts.join('\n'),
        themes: Array.from(themes).join(', ')
      }));
    }
  }, [datasetPreview, contextField, themeField, selectedDatasetId, datasets]);

  // 处理模型选择
  const handleModelSelect = (modelName: string) => {
    const selectedModel = models.find(m => m.name === modelName);
    if (selectedModel) {
      setForm(prev => ({
        ...prev,
        llmName: selectedModel.name,
        llmBaseUrl: selectedModel.base_url || "",
        llmApiKey: selectedModel.api_key || "",
      }));
    }
  };

  // 当切换到模型选择模式时，如果没有选择模型，自动选择默认模型
  useEffect(() => {
    if (useModelSelection && models.length > 0 && !form.llmName) {
      const defaultModel = models.find(m => m.is_default) || models[0];
      if (defaultModel) {
        setForm(prev => ({
          ...prev,
          llmName: defaultModel.name,
          llmBaseUrl: defaultModel.base_url || "",
          llmApiKey: defaultModel.api_key || "",
        }));
      }
    }
  }, [useModelSelection, models, form.llmName]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (activeTab === "hard_negative") {
      // Handle negative mining submission
      await handleNegativeMiningSubmit();
      return;
    }
    
    // Handle synthesis submission with three modes
    let inputData: InputData;
    
    if (inputMode === 'manual') {
      // Mode 1: Manual input validation
      if (!form.context && !form.themes) {
        setError("请至少提供主题或上下文之一");
        return;
      }
      inputData = {
        themes: form.themes
          ? form.themes.split(",").map((s) => s.trim()).filter(Boolean)
          : undefined,
        context: form.context
          ? form.context.split("\n").filter(Boolean)
          : undefined,
      };
    } else if (inputMode === 'dataset') {
      // Mode 2: Dataset import validation
      if (!selectedDatasetId) {
        setError("请选择数据集");
        return;
      }
      if (!contextField && !themeField) {
        setError("请至少选择一个字段映射（上下文或主题）");
        return;
      }
      // Optimized: only send dataset_id and field mappings (no actual data)
      inputData = {
        dataset_id: selectedDatasetId,
        context_field: contextField || undefined,
        theme_field: themeField || undefined,
      };
    } else {
      // Mode 3: File upload validation
      if (!uploadedFile) {
        setError("请上传文件");
        return;
      }
      if (!fileContextField && !fileThemeField) {
        setError("请至少选择一个字段映射（上下文或主题）");
        return;
      }
      // Convert file to base64
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve, reject) => {
        reader.onload = () => {
          const result = reader.result as string;
          // Extract base64 part (remove data:xxx;base64, prefix)
          const base64 = result.split(',')[1];
          resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(uploadedFile);
      });
      
      try {
        const file_content = await base64Promise;
        const fileExt = uploadedFile.name.split('.').pop()?.toLowerCase();
        inputData = {
          file_content,
          file_name: uploadedFile.name,
          file_type: fileExt === 'xlsx' || fileExt === 'xls' ? 'xlsx' : fileExt,
          file_context_field: fileContextField || undefined,
          file_theme_field: fileThemeField || undefined,
        };
      } catch (err) {
        setError("文件读取失败");
        return;
      }
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const payload: CreateSynthesisTaskRequest = {
      ...(form.llmName
        ? {
            llm_config: {
              name: form.llmName,
              base_url: form.llmBaseUrl || undefined,
              api_key: form.llmApiKey || undefined,
            },
          }
        : {}),
      synthesizer_config: {
        synthesizer_name: form.synthesizerName,
      },
      input_data: inputData,
      metadata: form.taskName.trim() ? { name: form.taskName.trim() } : undefined,
    };

   try {
      const data = await createSynthesisTask(payload);
      setResult(data);
      // Close creator modal on success
      setShowCreateTaskModal(false);
      // 数据合成任务创建成功后，留在当前页面（数据增强-生成）
      // 任务会自动出现在右侧的"最近任务"列表中
      // 刷新任务列表
      const taskType = 'synthesis' as TaskType;
      const taskData = await getTasks(taskPage, taskPageSize, taskType);
      setRecentTasks(taskData.items || []);
      setTaskTotal(taskData.total || 0);
    } catch (e: any) {
      setError(e?.response?.data?.detail || String(e));
    } finally {
      setLoading(false);
    }
  };

  // Handle negative mining submission
  const handleNegativeMiningSubmit = async () => {
    if (!negativeMiningForm.embeddingName) {
      setError("请选择或输入embedding模型名称");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    // 构建 embedding_config
    let embeddingConfig: any = {
      name: negativeMiningForm.embeddingName,
    };
    
    // 如果是手动输入模式，才添加 base_url 和 api_key
    if (!useEmbeddingModelSelection) {
      if (negativeMiningForm.embeddingBaseUrl) {
        embeddingConfig.base_url = negativeMiningForm.embeddingBaseUrl;
      }
      if (negativeMiningForm.embeddingApiKey) {
        embeddingConfig.api_key = negativeMiningForm.embeddingApiKey;
      }
    }

    let inputData: any;

    if (useNegativeMiningDatasetImport) {
      // 数据集导入模式：只传 dataset_id 和字段映射
      if (!negativeMiningSelectedDatasetId) {
        setError("请选择数据集");
        setLoading(false);
        return;
      }
      if (!queryField || !posField) {
        setError("请选择Query字段和Pos字段");
        setLoading(false);
        return;
      }
      
      inputData = {
        dataset_id: negativeMiningSelectedDatasetId,
        query_field: queryField,
        pos_field: posField,
        neg_field: negField || undefined,
      };
    } else {
      // 手动JSON输入模式：解析并验证训练数据
      if (!negativeMiningForm.trainDataJson.trim()) {
        setError("请输入训练数据（JSON格式）");
        setLoading(false);
        return;
      }

      let trainData: Array<{ query: string; pos: string[]; neg?: string[] }>;
      try {
        trainData = JSON.parse(negativeMiningForm.trainDataJson);
        if (!Array.isArray(trainData) || trainData.length === 0) {
          throw new Error("训练数据必须是包含至少一条数据的数组");
        }
        // Validate format
        for (const item of trainData) {
          if (!item.query || !Array.isArray(item.pos)) {
            throw new Error("每条数据必须包含 query 和 pos 字段");
          }
        }
      } catch (e: any) {
        setError(`训练数据格式错误: ${e.message}`);
        setLoading(false);
        return;
      }

      inputData = {
        train_data: trainData,
      };
    }

    const payload: CreateNegativeMiningTaskRequest = {
      embedding_config: embeddingConfig,
      input_data: inputData,
      sample_range: negativeMiningForm.sampleRange,
      negative_number: negativeMiningForm.negativeNumber,
      use_gpu: false, // GPU加速暂时禁用
      embedding_batch_size: negativeMiningForm.embeddingBatchSize,
      metadata: negativeMiningForm.taskName.trim() ? { name: negativeMiningForm.taskName.trim() } : undefined,
    };

   try {
      const data = await createNegativeMiningTask(payload);
      setResult(data);
      // Close creator modal on success
      setShowCreateTaskModal(false);
      // 负样本挖掘任务创建成功后，留在当前页面（数据增强-负样本挖掘）
      // 任务会自动出现在右侧的"最近任务"列表中
      // 刷新任务列表
      const taskType = 'negative_mining' as TaskType;
      const taskData = await getTasks(taskPage, taskPageSize, taskType);
      setRecentTasks(taskData.items || []);
      setTaskTotal(taskData.total || 0);
    } catch (e: any) {
      setError(e?.response?.data?.detail || String(e));
    } finally {
      setLoading(false);
    }
  };


  // Handle export negative mining results
  const handleExportNegativeMiningResults = (format: "json" | "jsonl" = "jsonl") => {
    if (negativeMiningResults.length === 0) return;
    
    let content = "";
    let filename = "";
    let mimeType = "";
    
    if (format === "json") {
      content = JSON.stringify(negativeMiningResults, null, 2);
      filename = `negative_mining_results_${result?.task_id || Date.now()}.json`;
      mimeType = "application/json";
    } else {
      content = negativeMiningResults.map(item => JSON.stringify(item)).join("\n");
      filename = `negative_mining_results_${result?.task_id || Date.now()}.jsonl`;
      mimeType = "application/x-ndjson";
    }
    
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };




  // Handle export
  const handleExport = async (format: "csv" | "jsonl" = "csv") => {
    if (!result?.task_id) return;
    try {
      await exportSynthesisResults(result.task_id, format);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "导出失败");
    }
  };

  // Handle create dataset
  const handleCreateDataset = async () => {
    if (!result?.task_id || !datasetName.trim()) {
      setError("请输入数据集名称");
      return;
    }
    
    setCreatingDataset(true);
    setError(null);
    
    try {
      const dataset = await createDatasetFromSynthesisResults(
        result.task_id,
        datasetName.trim(),
        datasetDescription.trim() || undefined
      );
      setShowCreateDatasetModal(false);
      setDatasetName("");
      setDatasetDescription("");
      // Show success message
      alert(`数据集 "${dataset.name}" 创建成功！`);
      // Optionally redirect to dataset detail page
      // window.location.href = `/datasets/${dataset.id}`;
    } catch (e: any) {
      setError(e?.response?.data?.detail || "创建数据集失败");
    } finally {
      setCreatingDataset(false);
    }
  };

  return (
    <div className="max-w-[1600px] mx-auto px-4 py-3 space-y-4">
      {/* Creator Modal */}
      {showCreateTaskModal && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4 sm:p-6 transition-opacity duration-200 overflow-y-auto">
          <div className="relative max-w-6xl w-full max-h-[95vh] transform transition-all duration-200 scale-100 my-auto">
            {/* Creator content (no tabs to avoid nested UI) */}
            <div className="bg-white rounded-3xl border border-slate-200/80 shadow-2xl overflow-hidden flex flex-col max-h-[95vh]">
        <div className="sticky top-0 z-10 border-b border-slate-200/80 px-6 py-3 bg-white flex items-center justify-between shadow-sm flex-shrink-0">
          <div className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            新建任务 · {tabs.find(t => t.key === activeTab)?.label}
          </div>
          <button
            onClick={() => setShowCreateTaskModal(false)}
            aria-label="关闭"
            className="p-2 rounded-xl text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-all duration-200 hover:scale-105"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-4 pb-4 overflow-y-auto flex-1">
          {activeTab === "hard_negative" ? (
            // Negative Mining Tab
          <form onSubmit={onSubmit} className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {/* Left Column Wrapper */}
            <div className="space-y-2">
              {/* Basic Information */}
              <div className={sectionCardClass}>
                <h2 className={sectionTitleClass}>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                    className={baseFieldClass}
                    value={negativeMiningForm.taskName}
                    onChange={(e) => setNegativeMiningForm((f) => ({ ...f, taskName: e.target.value }))}
                    placeholder="例如：负样本挖掘 - 搜索优化"
                  />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">
                    为任务设置一个便于识别的名称，留空则使用任务ID
                  </p>
                </div>
              </div>

              {/* Embedding Configuration */}
              <div className={sectionCardClass}>
                <div className="flex items-center justify-between mb-2">
                  <h2 className={sectionTitleClass}>
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                    </svg>
                    Embedding 配置
                  </h2>
                  <button
                    type="button"
                    onClick={() => setUseEmbeddingModelSelection(!useEmbeddingModelSelection)}
                    className="text-xs font-medium transition-all duration-200 px-3 py-1.5 rounded-lg border border-purple-200 text-purple-600 hover:bg-purple-50 hover:border-purple-300 hover:shadow-sm"
                  >
                    {useEmbeddingModelSelection ? "手动输入" : "选择模型"}
                  </button>
                </div>
                
                {useEmbeddingModelSelection ? (
                  <div className="space-y-2">
                    <div>
                      <label className={labelClass}>
                        <span>模型名称</span>
                        <span className="text-red-500">*</span>
                      </label>
                      {embeddingModelsLoading ? (
                        <div className="flex items-center gap-2 text-sm text-slate-500">
                          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          加载模型中...
                        </div>
                      ) : (
                        <select
                          className={baseFieldClass}
                          value={negativeMiningForm.embeddingName}
                          onChange={(e) => {
                            setNegativeMiningForm(prev => ({ ...prev, embeddingName: e.target.value }));
                          }}
                          required
                        >
                          <option value="">请选择模型</option>
                          {embeddingModels.map((model) => (
                            <option key={model.id} value={model.name}>
                              {model.name} {model.is_default && "(默认)"}
                            </option>
                          ))}
                        </select>
                      )}
                      <p className="mt-1 text-xs text-slate-500 leading-tight">从已配置的模型中选择</p>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                    <div>
                      <label className={labelClass}>
                        <span>模型名称</span>
                        <span className="text-red-500">*</span>
                      </label>
                      <input
                        className={baseFieldClass}
                        value={negativeMiningForm.embeddingName}
                        onChange={(e) =>
                          setNegativeMiningForm((f) => ({ ...f, embeddingName: e.target.value }))
                        }
                        placeholder="bge-m3"
                        required
                      />
                    </div>
                    <div>
                      <label className={labelClass}>
                        Base URL <span className="text-slate-400 font-normal">(可选)</span>
                      </label>
                      <input
                        className={baseFieldClass}
                        value={negativeMiningForm.embeddingBaseUrl}
                        onChange={(e) =>
                          setNegativeMiningForm((f) => ({ ...f, embeddingBaseUrl: e.target.value }))
                        }
                        placeholder="https://api.openai.com/v1"
                      />
                    </div>
                    <div>
                      <label className={labelClass}>
                        API Key <span className="text-slate-400 font-normal">(可选)</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showEmbeddingApiKey ? "text" : "password"}
                          className={baseFieldClass + " pr-10"}
                          value={negativeMiningForm.embeddingApiKey}
                          onChange={(e) =>
                            setNegativeMiningForm((f) => ({ ...f, embeddingApiKey: e.target.value }))
                          }
                          placeholder="sk-..."
                        />
                        <button
                          type="button"
                          onClick={() => setShowEmbeddingApiKey(!showEmbeddingApiKey)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                        >
                          {showEmbeddingApiKey ? (
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Advanced Parameters - merged into Embedding Configuration */}
                <div className="mt-3 pt-2 border-t border-slate-100">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                    <div>
                      <label className={labelClass}>
                        采样区间
                      </label>
                      <input
                        className={baseFieldClass}
                        value={negativeMiningForm.sampleRange}
                        onChange={(e) =>
                          setNegativeMiningForm((f) => ({ ...f, sampleRange: e.target.value }))
                        }
                        placeholder="10-210"
                      />
                      <p className="mt-1 text-xs text-slate-500 leading-tight">
                        跳过前N个最相似的，从第N到第M个中选择负样本（格式：起始-结束）
                      </p>
                    </div>
                    <div>
                      <label className={labelClass}>
                        负样本数量
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        className={baseFieldClass}
                        value={negativeMiningForm.negativeNumber}
                        onChange={(e) =>
                          setNegativeMiningForm((f) => ({ ...f, negativeNumber: parseInt(e.target.value) || 15 }))
                        }
                      />
                      <p className="mt-1 text-xs text-slate-500 leading-tight">
                        每条查询挖掘的负样本数量（1-1000）
                      </p>
                    </div>
                    <div>
                      <label className={labelClass}>
                        Embedding批处理大小
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="256"
                        className={baseFieldClass}
                        value={negativeMiningForm.embeddingBatchSize}
                        onChange={(e) =>
                          setNegativeMiningForm((f) => ({ ...f, embeddingBatchSize: parseInt(e.target.value) || 32 }))
                        }
                      />
                      <p className="mt-1 text-xs text-slate-500 leading-tight">
                        批量编码时的批次大小（1-256）
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column Wrapper */}
            <div className="space-y-2">
              {/* Training Data Input */}
              <div className={`${sectionCardClass} min-h-[440px]`}>
                <div className="flex items-center justify-between mb-2">
                  <h2 className={sectionTitleClass}>
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    训练数据
                  </h2>
                  <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
                    <button
                      type="button"
                      onClick={() => {
                        setUseNegativeMiningDatasetImport(false);
                        setNegativeMiningSelectedDatasetId("");
                        setNegativeMiningDatasetPreview(null);
                        setQueryField("");
                        setPosField("");
                        setNegField("");
                      }}
                      className={`text-xs font-medium transition-all duration-200 px-3 py-1.5 rounded-md ${
                        !useNegativeMiningDatasetImport
                          ? 'bg-white text-purple-700 shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      手动输入
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setUseNegativeMiningDatasetImport(true);
                        setNegativeMiningForm(prev => ({ ...prev, trainDataJson: "" }));
                      }}
                      className={`text-xs font-medium transition-all duration-200 px-3 py-1.5 rounded-md ${
                        useNegativeMiningDatasetImport
                          ? 'bg-white text-purple-700 shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      从数据集导入
                    </button>
                  </div>
                </div>

                {useNegativeMiningDatasetImport ? (
                  <div className="space-y-2 transition-all duration-200 ease-in-out">
                    {/* Dataset Selection */}
                    <div>
                      <label className={labelClass}>
                        <span>选择数据集</span>
                        <span className="text-red-500">*</span>
                      </label>
                      <select
                        className={baseFieldClass}
                        value={negativeMiningSelectedDatasetId}
                        onChange={(e) => setNegativeMiningSelectedDatasetId(e.target.value)}
                        required
                      >
                        <option value="">请选择数据集</option>
                        {datasets.map((dataset) => (
                          <option key={dataset.id} value={dataset.id}>
                            {dataset.name} ({dataset.row_count} 条)
                          </option>
                        ))}
                      </select>
                      {datasets.length === 0 && (
                        <p className="mt-1 text-xs text-slate-500 leading-tight">
                          暂无数据集，请先上传数据集
                        </p>
                      )}
                    </div>

                    {/* Field Mapping */}
                    {negativeMiningSelectedDatasetId && negativeMiningDatasetPreview && (
                      <>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-2 border-t border-slate-100 transition-all duration-200 ease-in-out">
                          <div>
                            <label className={labelClass}>
                              <span>Query字段</span>
                              <span className="text-red-500">*</span>
                            </label>
                            <select
                              className={baseFieldClass}
                              value={queryField}
                              onChange={(e) => setQueryField(e.target.value)}
                              required
                            >
                              <option value="">-- 请选择 --</option>
                              {negativeMiningDatasetPreview.columns.map((col) => (
                                <option key={col} value={col}>
                                  {col}
                                </option>
                              ))}
                            </select>
                            <p className="mt-0.5 text-xs text-slate-500">
                              查询字段
                            </p>
                          </div>
                          <div>
                            <label className={labelClass}>
                              <span>Pos字段</span>
                              <span className="text-red-500">*</span>
                            </label>
                            <select
                              className={baseFieldClass}
                              value={posField}
                              onChange={(e) => setPosField(e.target.value)}
                              required
                            >
                              <option value="">-- 请选择 --</option>
                              {negativeMiningDatasetPreview.columns.map((col) => (
                                <option key={col} value={col}>
                                  {col}
                                </option>
                              ))}
                            </select>
                            <p className="mt-0.5 text-xs text-slate-500">
                              正例字段（数组或逗号分隔）
                            </p>
                          </div>
                          <div>
                            <label className={labelClass}>
                              <span>Neg字段</span>
                              <span className="text-slate-400 font-normal">(可选)</span>
                            </label>
                            <select
                              className={baseFieldClass}
                              value={negField}
                              onChange={(e) => setNegField(e.target.value)}
                            >
                              <option value="">-- 不映射 --</option>
                              {negativeMiningDatasetPreview.columns.map((col) => (
                                <option key={col} value={col}>
                                  {col}
                                </option>
                              ))}
                            </select>
                            <p className="mt-0.5 text-xs text-slate-500">
                              负例字段（可选，数组或逗号分隔）
                            </p>
                          </div>
                        </div>

                        {/* Data Preview */}
                        {(loadingNegativeMiningDataset || _loadingNegativeMiningAllData) ? (
                          <div className="pt-4 flex items-center gap-2 text-sm text-slate-500">
                            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            {_loadingNegativeMiningAllData ? "加载并转换数据中..." : "加载数据中..."}
                          </div>
                        ) : negativeMiningDatasetPreview && queryField && posField ? (
                          <div className="pt-2 border-t border-slate-100 transition-all duration-200 ease-in-out">
                            <div className="bg-blue-50/80 border border-blue-200 rounded-xl p-2.5">
                              <h4 className="text-sm font-semibold text-blue-900 mb-1.5 flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                                数据预览 (前 {Math.min(negativeMiningDatasetPreview.preview_data.length, 3)} 条，共 {negativeMiningDatasetPreview.row_count} 条)
                              </h4>
                              <div className="space-y-1 text-sm text-blue-800">
                                {negativeMiningDatasetPreview.preview_data.slice(0, 3).map((row, idx) => (
                                  <div key={idx} className="bg-white/60 rounded p-1.5">
                                    <div className="font-medium text-blue-900 mb-0.5">
                                      Query: {String(row[queryField] || "").slice(0, 50)}
                                      {String(row[queryField] || "").length > 50 && "..."}
                                    </div>
                                    <div className="text-xs text-blue-700">
                                      Pos: {Array.isArray(row[posField]) 
                                        ? `[${row[posField].length} 项]`
                                        : String(row[posField] || "").slice(0, 50)}
                                      {!Array.isArray(row[posField]) && String(row[posField] || "").length > 50 && "..."}
                                    </div>
                                    {negField && row[negField] && (
                                      <div className="text-xs text-blue-700">
                                        Neg: {Array.isArray(row[negField]) 
                                          ? `[${row[negField].length} 项]`
                                          : String(row[negField] || "").slice(0, 50)}
                                        {!Array.isArray(row[negField]) && String(row[negField] || "").length > 50 && "..."}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        ) : null}
                      </>
                    )}
                  </div>
                ) : (
                  <div className="transition-all duration-200 ease-in-out">
                    <div className="flex items-center justify-between mb-2">
                      <label className={labelClass}>
                        <span>训练数据（JSON格式）</span>
                        <span className="text-red-500">*</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => {
                          const exampleData = `[
  {
    "query": "什么是Python？",
    "pos": ["Python是一种编程语言", "Python是高级语言"],
    "neg": []
  },
  {
    "query": "如何使用React？",
    "pos": ["React是一个UI库", "React使用JSX语法"],
    "neg": []
  }
]`;
                          setNegativeMiningForm((f) => ({ ...f, trainDataJson: exampleData }));
                        }}
                        className="text-xs font-medium text-purple-600 hover:text-purple-700 transition-colors flex items-center gap-1"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        使用示例
                      </button>
                    </div>
                    <textarea
                      className={`${textAreaClass} font-mono text-xs min-h-[320px] max-h-[400px] overflow-y-auto`}
                      rows={15}
                      value={negativeMiningForm.trainDataJson}
                      onChange={(e) =>
                        setNegativeMiningForm((f) => ({ ...f, trainDataJson: e.target.value }))
                      }
                      placeholder={`[
  {
    "query": "什么是Python？",
    "pos": ["Python是一种编程语言", "Python是高级语言"],
    "neg": []
  },
  {
    "query": "如何使用React？",
    "pos": ["React是一个UI库", "React使用JSX语法"],
    "neg": []
  }
]`}
                    />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">
                      格式：JSON数组，每项包含 query（查询）、pos（正例数组）、neg（负例数组，可选）
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <div className="lg:col-span-2 mt-4 pt-4 border-t border-slate-200 flex items-center justify-between gap-4">
              <div className="flex-1">
                {error && (
                  <div className="px-4 py-3 bg-red-50/80 border border-red-200/60 text-red-700 rounded-xl text-sm flex items-start gap-2 backdrop-blur-sm">
                    <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{error}</span>
                  </div>
                )}
              </div>
              <button
                className="px-8 py-3.5 bg-gradient-to-r from-brand-500 to-violet-500 hover:from-brand-600 hover:to-violet-600 text-white rounded-2xl font-semibold transition-all shadow-lg hover:shadow-xl disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed disabled:shadow-none flex items-center gap-2 min-w-[140px] justify-center"
                disabled={
                  loading ||
                  !negativeMiningForm.embeddingName ||
                  (useNegativeMiningDatasetImport 
                    ? (!negativeMiningSelectedDatasetId || !queryField || !posField)
                    : !negativeMiningForm.trainDataJson.trim())
                }
                type="submit"
              >
                {loading && (
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {loading ? "挖掘中..." : "开始挖掘"}
              </button>
            </div>
            </form>
          ) : activeTab === "distillation" ? (
            // Data Distillation Tab
            <form onSubmit={onSubmit} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left Column Wrapper */}
            <div className="space-y-3">
              {/* Basic Information */}
              <div className={sectionCardClass}>
                <h2 className={sectionTitleClass}>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                    className={baseFieldClass}
                    value={form.taskName}
                    onChange={(e) => setForm((f) => ({ ...f, taskName: e.target.value }))}
                    placeholder="例如：数据蒸馏 - 模型优化"
                  />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">
                    为任务设置一个便于识别的名称，留空则使用任务ID
                  </p>
                </div>
              </div>

              {/* Configuration */}
              <div className={sectionCardClass}>
                <h2 className={sectionTitleClass}>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                  配置信息
                </h2>
                <div>
                  <label className={labelClass}>
                    <span>配置项</span>
                    <span className="text-slate-400 font-normal">(可选)</span>
                  </label>
                  <input
                    className={baseFieldClass}
                    placeholder="数据蒸馏配置..."
                  />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">
                    数据蒸馏功能开发中，敬请期待
                  </p>
                </div>
              </div>
            </div>

            {/* Right Column Wrapper */}
            <div className="space-y-3">
              {/* Input Data */}
              <div className={sectionCardClass}>
                <h2 className={sectionTitleClass}>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  输入数据
                </h2>
                <div className="text-center py-12 text-slate-500">
                  <svg className="w-16 h-16 mx-auto mb-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <p className="text-base font-medium">数据蒸馏功能开发中</p>
                  <p className="text-sm mt-2">该功能即将上线，敬请期待</p>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <div className="lg:col-span-2 mt-4 pt-4 border-t border-slate-200 flex items-center justify-end gap-4">
              <button
                className="px-8 py-3.5 bg-gradient-to-r from-brand-500 to-violet-500 hover:from-brand-600 hover:to-violet-600 text-white rounded-2xl font-semibold transition-all shadow-lg hover:shadow-xl disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed disabled:shadow-none flex items-center gap-2 min-w-[140px] justify-center"
                disabled={true}
                type="button"
              >
                功能开发中
              </button>
            </div>
          </form>
          ) : (
            // Synthesis Tab (existing code)
            <form onSubmit={onSubmit} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left Column Wrapper */}
            <div className="space-y-3">
              {/* Basic Information */}
              <div className={sectionCardClass}>
                <h2 className={sectionTitleClass}>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                    className={baseFieldClass}
                    value={form.taskName}
                    onChange={(e) => setForm((f) => ({ ...f, taskName: e.target.value }))}
                    placeholder="例如：知识库问答生成 - 2024年11月"
                  />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">
                    为任务设置一个便于识别的名称，留空则使用任务ID
                  </p>
                </div>
              </div>

              {/* Synthesizer Configuration */}
              <div className={sectionCardClass}>
                <h2 className={sectionTitleClass}>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  合成器配置
                </h2>
                <div>
                  <label className={labelClass}>
                    <span>合成器名称</span>
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    className={baseFieldClass}
                    value={form.synthesizerName}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, synthesizerName: e.target.value }))
                    }
                    placeholder="qa_synthesizer"
                    required
                  />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">用于生成数据的合成器类型</p>
                </div>
              </div>

              {/* LLM Configuration */}
              <div className={sectionCardClass}>
              <div className="flex items-center justify-between mb-3">
                <h2 className={sectionTitleClass}>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  LLM 配置
                </h2>
                <button
                  type="button"
                  onClick={() => setUseModelSelection(!useModelSelection)}
                  className="text-xs font-medium transition-all duration-200 px-3 py-1.5 rounded-lg border border-purple-200 text-purple-600 hover:bg-purple-50 hover:border-purple-300 hover:shadow-sm"
                >
                  {useModelSelection ? "手动输入" : "选择模型"}
                </button>
              </div>
              
              {useModelSelection ? (
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>
                      <span>模型名称</span>
                      <span className="text-slate-400 font-normal">(可选)</span>
                    </label>
                    {modelsLoading ? (
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        加载模型中...
                      </div>
                    ) : (
                      <select
                        className={baseFieldClass}
                        value={form.llmName}
                        onChange={(e) => {
                          handleModelSelect(e.target.value);
                        }}
                        
                      >
                        <option value="">请选择模型</option>
                        {models.map((model) => (
                          <option key={model.id} value={model.name}>
                            {model.name} {model.is_default && "(默认)"}
                          </option>
                        ))}
                      </select>
                    )}
                            <p className="mt-1 text-xs text-slate-500 leading-tight">从已配置的模型中选择；可留空时系统将使用默认模型（如已设置）</p>
                  </div>
                </div>
              ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
                    <label className={labelClass}>
                      <span>模型名称</span>
                      <span className="text-slate-400 font-normal">(可选)</span>
              </label>
              <input
                      className={baseFieldClass}
                value={form.llmName}
                onChange={(e) =>
                  setForm((f) => ({ ...f, llmName: e.target.value }))
                }
                placeholder="gpt-4o-mini"
              />
            </div>
            <div>
                    <label className={labelClass}>
                      Base URL <span className="text-slate-400 font-normal">(可选)</span>
              </label>
              <input
                      className={baseFieldClass}
                value={form.llmBaseUrl}
                onChange={(e) =>
                  setForm((f) => ({ ...f, llmBaseUrl: e.target.value }))
                }
                placeholder="https://api.openai.com/v1"
              />
            </div>
            <div>
                    <label className={labelClass}>
                      API Key <span className="text-slate-400 font-normal">(可选)</span>
              </label>
                    <div className="relative">
              <input
                        type={showApiKey ? "text" : "password"}
                        className={baseFieldClass + " pr-10"}
                value={form.llmApiKey}
                onChange={(e) =>
                  setForm((f) => ({ ...f, llmApiKey: e.target.value }))
                }
                placeholder="sk-..."
              />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showApiKey ? (
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        )}
                      </button>
                    </div>
            </div>
          </div>
              )}
              </div>
            </div>

            {/* Right Column Wrapper */}
            <div className="space-y-3">
              {/* Input Data */}
              <div className={sectionCardClass}>
              <div className="flex items-center justify-between mb-3">
                <h2 className={sectionTitleClass}>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  输入数据
                </h2>
                <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
                  <button
                    type="button"
                    onClick={() => setInputMode('manual')}
                    className={`text-xs font-medium transition-all duration-200 px-3 py-1.5 rounded-md ${
                      inputMode === 'manual'
                        ? 'bg-white text-purple-700 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    手动输入
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputMode('dataset')}
                    className={`text-xs font-medium transition-all duration-200 px-3 py-1.5 rounded-md ${
                      inputMode === 'dataset'
                        ? 'bg-white text-purple-700 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    从数据集导入
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputMode('file')}
                    className={`text-xs font-medium transition-all duration-200 px-3 py-1.5 rounded-md ${
                      inputMode === 'file'
                        ? 'bg-white text-purple-700 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    上传文件
                  </button>
                </div>
              </div>

              {inputMode === 'dataset' ? (
                <div className="space-y-4">
                  {/* Dataset Selection */}
                  <div>
                    <label className={labelClass}>
                      <span>选择数据集</span>
                      <span className="text-red-500">*</span>
                    </label>
                    <select
                      className={baseFieldClass}
                      value={selectedDatasetId}
                      onChange={(e) => setSelectedDatasetId(e.target.value)}
                      required
                    >
                      <option value="">请选择数据集</option>
                      {datasets.map((dataset) => (
                        <option key={dataset.id} value={dataset.id}>
                          {dataset.name} ({dataset.row_count} 条)
                        </option>
                      ))}
                    </select>
                    {datasets.length === 0 && (
                      <p className="mt-1 text-xs text-slate-500 leading-tight">
                        暂无数据集，请先上传数据集
                      </p>
                    )}
                  </div>

                  {/* Field Mapping */}
                  {selectedDatasetId && datasetPreview && (
                    <>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
                        <div>
                          <label className={labelClass}>
                            <span>上下文字段</span>
                            <span className="text-slate-400 font-normal">(可选)</span>
                          </label>
                          <select
                            className={baseFieldClass}
                            value={contextField}
                            onChange={(e) => setContextField(e.target.value)}
                          >
                            <option value="">-- 不映射 --</option>
                            {datasetPreview.columns.map((col) => (
                              <option key={col} value={col}>
                                {col}
                              </option>
                            ))}
                          </select>
                          <p className="mt-1 text-xs text-slate-500 leading-tight">
                            选择作为上下文的字段
                          </p>
                        </div>
                        <div>
                          <label className={labelClass}>
                            <span>主题字段</span>
                            <span className="text-slate-400 font-normal">(可选)</span>
                          </label>
                          <select
                            className={baseFieldClass}
                            value={themeField}
                            onChange={(e) => setThemeField(e.target.value)}
                          >
                            <option value="">-- 不映射 --</option>
                            {datasetPreview.columns.map((col) => (
                              <option key={col} value={col}>
                                {col}
                              </option>
                            ))}
                          </select>
                          <p className="mt-1 text-xs text-slate-500 leading-tight">
                            选择作为主题的字段
                          </p>
                        </div>
                      </div>

                      {/* Data Preview */}
                      {(loadingDataset || loadingAllData) ? (
                        <div className="pt-4 flex items-center gap-2 text-sm text-slate-500">
                          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          {loadingAllData ? "加载全部数据中..." : "加载数据中..."}
                        </div>
                      ) : datasetPreview && (contextField || themeField) ? (
                        <div className="pt-4 border-t border-slate-100">
                          <div className="bg-blue-50/80 border border-blue-200 rounded-xl p-4">
                            <h4 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-2">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                              数据预览 (前 {Math.min(datasetPreview.preview_data.length, 10)} 条，共 {datasetPreview.row_count} 条)
                            </h4>
                            <div className="space-y-2 text-sm text-blue-800">
                              {contextField && (
                                <div>
                                  <span className="font-medium">上下文:</span>{" "}
                                  <span className="text-blue-600">
                                    {datasetPreview.preview_data
                                      .slice(0, 3)
                                      .map(row => row[contextField])
                                      .filter(Boolean)
                                      .join(", ")}
                                    {datasetPreview.preview_data.length > 3 && "..."}
                                  </span>
                                </div>
                              )}
                              {themeField && (
                                <div>
                                  <span className="font-medium">主题:</span>{" "}
                                  <span className="text-blue-600">
                                    {Array.from(
                                      new Set(
                                        datasetPreview.preview_data
                                          .slice(0, 10)
                                          .map(row => row[themeField])
                                          .filter(Boolean)
                                      )
                                    ).join(", ")}
                                    {datasetPreview.preview_data.length > 10 && "..."}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </>
                  )}

                  {/* Mapped Data Display */}
                  {(contextField || themeField) && (
                    <div className="pt-2 border-t border-slate-100">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className={labelClass}>
                            主题 <span className="text-slate-400 font-normal">(自动填充)</span>
                          </label>
                          <input
                            className={baseFieldClass}
                            value={form.themes}
                            onChange={(e) =>
                              setForm((f) => ({ ...f, themes: e.target.value }))
                            }
                            placeholder="从数据集自动填充..."
                            readOnly={themeField !== ""}
                          />
                          {themeField && (
                            <p className="mt-1.5 text-xs text-slate-400">
                              已从数据集字段 "{themeField}" 自动填充
                            </p>
                          )}
                        </div>
                        <div>
                          <label className={labelClass}>
                            上下文 <span className="text-slate-400 font-normal">(自动填充)</span>
                          </label>
                          <textarea
                            className={textAreaClass}
                            rows={12}
                            value={form.context}
                            onChange={(e) =>
                              setForm((f) => ({ ...f, context: e.target.value }))
                            }
                            placeholder="从数据集自动填充..."
                            readOnly={contextField !== ""}
                          />
                          {contextField && (
                            <p className="mt-1.5 text-xs text-slate-400">
                              已从数据集字段 "{contextField}" 自动填充 ({form.context.split('\n').filter(Boolean).length} 条)
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : inputMode === 'file' ? (
                <div className="space-y-4">
                  {/* File Upload */}
                  <div>
                    <label className={labelClass}>
                      <span>上传文件</span>
                      <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="file"
                      accept=".csv,.jsonl,.xlsx,.xls"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          setUploadedFile(file);
                          setFilePreview(null);
                          setFileContextField("");
                          setFileThemeField("");
                        }
                      }}
                      className={baseFieldClass}
                    />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">
                      支持格式: CSV, JSONL, Excel (.xlsx/.xls)
                    </p>
                  </div>
                  
                  {uploadedFile && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-amber-800">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span className="font-medium">已选择文件:</span>
                        <span>{uploadedFile.name}</span>
                      </div>
                      <p className="mt-2 text-sm text-amber-700">
                        📝 注意：文件上传功能需要先实现字段映射预览。目前建议使用"从数据集导入"功能。
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>
                      主题 <span className="text-slate-400 font-normal">(逗号分隔)</span>
                    </label>
                    <input
                      className={baseFieldClass}
                      value={form.themes}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, themes: e.target.value }))
                      }
                      placeholder="主题1, 主题2, 主题3"
                    />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">
                      示例: Python编程, 机器学习, 数据分析
                    </p>
                  </div>
                  <div>
                    <label className={labelClass}>
                      上下文 <span className="text-slate-400 font-normal">(每行一条)</span>
                    </label>
                    <textarea
                      className={textAreaClass}
                      rows={8}
                      value={form.context}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, context: e.target.value }))
                      }
                      placeholder="提供相关的上下文信息，每行一条..."
                    />
                            <p className="mt-1 text-xs text-slate-500 leading-tight">
                      可以是文档片段、知识库内容等
                    </p>
                  </div>
                </div>
              )}
              </div>
            </div>

            {/* Submit Button */}
            <div className="lg:col-span-2 mt-4 pt-4 border-t border-slate-200 flex items-center justify-between gap-4">
              <div className="flex-1">
                {error && (
                  <div className="px-4 py-3 bg-red-50/80 border border-red-200/60 text-red-700 rounded-xl text-sm flex items-start gap-2 backdrop-blur-sm">
                    <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{error}</span>
                  </div>
                )}
              </div>
              <button
                className="px-8 py-3.5 bg-gradient-to-r from-brand-500 to-violet-500 hover:from-brand-600 hover:to-violet-600 text-white rounded-2xl font-semibold transition-all shadow-lg hover:shadow-xl disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed disabled:shadow-none flex items-center gap-2 min-w-[140px] justify-center"
                disabled={
                  loading ||
                  !form.synthesizerName ||
                  (inputMode === 'dataset' && (!selectedDatasetId || (!contextField && !themeField))) ||
                  (inputMode === 'manual' && !form.context && !form.themes) ||
                  (inputMode === 'file' && (!uploadedFile || (!fileContextField && !fileThemeField)))
                }
                type="submit"
              >
                {loading && (
                  <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {loading ? "创建中..." : "创建任务"}
              </button>
            </div>
          </form>
          )}
        </div>
      </div>
          </div>
        </div>
          )}

          {/* Result */}
          {result && (
            <div className={`${sectionCardClass} mt-6`}>
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  任务详情
                </h2>
                <span className={`px-3 py-1.5 rounded-xl text-sm font-medium border ${
                  (taskDetails?.status || result.status) === "pending" || (taskDetails?.status || result.status) === "running"
                    ? "bg-blue-50 text-blue-700 border-blue-200" 
                    : (taskDetails?.status || result.status) === "completed"
                    ? "bg-green-50 text-green-700 border-green-200"
                    : "bg-red-50 text-red-700 border-red-200"
                }`}>
                  {(taskDetails?.status || result.status) === "pending" ? "等待中" :
                   (taskDetails?.status || result.status) === "running" ? "运行中" :
                   (taskDetails?.status || result.status) === "completed" ? "已完成" : 
                   (taskDetails?.status || result.status)}
            </span>
          </div>

          <div className="space-y-4">
                <div className="bg-blue-50/80 border border-blue-200 rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    任务信息
                  </h3>
                  <div className="space-y-2.5 text-sm text-blue-800">
                    <div className="flex justify-between items-center">
                      <span className="text-blue-600 font-medium">任务 ID:</span>
                      <code className="font-mono text-xs bg-blue-100 px-2 py-1 rounded">{result.task_id}</code>
                </div>
                    <div className="flex justify-between items-center">
                      <span className="text-blue-600 font-medium">创建时间:</span>
                  <span>{new Date(result.created_at).toLocaleString("zh-CN")}</span>
                </div>
                    {taskDetails && (
                      <>
                        {taskDetails.completed_at && (
                          <div className="flex justify-between items-center">
                            <span className="text-blue-600 font-medium">完成时间:</span>
                            <span>{new Date(taskDetails.completed_at).toLocaleString("zh-CN")}</span>
                          </div>
                        )}
                        {taskDetails.total_tokens > 0 && (
                          <div className="flex justify-between items-center">
                            <span className="text-blue-600 font-medium">Token 使用量:</span>
                            <span>{taskDetails.total_tokens.toLocaleString()}</span>
                          </div>
                        )}
                        {taskDetails.total_cost > 0 && (
                          <div className="flex justify-between items-center">
                            <span className="text-blue-600 font-medium">成本:</span>
                            <span>${taskDetails.total_cost.toFixed(4)}</span>
                          </div>
                        )}
                      </>
                    )}
                {result.estimated_time && (
                      <div className="flex justify-between items-center">
                        <span className="text-blue-600 font-medium">预计时间:</span>
                    <span>{result.estimated_time} 秒</span>
                  </div>
                )}
              </div>
            </div>

                {/* Results count and actions */}
                {activeTab === "hard_negative" ? (
                  // Negative Mining Results
                  <>
                    {negativeMiningResults.length > 0 && (
                      <div className="bg-purple-50/80 border border-purple-200 rounded-xl p-5">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-sm font-semibold text-purple-900 flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            挖掘结果
                          </h3>
                          <span className="text-sm text-purple-700 font-medium">
                            共 {negativeMiningResults.length} 条数据
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-3">
                          <button
                            onClick={() => handleExportNegativeMiningResults("json")}
                            className="px-4 py-2 bg-white border border-purple-300 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-50 transition-colors flex items-center gap-2"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            导出 JSON
                          </button>
                          <button
                            onClick={() => handleExportNegativeMiningResults("jsonl")}
                            className="px-4 py-2 bg-white border border-purple-300 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-50 transition-colors flex items-center gap-2"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            导出 JSONL
                          </button>
                        </div>
                        {/* Preview first few results */}
                        <div className="mt-4 space-y-2 max-h-96 overflow-y-auto">
                          {negativeMiningResults.slice(0, 5).map((item: any, idx: number) => (
                            <div key={idx} className="bg-white rounded-lg p-3 border border-purple-200">
                              <div className="text-sm font-medium text-purple-900 mb-1">Query: {item.query}</div>
                              <div className="text-xs text-purple-700">
                                <span className="font-medium">正例:</span> {item.pos?.length || 0} 条
                                {item.pos && item.pos.length > 0 && (
                                  <span className="ml-2">({item.pos.slice(0, 2).join(", ")}{item.pos.length > 2 ? "..." : ""})</span>
                                )}
                              </div>
                              <div className="text-xs text-purple-700">
                                <span className="font-medium">负例:</span> {item.neg?.length || 0} 条
                                {item.neg && item.neg.length > 0 && (
                                  <span className="ml-2">({item.neg.slice(0, 2).join(", ")}{item.neg.length > 2 ? "..." : ""})</span>
                                )}
                              </div>
                            </div>
                          ))}
                          {negativeMiningResults.length > 5 && (
                            <div className="text-xs text-purple-600 text-center py-2">
                              还有 {negativeMiningResults.length - 5} 条结果，请导出查看全部
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    {(taskDetails?.status || result.status) === "completed" && negativeMiningResults.length === 0 && (
                      <div className="bg-green-50/80 border border-green-200 rounded-xl p-4 flex items-start gap-2">
                        <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className="text-sm text-green-800 leading-relaxed">
                          任务已完成，正在加载结果...
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  // Synthesis Results
                  <>
                {synthesisResults.length > 0 && (
                  <div className="bg-purple-50/80 border border-purple-200 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-semibold text-purple-900 flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        生成结果
                      </h3>
                      <span className="text-sm text-purple-700 font-medium">
                        共 {synthesisResults.length} 条数据
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={() => handleExport("csv")}
                        className="px-4 py-2 bg-white border border-purple-300 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-50 transition-colors flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        导出 CSV
                      </button>
                      <button
                        onClick={() => handleExport("jsonl")}
                        className="px-4 py-2 bg-white border border-purple-300 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-50 transition-colors flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        导出 JSONL
                      </button>
              <button
                onClick={() => setShowCreateDatasetModal(true)}
                className="px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                        </svg>
                        导入为数据集
                      </button>
                    </div>
                  </div>
                )}

                {(taskDetails?.status || result.status) === "completed" && synthesisResults.length === 0 && (
                  <div className="bg-green-50/80 border border-green-200 rounded-xl p-4 flex items-start gap-2">
                    <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm text-green-800 leading-relaxed">
                      任务已完成，正在加载结果...
                    </p>
                  </div>
                    )}
                  </>
                )}

                {(taskDetails?.status || result.status) !== "completed" && (
                  <div className="bg-blue-50/80 border border-blue-200 rounded-xl p-4 flex items-start gap-2">
                    <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm text-blue-800 leading-relaxed">
                      任务正在处理中，请稍候...任务完成后将自动加载结果。
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

      {/* Create Dataset Modal */}
      {showCreateDatasetModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">创建数据集</h3>
            <div className="space-y-4">
              <div>
                <label className={labelClass}>
                  <span>数据集名称</span>
                  <span className="text-red-500">*</span>
                </label>
                <input
                  className={baseFieldClass}
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  placeholder="请输入数据集名称"
                  required
                />
              </div>
              <div>
                <label className={labelClass}>
                  描述 <span className="text-slate-400 font-normal">(可选)</span>
                </label>
                <textarea
                  className={textAreaClass}
                  rows={3}
                  value={datasetDescription}
                  onChange={(e) => setDatasetDescription(e.target.value)}
                  placeholder="请输入数据集描述"
                />
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={handleCreateDataset}
                  disabled={creatingDataset || !datasetName.trim()}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-medium transition-colors disabled:bg-slate-300 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {creatingDataset && (
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  {creatingDataset ? "创建中..." : "创建"}
                </button>
                <button
                  onClick={() => {
                    setShowCreateDatasetModal(false);
                    setDatasetName("");
                    setDatasetDescription("");
                  }}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Task List */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center justify-between gap-6">
            {/* Left: Title and Search */}
            <div className="flex items-center gap-6">
              <h2 className="text-lg font-bold text-gray-900">任务列表</h2>

              {/* Search Box */}
              <div className="relative w-80">
                <input
                  type="text"
                  placeholder="搜索任务名称..."
                  value={taskSearchQuery}
                  onChange={(e) => {
                    setTaskSearchQuery(e.target.value);
                    setTaskPage(1);
                  }}
                  className="w-full pl-10 pr-10 py-2.5 text-sm border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all"
                />
                <svg className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                {taskSearchQuery && (
                  <button
                    onClick={() => {
                      setTaskSearchQuery("");
                      setTaskPage(1);
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
                  value={taskFilterStatus}
                  onChange={(e) => {
                    setTaskFilterStatus(e.target.value);
                    setTaskPage(1);
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
                  onClick={async () => {
                    if (!window.confirm(`确定要删除选中的 ${selectedTasks.size} 个任务吗？删除后无法恢复！`)) return;
                    try {
                      await Promise.all(Array.from(selectedTasks).map(taskId => deleteTask(taskId)));
                      setSelectedTasks(new Set());
                      // Reload tasks
                      let taskType: TaskType | undefined = undefined;
                      if (activeTab === 'generation') taskType = 'synthesis' as TaskType;
                      else if (activeTab === 'hard_negative') taskType = 'negative_mining' as TaskType;
                      if (taskType) {
                        const data = await getTasks(taskPage, taskPageSize, taskType);
                        setRecentTasks(data.items || []);
                        setTaskTotal(data.total || 0);
                      }
                    } catch (err: any) {
                      alert("批量删除失败：" + (err.response?.data?.detail || err.message));
                    }
                  }}
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
                onClick={() => setShowCreateTaskModal(true)}
                className="px-4 py-2 bg-gradient-to-r from-green-500 to-green-600 text-white text-sm font-medium rounded-lg hover:from-green-600 hover:to-green-700 transition-all flex items-center gap-2 shadow-sm hover:shadow whitespace-nowrap"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                新建任务
              </button>
            </div>
          </div>
        </div>
        {recentLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="flex flex-col items-center gap-3">
              <svg className="animate-spin h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-gray-600">加载中...</span>
            </div>
          </div>
        ) : recentTasks.length === 0 ? (
          <div className="py-16 text-center">
            <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-sm font-medium text-gray-700 mb-2">暂无任务</p>
            <p className="text-sm text-gray-500 mb-4">还没有创建任何任务</p>
            <button
              onClick={() => setShowCreateTaskModal(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors inline-flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              创建第一个任务
            </button>
          </div>
        ) : (() => {
          // Filter tasks by search query and status
          const filteredTasks = recentTasks.filter(task => {
            const matchesSearch = !taskSearchQuery || (task.name && task.name.toLowerCase().includes(taskSearchQuery.toLowerCase()));
            const matchesStatus = !taskFilterStatus || task.status === taskFilterStatus;
            return matchesSearch && matchesStatus;
          });

          return (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left w-12">
                    <input
                      type="checkbox"
                      checked={filteredTasks.length > 0 && selectedTasks.size === filteredTasks.length}
                      onChange={() => {
                        if (selectedTasks.size === filteredTasks.length) {
                          setSelectedTasks(new Set());
                        } else {
                          setSelectedTasks(new Set(filteredTasks.map(t => t.id)));
                        }
                      }}
                      className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500 cursor-pointer"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">任务名称</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">耗时</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">TOKEN/成本</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTasks.map((t) => {
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

                  const formatDate = (dateStr: string) => {
                    return new Date(dateStr).toLocaleString("zh-CN", {
                      month: "2-digit",
                      day: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    });
                  };

                  const statusConfig = getStatusConfig(t.status);
                  const displayName = t.name || `任务 ${t.id.substring(0, 8)}`;

                  return (
                    <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                      {/* Checkbox */}
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedTasks.has(t.id)}
                          onChange={() => {
                            const newSelected = new Set(selectedTasks);
                            if (newSelected.has(t.id)) {
                              newSelected.delete(t.id);
                            } else {
                              newSelected.add(t.id);
                            }
                            setSelectedTasks(newSelected);
                          }}
                          className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500 cursor-pointer"
                        />
                      </td>
                      
                      {/* Task Name */}
                      <td className="px-4 py-3 cursor-pointer" onClick={() => navigate(`/tasks/${t.id}`)}>
                        <div className="text-sm font-medium text-gray-900">
                          {displayName}
                        </div>
                      </td>
                      
                      {/* Status */}
                      <td className="px-4 py-3 cursor-pointer" onClick={() => navigate(`/tasks/${t.id}`)}>
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${statusConfig.dotColor}`}></div>
                          <span className={`text-xs font-semibold ${statusConfig.color}`}>
                            {statusConfig.label}
                          </span>
                        </div>
                      </td>

                      {/* Created At */}
                      <td className="px-4 py-3 cursor-pointer" onClick={() => navigate(`/tasks/${t.id}`)}>
                        <div className="text-sm text-gray-700">
                          {formatDate(t.created_at)}
                        </div>
                      </td>

                      {/* Duration */}
                      <td className="px-4 py-3 cursor-pointer" onClick={() => navigate(`/tasks/${t.id}`)}>
                        <div className="text-sm text-gray-700">
                          {formatDuration(t.started_at, t.completed_at)}
                        </div>
                      </td>

                      {/* Tokens/Cost */}
                      <td className="px-4 py-3 text-right cursor-pointer" onClick={() => navigate(`/tasks/${t.id}`)}>
                        <div className="text-sm text-gray-700">
                          {t.total_tokens > 0 ? t.total_tokens.toLocaleString() : "-"}
                        </div>
                        {t.total_cost && Number(t.total_cost) > 0 && (
                          <div className="text-xs text-gray-500">
                            ${Number(t.total_cost).toFixed(4)}
                          </div>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="inline-flex items-center justify-end gap-1">
                          {/* View Details - Always visible */}
                          <button
                            onClick={() => navigate(`/tasks/${t.id}`)}
                            className="p-1.5 text-gray-600 hover:bg-gray-100 rounded transition-colors"
                            title="查看详情"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                            </svg>
                          </button>

                          {/* Retry - Fixed width placeholder */}
                          {t.status === 'failed' ? (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                try {
                                  await retryTask(t.id);
                                  let taskType: TaskType | undefined = undefined;
                                  if (activeTab === 'generation') taskType = 'synthesis' as TaskType;
                                  else if (activeTab === 'hard_negative') taskType = 'negative_mining' as TaskType;
                                  const data = await getTasks(taskPage, taskPageSize, taskType);
                                  setRecentTasks(data.items || []);
                                  setTaskTotal(data.total || 0);
                                } catch {}
                              }}
                              className="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                              title="重试"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                              </svg>
                            </button>
                          ) : (
                            <div className="w-[28px]"></div>
                          )}

                          {/* Delete - Fixed width placeholder */}
                          {t.status !== 'running' && t.status !== 'pending' ? (
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                if (confirm('确定删除该任务吗？')) {
                                  try {
                                    await deleteTask(t.id);
                                    // Reload tasks
                                    let taskType: TaskType | undefined = undefined;
                                    if (activeTab === 'generation') taskType = 'synthesis' as TaskType;
                                    else if (activeTab === 'hard_negative') taskType = 'negative_mining' as TaskType;
                                    if (taskType) {
                                      const data = await getTasks(taskPage, taskPageSize, taskType);
                                      setRecentTasks(data.items || []);
                                      setTaskTotal(data.total || 0);
                                    }
                                  } catch {}
                                }
                              }}
                              className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                              title="删除"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
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
          );
        })()}
        
        {/* Pagination */}
        {taskTotal > 0 && (
          <Pagination
            page={taskPage}
            pageSize={taskPageSize}
            total={taskTotal}
            onPageChange={(p) => setTaskPage(p)}
            onPageSizeChange={(ps) => {
              setTaskPageSize(ps);
              setTaskPage(1);
            }}
          />
        )}
      </div>

      {/* Result (main panel) */}
      {result && (
        <div className={`${sectionCardClass} mt-6`}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              任务详情
            </h2>
            <span className={`px-3 py-1.5 rounded-xl text-sm font-medium border ${
              (taskDetails?.status || result.status) === "pending" || (taskDetails?.status || result.status) === "running"
                ? "bg-blue-50 text-blue-700 border-blue-200" 
                : (taskDetails?.status || result.status) === "completed"
                ? "bg-green-50 text-green-700 border-green-200"
                : "bg-red-50 text-red-700 border-red-200"
            }`}>
              {(taskDetails?.status || result.status) === "pending" ? "等待中" :
               (taskDetails?.status || result.status) === "running" ? "运行中" :
               (taskDetails?.status || result.status) === "completed" ? "已完成" : 
               (taskDetails?.status || result.status)}
            </span>
          </div>

          <div className="space-y-4">
            <div className="bg-blue-50/80 border border-blue-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                任务信息
              </h3>
              <div className="space-y-2.5 text-sm text-blue-800">
                <div className="flex justify-between items-center">
                  <span className="text-blue-600 font-medium">任务 ID:</span>
                  <code className="font-mono text-xs bg-blue-100 px-2 py-1 rounded">{result.task_id}</code>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-blue-600 font-medium">创建时间:</span>
                  <span>{new Date(result.created_at).toLocaleString("zh-CN")}</span>
                </div>
                {taskDetails && (
                  <>
                    {taskDetails.completed_at && (
                      <div className="flex justify-between items-center">
                        <span className="text-blue-600 font-medium">完成时间:</span>
                        <span>{new Date(taskDetails.completed_at).toLocaleString("zh-CN")}</span>
                      </div>
                    )}
                    {taskDetails.total_tokens > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-blue-600 font-medium">Token 使用量:</span>
                        <span>{taskDetails.total_tokens.toLocaleString()}</span>
                      </div>
                    )}
                    {taskDetails.total_cost > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-blue-600 font-medium">成本:</span>
                        <span>${taskDetails.total_cost.toFixed(4)}</span>
                      </div>
                    )}
                  </>
                )}
                {result.estimated_time && (
                  <div className="flex justify-between items-center">
                    <span className="text-blue-600 font-medium">预计时间:</span>
                    <span>{result.estimated_time} 秒</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

