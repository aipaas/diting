import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import type { ReactNode } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getDataset, previewDataset, updateDatasetRow, deleteDatasetRow, addAnnotationColumn, updateAnnotationColumn, deleteAnnotationColumn, exportDataset, getDatasetDownloadUrl } from "@/api/client";
import type { DatasetResponse, DatasetPreviewResponse, AnnotationColumn } from "@/types/api";

export default function DatasetDetail() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  
  const [dataset, setDataset] = useState<DatasetResponse | null>(null);
  const [previewData, setPreviewData] = useState<DatasetPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null);
  const [editedData, setEditedData] = useState<any>({});
  const [isEditing, setIsEditing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(20);
  const [showAnnotationModal, setShowAnnotationModal] = useState(false);
  const [newColumnName, setNewColumnName] = useState("");
  const [newColumnType, setNewColumnType] = useState("text");
  const [newColumnDescription, setNewColumnDescription] = useState("");
  const [editingColumn, setEditingColumn] = useState<string | null>(null);
  const [editColumnName, setEditColumnName] = useState("");
  const [editColumnType, setEditColumnType] = useState("");
  const [editColumnDescription, setEditColumnDescription] = useState("");
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Define fetchDatasetDetails before useEffect to avoid initialization error
  const fetchDatasetDetails = useCallback(async () => {
    if (!datasetId) return;
    
    try {
      setLoading(true);
      setError("");
      const [datasetData, previewDataResponse] = await Promise.all([
        getDataset(datasetId),
        previewDataset(datasetId, currentPage, itemsPerPage, debouncedSearchQuery || undefined)
      ]);
      setDataset(datasetData);
      setPreviewData(previewDataResponse);
    } catch (err: any) {
      console.error("Failed to fetch dataset details:", err);
      setError("获取数据集详情失败");
    } finally {
      setLoading(false);
    }
  }, [datasetId, currentPage, itemsPerPage, debouncedSearchQuery]);

  // Debounce search query to avoid excessive API calls
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    searchTimeoutRef.current = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
      setCurrentPage(1); // Reset to first page on search
    }, 500); // 500ms debounce delay

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery]);

  useEffect(() => {
    if (datasetId) {
      fetchDatasetDetails();
    }
  }, [datasetId, fetchDatasetDetails]);

  // Helper function to format cell value for display (memoized)
  const formatCellValue = useCallback((value: any): string => {
    if (value === null || value === undefined) {
      return "";
    }
    if (Array.isArray(value)) {
      // For arrays, join with newlines for better readability
      return value.join("\n");
    }
    if (typeof value === "object") {
      // For objects, stringify with formatting
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  }, []);

  // Helper function to render cell value with proper formatting (memoized)
  const renderCellValue = useCallback((value: any): ReactNode => {
    if (value === null || value === undefined || value === "") {
      return <span className="text-gray-400 italic">空</span>;
    }
    if (Array.isArray(value)) {
      // Render array as a list
      return (
        <div className="space-y-1">
          {value.map((item: any, index: number) => (
            <div key={index} className="text-sm text-gray-900 bg-gray-50 px-2 py-1 rounded border border-gray-200">
              {typeof item === "object" ? JSON.stringify(item, null, 2) : String(item)}
            </div>
          ))}
        </div>
      );
    }
    if (typeof value === "object") {
      // Render object as formatted JSON
      return (
        <pre className="text-sm text-gray-900 whitespace-pre-wrap bg-gray-50 px-2 py-1 rounded border border-gray-200">
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }
    return <span className="text-sm text-gray-900">{String(value)}</span>;
  }, []);

  // Memoize filtered data to avoid recalculating on every render
  const filteredData = useMemo(() => {
    return previewData?.preview_data || [];
  }, [previewData?.preview_data]);

  // 当分页数据更新后，如果有待打开的行，则打开它
  useEffect(() => {
    if (selectedRowIndex !== null && filteredData.length > 0 && filteredData[selectedRowIndex]) {
      setEditedData({ ...filteredData[selectedRowIndex] });
    }
  }, [filteredData, selectedRowIndex]);

  const handleOpenDetail = useCallback((rowIndex: number) => {
    // rowIndex is the index within the current page's data (0-19)
    setSelectedRowIndex(rowIndex);
    setEditedData({ ...filteredData[rowIndex] });
    setIsEditing(false);
  }, [filteredData]);

  const handleCloseDetail = () => {
    setSelectedRowIndex(null);
    setEditedData({});
    setIsEditing(false);
  };

  const handleStartEdit = () => {
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!previewData || !datasetId || selectedRowIndex === null) return;
    
    try {
      // 从数据中获取实际的 row_index
      const actualRowIndex = filteredData[selectedRowIndex]?.__row_index__;
      if (actualRowIndex === undefined) {
        alert("无法获取行索引，请刷新页面后重试");
        return;
      }
      
      // 移除内部字段 __row_index__
      const { __row_index__, ...dataToSave } = editedData;
      
      // 调用单行更新API
      await updateDatasetRow(datasetId, actualRowIndex, dataToSave);
      
      // 重新获取数据，确保同步
      await fetchDatasetDetails();
      
      setIsEditing(false);
      // 保存后不再自动跳转，保持在当前项
    } catch (err: any) {
      console.error("Failed to save data:", err);
      alert("保存失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleCancel = () => {
    if (selectedRowIndex !== null) {
      setEditedData({ ...filteredData[selectedRowIndex] });
    }
    setIsEditing(false);
  };

  const handleChange = (column: string, value: any) => {
    setEditedData({
      ...editedData,
      [column]: value
    });
  };

  const handlePrevious = () => {
    if (selectedRowIndex !== null) {
      if (selectedRowIndex > 0) {
        // 当前页还有上一条
        const newIndex = selectedRowIndex - 1;
        setSelectedRowIndex(newIndex);
        setEditedData({ ...filteredData[newIndex] });
        setIsEditing(false);
      } else if (currentPage > 1) {
        // 当前页第一条，但还有上一页，跳转到上一页最后一条
        setCurrentPage(currentPage - 1);
        // 延迟一下让数据加载完成后再打开详情
        setTimeout(() => {
          setSelectedRowIndex(itemsPerPage - 1); // 上一页的最后一条
        }, 300);
      }
    }
  };

  const handleNext = () => {
    if (selectedRowIndex !== null) {
      if (selectedRowIndex < filteredData.length - 1) {
        // 当前页还有下一条
        const newIndex = selectedRowIndex + 1;
        setSelectedRowIndex(newIndex);
        setEditedData({ ...filteredData[newIndex] });
        setIsEditing(false);
      } else {
        // 当前页最后一条，检查是否还有下一页
        const totalRows = previewData?.row_count || 0;
        const totalPages = Math.ceil(totalRows / itemsPerPage);
        if (currentPage < totalPages) {
          // 还有下一页，跳转到下一页第一条
          setCurrentPage(currentPage + 1);
          setTimeout(() => {
            setSelectedRowIndex(0);
          }, 300);
        }
      }
    }
  };

  const handleDelete = async () => {
    if (!confirm("确定要删除这条数据吗？")) return;
    
    if (!previewData || !datasetId || selectedRowIndex === null) return;
    
    try {
      // 从数据中获取实际的 row_index
      const actualRowIndex = filteredData[selectedRowIndex]?.__row_index__;
      if (actualRowIndex === undefined) {
        alert("无法获取行索引，请刷新页面后重试");
        return;
      }
      
      // 调用单行删除API
      await deleteDatasetRow(datasetId, actualRowIndex);
      
      // 关闭详情面板
      handleCloseDetail();
      
      // 重新从后端获取数据，确保前后端同步
      await fetchDatasetDetails();
    } catch (err: any) {
      console.error("Failed to delete data:", err);
      alert("删除失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const formatFileSizeDisplay = (bytes: number | null) => {
    if (!bytes) return "0 B";
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  };

  const handleAddAnnotationColumn = async () => {
    if (!datasetId || !newColumnName.trim()) {
      alert("请输入列名");
      return;
    }

    try {
      await addAnnotationColumn(datasetId, {
        column_name: newColumnName.trim(),
        column_type: newColumnType,
        description: newColumnDescription || undefined,
      });
      
      // 显示成功提示
      alert(`列 "${newColumnName.trim()}" 添加成功！`);
      
      // 重置表单
      setNewColumnName("");
      setNewColumnType("text");
      setNewColumnDescription("");
      
      // 刷新数据而不是整页刷新
      await fetchDatasetDetails();
    } catch (err: any) {
      console.error("Failed to add annotation column:", err);
      alert("添加标注列失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleStartEditColumn = (col: {column_name: string; column_type: string; description?: string}) => {
    setEditingColumn(col.column_name);
    setEditColumnName(col.column_name);
    setEditColumnType(col.column_type);
    setEditColumnDescription(col.description || "");
  };

  const handleCancelEditColumn = () => {
    setEditingColumn(null);
    setEditColumnName("");
    setEditColumnType("");
    setEditColumnDescription("");
  };

  const handleSaveEditColumn = async (oldColumnName: string) => {
    if (!datasetId || !editColumnName.trim()) {
      alert("请输入列名");
      return;
    }

    try {
      await updateAnnotationColumn(datasetId, {
        old_column_name: oldColumnName,
        new_column_name: editColumnName.trim(),
        column_type: editColumnType,
        description: editColumnDescription || undefined,
      });
      
      alert(`列 "${editColumnName.trim()}" 更新成功！`);
      
      // 重置编辑状态
      setEditingColumn(null);
      setEditColumnName("");
      setEditColumnType("");
      setEditColumnDescription("");
      
      // 刷新数据而不是整页刷新
      await fetchDatasetDetails();
    } catch (err: any) {
      console.error("Failed to update annotation column:", err);
      alert("更新标注列失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleDeleteAnnotationColumn = async (columnName: string) => {
    if (!confirm(`确定要删除列 "${columnName}" 吗？这将删除该列在所有数据中的值，且不可恢复。`)) return;
    
    if (!datasetId) return;

    try {
      await deleteAnnotationColumn(datasetId, { column_name: columnName });
      
      alert(`列 "${columnName}" 删除成功！`);
      
      // 刷新数据而不是整页刷新
      await fetchDatasetDetails();
    } catch (err: any) {
      console.error("Failed to delete annotation column:", err);
      alert("删除标注列失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const getAnnotationColumns = (): AnnotationColumn[] => {
    return dataset?.metadata?.annotation_columns || [];
  };

  const isAnnotationColumn = (columnName: string): boolean => {
    return getAnnotationColumns().some(col => col.column_name === columnName);
  };

  // 获取所有列（原始列 + 标注列）
  const getAllColumns = (): Array<{column_name: string; column_type: string; description?: string; isOriginal: boolean}> => {
    const allCols: Array<{column_name: string; column_type: string; description?: string; isOriginal: boolean}> = [];
    
    // 添加原始列
    const originalColumns = previewData?.columns || [];
    const dataTypes = previewData?.data_types || {};
    const annotationColumnNames = getAnnotationColumns().map(c => c.column_name);
    
    originalColumns.forEach(colName => {
      if (!annotationColumnNames.includes(colName)) {
        allCols.push({
          column_name: colName,
          column_type: dataTypes[colName] || 'string',
          description: '原始数据列',
          isOriginal: true,
        });
      }
    });
    
    // 添加标注列
    getAnnotationColumns().forEach(col => {
      allCols.push({
        column_name: col.column_name,
        column_type: col.column_type,
        description: col.description || undefined,
        isOriginal: false,
      });
    });
    
    return allCols;
  };

  const handleExportDataset = async (format: 'csv' | 'jsonl' = 'csv') => {
    if (!datasetId) return;
    
    try {
      await exportDataset(datasetId, format);
    } catch (err: any) {
      console.error("Failed to export dataset:", err);
      alert("导出数据集失败：" + (err.response?.data?.msg || err.message));
    }
  };

  const handleDownloadOriginal = async () => {
    if (!datasetId) return;
    
    try {
      const url = await getDatasetDownloadUrl(datasetId);
      window.open(url, "_blank");
    } catch (err: any) {
      console.error("Failed to download original file:", err);
      alert("下载原始文件失败：" + (err.response?.data?.msg || err.message));
    }
  };

  // Pagination info (from server response) - memoized for performance
  const paginationInfo = useMemo(() => {
    const totalRows = previewData?.row_count || 0;
    const totalPages = Math.ceil(totalRows / itemsPerPage);
    const paginatedData = filteredData;
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + paginatedData.length, totalRows);
    return { totalRows, totalPages, paginatedData, startIndex, endIndex };
  }, [previewData?.row_count, filteredData, currentPage, itemsPerPage]);
  
  const { totalRows, totalPages, paginatedData, startIndex, endIndex } = paginationInfo;

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

  if (error || !dataset || !previewData) {
    return (
      <div className="max-w-7xl mx-auto space-y-5">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || "数据集不存在"}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] mx-auto space-y-3 px-4 py-2">
      {/* Compact Header with Stats */}
      <div className="bg-white rounded-lg border border-gray-200 p-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/datasets")}
              className="btn btn-ghost btn-xs btn-circle"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="text-base font-bold text-gray-900">{dataset.name}</h1>
          </div>
          <div className="flex items-center gap-12">
            {/* 统计信息 */}
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-bold text-gray-900">{previewData.row_count.toLocaleString()}</div>
                  <div className="text-xs text-gray-500">条记录</div>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
                  <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-bold text-gray-900">{previewData.column_count}</div>
                  <div className="text-xs text-gray-500">列</div>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                  <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-bold text-gray-900">{formatFileSizeDisplay(dataset.file_size)}</div>
                  <div className="text-xs text-gray-500">文件大小</div>
                </div>
              </div>
            </div>
            
            {/* 操作按钮 */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleDownloadOriginal}
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-lg border border-gray-200 hover:border-gray-300 transition-all"
                title="下载MinIO中的原始文件"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                </svg>
                原始文件
              </button>
              
              <div className="dropdown dropdown-end">
                <button
                  tabIndex={0}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-gradient-to-r from-brand-500 to-violet-500 hover:from-brand-600 hover:to-violet-600 rounded-lg shadow-sm hover:shadow transition-all"
                  title="导出PostgreSQL中的当前数据（包含编辑）"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  导出数据
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <ul tabIndex={0} className="dropdown-content z-[1] menu p-2 shadow-lg bg-white rounded-lg w-40 border border-gray-200 mt-2">
                  <li>
                    <a onClick={() => handleExportDataset('csv')} className="text-sm hover:bg-brand-50 hover:text-brand-600">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      导出为 CSV
                    </a>
                  </li>
                  <li>
                    <a onClick={() => handleExportDataset('jsonl')} className="text-sm hover:bg-brand-50 hover:text-brand-600">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                      导出为 JSONL
                    </a>
                  </li>
                </ul>
              </div>
              
              <button
                onClick={() => setShowAnnotationModal(true)}
                className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 rounded-lg shadow-sm hover:shadow transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                管理列
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Data Cards */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* Search Bar */}
        <div className="px-4 py-2.5 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <input
                type="text"
                placeholder="搜索数据... (输入后自动搜索)"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  // Note: currentPage reset is handled by debounce effect
                }}
                className="input input-sm input-bordered w-full pl-9 pr-4 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setCurrentPage(1);
                }}
                className="ml-2 text-xs text-gray-500 hover:text-gray-700"
              >
                清除
              </button>
            )}
          </div>
        </div>

        {/* Card List */}
        <div className="divide-y divide-gray-100">
          {paginatedData.map((row, rowIndex) => {
            const actualRowIndex = startIndex + rowIndex;
            return (
              <div
                key={actualRowIndex}
                onClick={() => handleOpenDetail(rowIndex)}
                className="group px-4 py-2.5 hover:bg-gradient-to-r hover:from-blue-50 hover:to-transparent cursor-pointer transition-all duration-200 border-l-2 border-transparent hover:border-blue-500"
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Index Badge */}
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-7 h-7 rounded-full bg-gray-100 group-hover:bg-blue-100 flex items-center justify-center transition-colors">
                      <span className="text-xs font-semibold text-gray-600 group-hover:text-blue-600">
                        {actualRowIndex + 1}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2">
                      {previewData.columns.slice(0, 3).map((column) => (
                        <div key={column} className="flex flex-col">
                          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-0.5">
                            {column}
                          </span>
                          <div className="text-sm text-gray-900 font-medium truncate" title={formatCellValue(row[column])}>
                            {Array.isArray(row[column]) ? (
                              <span className="text-blue-600">{`[${row[column].length}项]`}</span>
                            ) : row[column] !== null && row[column] !== undefined && row[column] !== "" ? (
                              String(row[column])
                            ) : (
                              <span className="text-gray-400 italic">空</span>
                            )}
                          </div>
                        </div>
                      ))}
                      {/* overflow indicator moved to right-side ellipsis */}
                    </div>
                    {/* overflow indicator is rendered at the far right */}
                  </div>

                  {/* Right-side indicators: overflow ellipsis + arrow */}
                  <div className="flex-shrink-0 mt-2 flex items-center gap-2">
                    {previewData.columns.length > 3 && (
                      <span
                        className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-gray-500 border border-gray-200"
                        title={`还有 ${previewData.columns.length - 3} 个字段`}
                      >
                        ...
                      </span>
                    )}
                    <svg className="w-5 h-5 text-gray-300 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-3 py-2 border-t border-gray-200 bg-gray-50">
            <div className="text-xs text-gray-600">
              显示 {startIndex + 1}-{endIndex} / 共 {totalRows} 条
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="btn btn-xs btn-ghost disabled:opacity-50 h-6 min-h-0 px-2"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span className="text-xs text-gray-600">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="btn btn-xs btn-ghost disabled:opacity-50 h-6 min-h-0 px-2"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {paginatedData.length === 0 && (
          <div className="text-center py-16 px-4">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-gray-900 mb-2">没有找到数据</h3>
            <p className="text-gray-500 text-sm mb-4">
              {searchQuery ? `没有匹配 "${searchQuery}" 的数据` : "数据集为空"}
            </p>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="btn btn-sm btn-primary"
              >
                清除搜索
              </button>
            )}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedRowIndex !== null && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 px-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col animate-in slide-in-from-bottom-4 duration-300 overflow-hidden border border-gray-200">
            {/* Modern Header with Gradient */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-brand-50 to-violet-50">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg shadow-sm border border-brand-200">
                  <span className="text-sm font-bold text-brand-600">#{startIndex + selectedRowIndex + 1}</span>
                  <span className="text-gray-400">/</span>
                  <span className="text-sm text-gray-600">{totalRows}</span>
                </div>
                {isEditing && (
                  <span className="text-xs px-2 py-1 bg-amber-100 text-amber-700 rounded-md font-medium">
                    编辑模式
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handlePrevious}
                  disabled={selectedRowIndex === 0 && currentPage === 1}
                  className="p-2 hover:bg-white hover:shadow-md rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:shadow-none"
                  title="上一项"
                >
                  <svg className="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <button
                  onClick={handleNext}
                  disabled={selectedRowIndex === filteredData.length - 1 && currentPage === totalPages}
                  className="p-2 hover:bg-white hover:shadow-md rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:shadow-none"
                  title="下一项"
                >
                  <svg className="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <div className="w-px h-6 bg-gray-300 mx-2"></div>
                {isEditing ? (
                  <>
                    <button
                      onClick={handleCancel}
                      className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-white hover:shadow-md rounded-lg transition-all"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSave}
                      className="px-4 py-2 text-sm font-medium bg-gradient-to-r from-brand-500 to-violet-500 text-white hover:from-brand-600 hover:to-violet-600 rounded-lg shadow-md hover:shadow-lg transition-all"
                    >
                      保存
                    </button>
                  </>
                ) : (
                  <button
                    onClick={handleDelete}
                    className="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-all hover:shadow-md flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    删除
                  </button>
                )}
                <div className="w-px h-6 bg-gray-300 mx-2"></div>
                <button
                  onClick={handleCloseDetail}
                  className="p-2 hover:bg-white hover:shadow-md rounded-lg transition-all"
                  title="关闭"
                >
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
              <div className="space-y-3">
                {previewData.columns.map((column) => {
                  const isAnnotation = isAnnotationColumn(column);
                  const annotationCol = isAnnotation ? getAnnotationColumns().find(c => c.column_name === column) : null;
                  
                  return (
                    <div 
                      key={column} 
                      className="group bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all overflow-hidden"
                    >
                      {/* Field Header */}
                      <div className="flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-gray-50 to-white border-b border-gray-100">
                        <div className="flex items-center gap-2 flex-1">
                          <div className="w-1 h-5 rounded-full bg-gradient-to-b from-brand-500 to-violet-500"></div>
                          <span className="text-sm font-bold text-gray-900">{column}</span>
                          <span className="text-xs px-2 py-1 rounded-md bg-brand-100 text-brand-700 font-medium">
                            {isAnnotation ? annotationCol?.column_type : previewData.data_types[column]}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {annotationCol?.description && (
                            <span className="text-xs text-gray-500 italic">{annotationCol.description}</span>
                          )}
                          {!isEditing && (
                            <button
                              onClick={handleStartEdit}
                              className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-brand-50 text-brand-600 rounded-md transition-all"
                              title="点击编辑此字段"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                      
                      {/* Field Content */}
                      <div className="px-4 py-3">
                      {isEditing ? (
                        Array.isArray(editedData[column]) ? (
                          <div className="space-y-2">
                            {editedData[column].map((item: any, index: number) => (
                              <div key={index} className="flex gap-2 items-start">
                                <textarea
                                  value={typeof item === "object" ? JSON.stringify(item, null, 2) : String(item)}
                                  onChange={(e) => {
                                    const newArray = [...editedData[column]];
                                    try {
                                      // Try to parse as JSON if it looks like JSON
                                      newArray[index] = JSON.parse(e.target.value);
                                    } catch {
                                      newArray[index] = e.target.value;
                                    }
                                    handleChange(column, newArray);
                                  }}
                                  rows={2}
                                  className="flex-1 text-sm resize-none rounded-lg px-3 py-2 border border-gray-300 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white transition-all"
                                />
                                <button
                                  onClick={() => {
                                    const newArray = editedData[column].filter((_: any, i: number) => i !== index);
                                    handleChange(column, newArray);
                                  }}
                                  className="mt-1 p-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                                  title="删除此项"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                              </div>
                            ))}
                            <button
                              onClick={() => {
                                handleChange(column, [...editedData[column], ""]);
                              }}
                              className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 px-2 py-1 rounded hover:bg-blue-50 transition-colors"
                            >
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                              </svg>
                              添加项
                            </button>
                          </div>
                        ) : (
                          <textarea
                            value={typeof editedData[column] === "object" && editedData[column] !== null 
                              ? JSON.stringify(editedData[column], null, 2) 
                              : String(editedData[column] ?? "")}
                            onChange={(e) => {
                              try {
                                // Try to parse as JSON if it looks like JSON
                                const parsed = JSON.parse(e.target.value);
                                handleChange(column, parsed);
                              } catch {
                                handleChange(column, e.target.value);
                              }
                            }}
                            rows={3}
                            className="w-full text-sm resize-none rounded-lg px-3 py-2 border border-gray-300 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white transition-all"
                            placeholder=""
                          />
                        )
                      ) : (
                        <div className="text-sm rounded-lg px-1 py-1 min-h-[60px]">
                          {renderCellValue(editedData[column])}
                        </div>
                      )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Annotation Management Modal */}
      {showAnnotationModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-base font-bold text-gray-900">管理数据列</h3>
                  <p className="text-xs text-gray-500">查看、添加、编辑或删除数据列</p>
                </div>
              </div>
              <button
                onClick={() => setShowAnnotationModal(false)}
                className="btn btn-ghost btn-sm btn-circle hover:bg-gray-200"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5">
              {/* Add New Column Form */}
              <div className="bg-gradient-to-br from-blue-50 to-white rounded-xl border-2 border-blue-200 p-5 mb-5">
                <h4 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  添加新列
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs font-medium text-gray-700 mb-1 block">列名 *</label>
                    <input
                      type="text"
                      value={newColumnName}
                      onChange={(e) => setNewColumnName(e.target.value)}
                      placeholder="例如: 情感分类、分类标签等"
                      className="input input-sm input-bordered w-full focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-700 mb-1 block">类型</label>
                    <select
                      value={newColumnType}
                      onChange={(e) => setNewColumnType(e.target.value)}
                      className="select select-sm select-bordered w-full focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="text">文本</option>
                      <option value="number">数字</option>
                      <option value="category">分类</option>
                      <option value="boolean">是/否</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-700 mb-1 block">描述</label>
                    <input
                      type="text"
                      value={newColumnDescription}
                      onChange={(e) => setNewColumnDescription(e.target.value)}
                      placeholder="列的用途说明（可选）"
                      className="input input-sm input-bordered w-full focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <button
                    onClick={handleAddAnnotationColumn}
                    className="btn btn-sm btn-primary w-full gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    添加列
                  </button>
                </div>
              </div>

              {/* All Columns (Original + Annotation) */}
              {getAllColumns().length > 0 && (
                <div>
                  <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                    <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                    </svg>
                    所有列 ({getAllColumns().length})
                  </h4>
                  <div className="space-y-2">
                    {getAllColumns().map((col) => (
                      <div
                        key={col.column_name}
                        className={`p-3 rounded-lg border transition-all ${
                          col.isOriginal 
                            ? 'bg-gray-50 border-gray-300' 
                            : 'bg-white border-gray-200 hover:border-blue-300 hover:shadow-sm'
                        }`}
                      >
                        {editingColumn === col.column_name ? (
                          // 编辑模式
                          <div className="space-y-3">
                            <div>
                              <label className="text-xs font-medium text-gray-700 mb-1 block">列名</label>
                              <input
                                type="text"
                                value={editColumnName}
                                onChange={(e) => setEditColumnName(e.target.value)}
                                className="input input-sm input-bordered w-full focus:ring-2 focus:ring-blue-500"
                                placeholder="列名"
                              />
                            </div>
                            {!col.isOriginal && (
                              <>
                                <div>
                                  <label className="text-xs font-medium text-gray-700 mb-1 block">类型</label>
                                  <select
                                    value={editColumnType}
                                    onChange={(e) => setEditColumnType(e.target.value)}
                                    className="select select-sm select-bordered w-full focus:ring-2 focus:ring-blue-500"
                                  >
                                    <option value="text">文本</option>
                                    <option value="number">数字</option>
                                    <option value="category">分类</option>
                                    <option value="boolean">是/否</option>
                                  </select>
                                </div>
                                <div>
                                  <label className="text-xs font-medium text-gray-700 mb-1 block">描述</label>
                                  <input
                                    type="text"
                                    value={editColumnDescription}
                                    onChange={(e) => setEditColumnDescription(e.target.value)}
                                    className="input input-sm input-bordered w-full focus:ring-2 focus:ring-blue-500"
                                    placeholder="描述（可选）"
                                  />
                                </div>
                              </>
                            )}
                            <div className="flex items-center justify-end gap-2 pt-2">
                              <button
                                onClick={handleCancelEditColumn}
                                className="btn btn-xs btn-ghost gap-1"
                              >
                                取消
                              </button>
                              <button
                                onClick={() => handleSaveEditColumn(col.column_name)}
                                className="btn btn-xs btn-primary gap-1"
                              >
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                                </svg>
                                保存
                              </button>
                            </div>
                          </div>
                        ) : (
                          // 查看模式
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-semibold text-gray-900">{col.column_name}</span>
                                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 border border-gray-200">
                                  {col.column_type}
                                </span>
                              </div>
                              {col.description && (
                                <p className="text-xs text-gray-500 mt-1">{col.description}</p>
                              )}
                            </div>
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleStartEditColumn(col)}
                                className="btn btn-xs btn-ghost text-blue-600 hover:bg-blue-50 gap-1"
                                title="编辑列名"
                              >
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                                编辑
                              </button>
                              <button
                                onClick={() => handleDeleteAnnotationColumn(col.column_name)}
                                className="btn btn-xs btn-ghost text-red-600 hover:bg-red-50 gap-1"
                                title="删除列"
                              >
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                删除
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {getAllColumns().length === 0 && (
                <div className="text-center py-8 px-4 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                  <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                  </svg>
                  <p className="text-sm text-gray-600 font-medium">还没有任何列</p>
                  <p className="text-xs text-gray-500 mt-1">在上方表单中添加第一列</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-5 py-4 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                onClick={() => setShowAnnotationModal(false)}
                className="btn btn-sm btn-primary"
              >
                完成
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

