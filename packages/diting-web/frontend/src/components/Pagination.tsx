
type PaginationProps = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  pageSizeOptions?: number[];
  className?: string;
};

export default function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [5, 10, 20, 50, 100],
  className = "",
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(1, pageSize)));
  const currentPage = Math.min(Math.max(1, page), totalPages);

  const buildVisiblePages = () => {
    const pages: (number | "ellipsis")[] = [];
    const maxVisible = 5;

    let start = Math.max(1, currentPage - 2);
    let end = Math.min(totalPages, currentPage + 2);

    if (currentPage <= 3) end = Math.min(totalPages, maxVisible);
    if (currentPage >= totalPages - 2) start = Math.max(1, totalPages - (maxVisible - 1));

    if (start > 1) {
      pages.push(1);
      if (start > 2) pages.push("ellipsis");
    }

    for (let i = start; i <= end; i++) pages.push(i);

    if (end < totalPages) {
      if (end < totalPages - 1) pages.push("ellipsis");
      pages.push(totalPages);
    }

    return pages;
  };

  const from = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const to = Math.min(currentPage * pageSize, total);

  return (
    <div className={`px-6 py-3 border-t border-gray-200 bg-white ${className}`}>
      <div className="flex items-center justify-between">
        {/* Left: Stats */}
        <div className="text-sm text-gray-600">
          显示第 <span className="font-semibold text-gray-900">{from}</span> - <span className="font-semibold text-gray-900">{to}</span> 条，共 <span className="font-semibold text-gray-900">{total}</span> 条
        </div>

        {/* Center: Page Navigation */}
        {totalPages > 1 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white transition-colors"
            >
              上一页
            </button>

            <div className="flex items-center gap-1 mx-2">
              {buildVisiblePages().map((p, idx) =>
                p === "ellipsis" ? (
                  <span key={`e-${idx}`} className="px-1 text-gray-400">•••</span>
                ) : (
                  <button
                    key={p}
                    onClick={() => onPageChange(p)}
                    className={`min-w-[36px] h-9 px-3 text-sm font-medium rounded-md transition-colors ${
                      p === currentPage
                        ? "bg-brand-600 text-white border border-brand-600"
                        : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {p}
                  </button>
                )
              )}
            </div>

            <button
              onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage >= totalPages}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white transition-colors"
            >
              下一页
            </button>
          </div>
        )}

        {/* Right: Page Size */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 whitespace-nowrap">每页显示</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
            className="pl-3 pr-8 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 cursor-pointer transition-colors"
          >
            {pageSizeOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          <span className="text-sm text-gray-600 whitespace-nowrap">条</span>
        </div>
      </div>
    </div>
  );
}


