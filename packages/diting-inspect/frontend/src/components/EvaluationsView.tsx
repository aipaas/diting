import { Eye, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "../constants";
import type { EvaluationType } from "../types/Evaluations";
import EvaluationReportModal from "./EvaluationReportModal";

interface EvaluationsViewProps {
	evaluations: EvaluationType[];
	onRefresh: () => void;
	showNotification: (
		message: string,
		type?: "info" | "success" | "error",
	) => void;
}

const EvaluationsView = ({
	evaluations,
	onRefresh,
	showNotification,
}: EvaluationsViewProps) => {
	const [searchTerm, setSearchTerm] = useState<string>("");
	const [selectedEvaluations, setSelectedEvaluations] = useState<string[]>([]);
	const [autoRefreshInterval, setAutoRefreshInterval] = useState<number | null>(
		null,
	);
	const [selectedEvaluation, setSelectedEvaluation] =
		useState<EvaluationType | null>(null); // 新增状态管理
	const [isModalOpen, setIsModalOpen] = useState<boolean>(false); // 控制模态框的打开和关闭

	const filteredEvaluations = evaluations.filter(
		(eval_) =>
			eval_.id.toString().includes(searchTerm) ||
			eval_.status.toLowerCase().includes(searchTerm.toLowerCase()),
	);

	const handleSelectEvaluation = (id: string) => {
		if (selectedEvaluations.includes(id)) {
			setSelectedEvaluations(
				selectedEvaluations.filter((selectedId) => selectedId !== id),
			);
		} else {
			setSelectedEvaluations([...selectedEvaluations, id]);
		}
	};

	const handleDeleteSelected = async () => {
		try {
			await Promise.all(
				selectedEvaluations.map(async (id) => {
					const response = await fetch(`${API_BASE}/evaluations/${id}`, {
						method: "DELETE",
					});
					if (!response.ok) {
						throw new Error(`Failed to delete evaluation with ID: ${id}`);
					}
				}),
			);
			showNotification("Selected evaluations deleted successfully!", "success");
			setSelectedEvaluations([]);
			onRefresh(); // Refresh the evaluations after deletion
		} catch (error) {
			showNotification(error.message, "error");
		}
	};

	useEffect(() => {
		if (autoRefreshInterval) {
			const intervalId = setInterval(() => {
				onRefresh();
			}, autoRefreshInterval);
			return () => clearInterval(intervalId);
		}
	}, [autoRefreshInterval, onRefresh]);

	const handleAutoRefreshChange = (
		event: React.ChangeEvent<HTMLSelectElement>,
	) => {
		const value = event.target.value;
		setAutoRefreshInterval(value === "no" ? null : parseInt(value) * 1000);
	};

	const handleViewReport = (eval_) => {
		setSelectedEvaluation(eval_); // 设置选中的评估
		setIsModalOpen(true); // 打开模态框
	};

	const closeModal = () => {
		setIsModalOpen(false); // 关闭模态框
		setSelectedEvaluation(null); // 清空选中的评估
	};

	return (
		<div>
			{/* Search and Actions Bar */}
			<div className="flex items-center justify-between mb-4">
				<div className="relative">
					<Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
					<input
						type="text"
						placeholder="Search evaluations..."
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
						className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div className="flex items-center space-x-2">
					<select
						onChange={handleAutoRefreshChange}
						className="border border-gray-300 rounded-lg p-2"
					>
						<option value="no">No Auto Refresh</option>
						<option value="1">1 Second</option>
						<option value="5">5 Seconds</option>
						<option value="10">10 Seconds</option>
					</select>
					<button
						type="button"
						onClick={handleDeleteSelected}
						disabled={selectedEvaluations.length === 0}
						className={`inline-flex items-center px-4 py-2 rounded-lg ${
							selectedEvaluations.length > 0
								? "bg-red-600 text-white hover:bg-red-700"
								: "bg-gray-300 text-gray-500 cursor-not-allowed"
						}`}
					>
						<Trash2 className="w-5 h-5 mr-2" />
						Delete
					</button>
				</div>
			</div>

			{/* Evaluations Table */}
			<div className="bg-white shadow rounded-lg overflow-hidden">
				<table className="min-w-full divide-y divide-gray-200">
					<thead className="bg-gray-50">
						<tr>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								<input
									type="checkbox"
									checked={
										selectedEvaluations.length === filteredEvaluations.length &&
										filteredEvaluations.length > 0
									}
									onChange={() => {
										if (
											selectedEvaluations.length === filteredEvaluations.length
										) {
											setSelectedEvaluations([]);
										} else {
											setSelectedEvaluations(
												filteredEvaluations.map((eval_) => eval_.id),
											);
										}
									}}
								/>
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								ID
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Status
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Started At
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Completed At
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Actions
							</th>
						</tr>
					</thead>
					<tbody className="bg-white divide-y divide-gray-200">
						{filteredEvaluations.length > 0 ? (
							filteredEvaluations.map((eval_) => (
								<tr key={eval_.id}>
									<td className="px-6 py-4 whitespace-nowrap">
										<input
											type="checkbox"
											checked={selectedEvaluations.includes(eval_.id)}
											onChange={() => handleSelectEvaluation(eval_.id)}
										/>
									</td>
									<td className="px-6 py-4 whitespace-nowrap">{eval_.id}</td>
									<td className="px-6 py-4 whitespace-nowrap">
										{eval_.status}
									</td>
									<td className="px-6 py-4 whitespace-nowrap">
										{new Date(eval_.started_at).toLocaleString()}
									</td>
									<td className="px-6 py-4 whitespace-nowrap">
										{eval_.completed_at
											? new Date(eval_.completed_at).toLocaleString()
											: "N/A"}
									</td>
									<td className="px-6 py-4 whitespace-nowrap">
										<button
											type="button"
											className="text-blue-600 hover:text-blue-800"
											onClick={() => handleViewReport(eval_)} // 点击时打开模态框
										>
											<Eye className="w-5 h-5" />
										</button>
									</td>
								</tr>
							))
						) : (
							<tr>
								<td colSpan="6" className="text-center py-4">
									No evaluations found.
								</td>
							</tr>
						)}
					</tbody>
				</table>
			</div>

			{/* 模态框 */}
			<EvaluationReportModal
				isOpen={isModalOpen}
				onClose={closeModal}
				evaluation={selectedEvaluation}
			/>
		</div>
	);
};

export default EvaluationsView;
