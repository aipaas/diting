import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getDatasets, uploadDataset, deleteDataset } from "@/api/client";
import type { DatasetResponse } from "@/types/api";
import Pagination from "@/components/Pagination";

/**
 * Format MIME type to friendly display name
 */
function formatFileType(fileType: string | null | undefined): string {
  if (!fileType) return "未知";
  
  const typeMap: Record<string, string> = {
    "text/csv": "CSV",
    "application/x-ndjson": "JSONL",
    "application/jsonl": "JSONL",
    "application/json": "JSON",
    "application/vnd.ms-excel": "Excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
    "text/plain": "TXT",
    "application/octet-stream": "二进制",
  };
  
  // Direct match
  if (typeMap[fileType]) {
    return typeMap[fileType];
  }
  
  // Check if it contains known patterns
  if (fileType.includes("jsonl") || fileType.includes("ndjson")) {
    return "JSONL";
  }
  if (fileType.includes("csv")) {
    return "CSV";
  }
  if (fileType.includes("excel") || fileType.includes("spreadsheet")) {
    return "Excel";
  }
  
  // Return simplified version (remove application/, text/, etc.)
  return fileType.split("/").pop()?.toUpperCase() || fileType;
}

export default function Datasets() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  useEffect(() => {
    fetchDatasets();
  }, [currentPage, pageSize]);

  const fetchDatasets = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getDatasets(currentPage, pageSize);
      setDatasets(data.items);
      setTotal(data.total);
    } catch (err: any) {
      console.error("Failed to fetch datasets:", err);
      setError("获取数据集失败");
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    // 如果使用拖拽上传，需要添加文件
    if (selectedFile) {
      formData.set('file', selectedFile);
    }
    
    try {
      setUploadLoading(true);
      setUploadError("");
      await uploadDataset(formData);
      setShowUploadModal(false);
      fetchDatasets();
      // 重置表单和状态
      (e.currentTarget as HTMLFormElement).reset();
      setSelectedFile(null);
    } catch (err: any) {
      console.error("Failed to upload dataset:", err);
      setUploadError(err.response?.data?.detail || "上传失败");
    } finally {
      setUploadLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadError("");
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      const validTypes = ['.csv', '.json', '.jsonl'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      
      if (validTypes.includes(fileExt)) {
        setSelectedFile(file);
        setUploadError("");
      } else {
        setUploadError("不支持的文件格式，请上传 CSV、JSON 或 JSONL 文件");
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const resetUploadModal = () => {
    setShowUploadModal(false);
    setUploadError("");
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (datasetId: string) => {
    if (!confirm("确定要删除这个数据集吗？")) return;
    
    try {
      await deleteDataset(datasetId);
      fetchDatasets();
    } catch (err: any) {
      console.error("Failed to delete dataset:", err);
      alert("删除失败：" + (err.response?.data?.detail || err.message));
    }
  };

  const filteredDatasets = datasets.filter(dataset => {
    const matchesSearch = 
      dataset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (dataset.description?.toLowerCase() || "").includes(searchQuery.toLowerCase());
    
    return matchesSearch;
  });

  const formatFileSizeDisplay = (bytes: number | null) => {
    if (!bytes) return "0 B";
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto space-y-5">
        <div className="flex items-center justify-center h-96">
          <div className="flex flex-col items-center gap-3">
            <svg className="animate-spin h-10 w-10 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="text-gray-600">加载中...</span>
          </div>
        </div>
      </div>
    );
  }

  const getFileTypeColor = (fileType: string | null | undefined) => {
    const type = formatFileType(fileType);
    if (type === "JSONL") return "bg-purple-50 text-purple-600 border-purple-200";
    if (type === "CSV") return "bg-emerald-50 text-emerald-600 border-emerald-200";
    if (type === "Excel") return "bg-green-50 text-green-600 border-green-200";
    if (type === "JSON") return "bg-blue-50 text-blue-600 border-blue-200";
    return "bg-gray-50 text-gray-600 border-gray-200";
  };

  return (
    <div className="max-w-[1600px] mx-auto space-y-4 px-4 py-3">
      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* Datasets Grid Container */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* Header Bar */}
        <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center justify-between gap-4">
            {/* Left: Title and Search */}
            <div className="flex items-center gap-6">
              <h2 className="text-lg font-bold text-gray-900">
                数据集
              </h2>

              {/* Search Box */}
              <div className="relative w-80">
                <input
                  type="text"
                  placeholder="搜索数据集..."
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

            {/* Right: Upload Button */}
            <div className="flex items-center gap-3">
              <button 
                onClick={() => setShowUploadModal(true)}
                className="px-4 py-2 bg-gradient-to-r from-brand-500 to-violet-500 text-white text-sm font-medium rounded-lg hover:from-brand-600 hover:to-violet-600 transition-all flex items-center gap-2 shadow-sm hover:shadow whitespace-nowrap"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                </svg>
                上传数据集
              </button>
            </div>
          </div>
        </div>

        {/* Content - Grid or Empty State */}
        {filteredDatasets.length > 0 ? (
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredDatasets.map((dataset) => (
              <div 
                key={dataset.id} 
                className="bg-white border border-gray-200 rounded-lg p-4 hover:border-gray-300 hover:shadow-sm transition-all cursor-pointer"
                onClick={() => navigate(`/datasets/${dataset.id}`)}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <h3 className="text-sm font-semibold text-gray-900 truncate">
                        {dataset.name}
                      </h3>
                    </div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getFileTypeColor(dataset.file_type)}`}>
                        {formatFileType(dataset.file_type)}
                      </span>
                    </div>
                    {dataset.description && (
                      <p className="text-xs text-gray-500 line-clamp-2">{dataset.description}</p>
                    )}
                  </div>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(dataset.id);
                    }}
                    className="ml-2 p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="删除数据集"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-3 py-3 border-t border-gray-100">
                  <div>
                    <div className="text-xs text-gray-500 mb-0.5">大小</div>
                    <div className="text-sm font-semibold text-gray-900">{formatFileSizeDisplay(dataset.file_size)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-0.5">记录数</div>
                    <div className="text-sm font-semibold text-gray-900">{dataset.row_count.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-0.5">列数</div>
                    <div className="text-sm font-semibold text-gray-900">
                      {dataset.columns?.columns?.length || 0}
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <div>{new Date(dataset.updated_at).toLocaleDateString("zh-CN")}</div>
                    {dataset.creator && (
                      <>
                        <span>•</span>
                        <div className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                          <span>{dataset.creator.username}</span>
                        </div>
                      </>
                    )}
                  </div>
                  <div className="text-gray-600 hover:text-gray-900 text-xs font-medium flex items-center gap-1 transition-colors">
                    <span>查看</span>
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            ))}
            </div>

            {/* Pagination */}
            {total > pageSize && (
              <div className="border-t border-gray-200 mt-4">
                <Pagination
                  page={currentPage}
                  pageSize={pageSize}
                  total={total}
                  onPageChange={setCurrentPage}
                  onPageSizeChange={(newPageSize) => {
                    setPageSize(newPageSize);
                    setCurrentPage(1);
                  }}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="p-12 text-center">
            <svg className="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <h3 className="text-base font-semibold text-gray-900 mb-1">没有找到数据集</h3>
            <p className="text-sm text-gray-500 mb-4">
              {searchQuery ? "尝试调整搜索条件" : "上传你的第一个数据集"}
            </p>
            {!searchQuery && (
              <button 
                onClick={() => setShowUploadModal(true)}
                className="px-4 py-2 bg-gradient-to-r from-brand-500 to-violet-500 text-white text-sm font-medium rounded-lg hover:from-brand-600 hover:to-violet-600 transition-all inline-flex items-center gap-2 shadow-sm hover:shadow"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                </svg>
                上传数据集
              </button>
            )}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900">上传数据集</h3>
              <button
                onClick={resetUploadModal}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleUpload} className="space-y-4">
              {/* Error Message */}
              {uploadError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {uploadError}
                </div>
              )}

              {/* Dataset Name */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>数据集名称</span>
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300"
                  placeholder="请输入数据集名称"
                />
              </div>

              {/* Description */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>描述</span>
                  <span className="text-slate-400 font-normal">(可选)</span>
                </label>
                <textarea
                  name="description"
                  rows={3}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-sm transition-all duration-200 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:shadow-md placeholder:text-slate-400 hover:border-slate-300 resize-none leading-relaxed"
                  placeholder="简要描述该数据集的用途、来源或特点..."
                />
              </div>

              {/* File Upload Area */}
              <div>
                <label className="mb-2 text-sm font-medium text-slate-700 flex items-center gap-1.5">
                  <span>选择文件</span>
                  <span className="text-red-500">*</span>
                </label>
                
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`relative border border-dashed rounded-xl transition-all duration-200 ${
                    isDragging
                      ? 'border-brand-500 bg-brand-50'
                      : selectedFile
                      ? 'border-green-300 bg-green-50'
                      : 'border-slate-300 bg-slate-50 hover:border-slate-400'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    name="file"
                    required={!selectedFile}
                    accept=".csv,.json,.jsonl"
                    onChange={handleFileChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  />
                  
                  {!selectedFile ? (
                    <div className="px-4 py-12 text-center">
                      <svg className="w-12 h-12 mx-auto mb-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <p className="text-sm font-medium text-slate-700 mb-1">
                        {isDragging ? '放开以上传文件' : '拖拽文件到此处，或点击选择'}
                      </p>
                      <p className="text-xs text-slate-500">支持 CSV、JSON 和 JSONL 格式</p>
                    </div>
                  ) : (
                    <div className="px-4 py-4">
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                          <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-900 truncate">{selectedFile.name}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{formatFileSize(selectedFile.size)}</p>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedFile(null);
                            if (fileInputRef.current) {
                              fileInputRef.current.value = "";
                            }
                          }}
                          className="flex-shrink-0 text-slate-400 hover:text-red-600 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <p className="text-xs text-slate-500 mt-2">
                  文件大小建议不超过 100MB，数据量过大可能影响上传速度
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={resetUploadModal}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition-colors"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={uploadLoading || !selectedFile}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-medium transition-colors disabled:bg-slate-300 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {uploadLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>上传中...</span>
                    </>
                  ) : (
                    <span>开始上传</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

