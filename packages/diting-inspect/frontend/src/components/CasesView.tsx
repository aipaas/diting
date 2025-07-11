import { Download, Edit2, Play, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import * as XLSX from "xlsx";
import { API_BASE } from "../constants";
import type { CaseType } from "../schemas";
import EditCaseModal from "./EditCaseModal";

interface CasesViewProps {
	cases: CaseType[];
	selectedCases: string[];
	setSelectedCases: (cases: string[]) => void;
	searchTerm: string;
	setSearchTerm: (term: string) => void;
	loading: boolean;
	onRefresh: () => Promise<void>;
	onEvaluate: () => void;
	showNotification: (
		message: string,
		type?: "info" | "success" | "error",
	) => void;
}

const CasesView = ({
	cases,
	selectedCases,
	setSelectedCases,
	searchTerm,
	setSearchTerm,
	loading,
	onRefresh,
	onEvaluate,
	showNotification,
}: CasesViewProps) => {
	const [selectedCase, setSelectedCase] = useState<CaseType | null>(null);
	const [isEditModalOpen, setEditModalOpen] = useState(false);

	const handleSelectAll = () => {
		if (selectedCases.length === cases.length) {
			setSelectedCases([]);
		} else {
			setSelectedCases(cases.map((c) => c.id));
		}
	};

	const handleSelectCase = (caseId: string) => {
		if (selectedCases.includes(caseId)) {
			setSelectedCases(selectedCases.filter((id) => id !== caseId));
		} else {
			setSelectedCases([...selectedCases, caseId]);
		}
	};

	const deleteCase = async (caseId: string) => {
		try {
			const response = await fetch(`${API_BASE}/cases/${caseId}`, {
				method: "DELETE",
			});
			if (response.ok) {
				onRefresh();
				showNotification("Case deleted successfully!", "success");
			} else {
				showNotification("Failed to delete case", "error");
			}
		} catch (_error) {
			showNotification("Failed to delete case", "error");
		}
	};

	const deleteSelectedCases = async () => {
		try {
			const deletePromises = selectedCases.map((caseId) =>
				fetch(`${API_BASE}/cases/${caseId}`, {
					method: "DELETE",
				}),
			);
			const responses = await Promise.all(deletePromises);
			const allDeleted = responses.every((response) => response.ok);
			if (allDeleted) {
				onRefresh();
				showNotification("Selected cases deleted successfully!", "success");
			} else {
				showNotification("Failed to delete some cases", "error");
			}
		} catch (_error) {
			showNotification("Failed to delete cases", "error");
		}
	};

	const openEditModal = (caseData: CaseType) => {
		setSelectedCase(caseData);
		setEditModalOpen(true);
	};

	const exportSelectedCases = () => {
		const selectedData = cases
			.filter((case_) => selectedCases.includes(case_.id))
			.map(
				({
					input,
					actual_output,
					expected_output,
					context,
					retrieval_context,
				}) => ({
					input,
					actual_output,
					expected_output,
					context: context?.join(", ") || "",
					retrieval_context: retrieval_context?.join(", ") || "",
				}),
			);
		const worksheet = XLSX.utils.json_to_sheet(selectedData);
		const workbook = XLSX.utils.book_new();
		XLSX.utils.book_append_sheet(workbook, worksheet, "Cases");
		XLSX.writeFile(workbook, "diting_metric_cases.xlsx");
	};

	if (loading) {
		return <div className="text-center py-8">Loading...</div>;
	}

	return (
		<div>
			{/* Search and Actions Bar */}
			<div className="flex items-center justify-between mb-4">
				<div className="relative">
					<Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
					<input
						type="text"
						placeholder="Search cases..."
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
						className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div className="flex items-center space-x-2">
					<button
						type="button"
						onClick={onEvaluate}
						disabled={selectedCases.length === 0}
						className={`inline-flex items-center px-4 py-2 rounded-lg ${selectedCases.length > 0
								? "bg-blue-600 text-white hover:bg-blue-700"
								: "bg-gray-300 text-gray-500 cursor-not-allowed"
							}`}
					>
						<Play className="w-5 h-5 mr-2" />
						Evaluate
					</button>
					<button
						type="button"
						onClick={deleteSelectedCases}
						disabled={selectedCases.length === 0}
						className={`inline-flex items-center px-4 py-2 rounded-lg ${selectedCases.length > 0
								? "bg-red-600 text-white hover:bg-red-700"
								: "bg-gray-300 text-gray-500 cursor-not-allowed"
							}`}
					>
						<Trash2 className="w-5 h-5 mr-2" />
						Delete
					</button>
					<button
						type="button"
						onClick={exportSelectedCases}
						disabled={selectedCases.length === 0}
						className={`inline-flex items-center px-4 py-2 rounded-lg ${selectedCases.length > 0
								? "bg-green-600 text-white hover:bg-green-700"
								: "bg-gray-300 text-gray-500 cursor-not-allowed"
							}`}
					>
						<Download className="w-5 h-5 mr-2" />
						Export
					</button>
				</div>
			</div>

			{/* Cases Table */}
			<div className="bg-white shadow rounded-lg overflow-hidden">
				<table className="min-w-full divide-y divide-gray-200">
					<thead className="bg-gray-50">
						<tr>
							<th className="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								<input
									type="checkbox"
									checked={
										selectedCases.length === cases.length && cases.length > 0
									}
									onChange={handleSelectAll}
								/>
							</th>
							<th className="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								#
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Input
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Actual Output
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Expected Output
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Context
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Actions
							</th>
						</tr>
					</thead>
					<tbody className="bg-white divide-y divide-gray-200">
						{cases.map((case_, index) => (
							<tr key={case_.id}>
								<td className="px-2 py-4 whitespace-nowrap">
									<input
										type="checkbox"
										checked={selectedCases.includes(case_.id)}
										onChange={() => handleSelectCase(case_.id)}
									/>
								</td>
								<td className="px-2 py-4 whitespace-nowrap text-sm">
									{index + 1}
								</td>
								<td className="px-6 py-4 whitespace-nowrap" title={case_.input}>
									{case_.input.length > 10
										? `${case_.input.substring(0, 10)}...`
										: case_.input}
								</td>
								<td
									className="px-6 py-4 whitespace-nowrap"
									title={case_.actual_output}
								>
									{case_.actual_output.length > 10
										? `${case_.actual_output.substring(0, 10)}...`
										: case_.actual_output}
								</td>
								<td
									className="px-6 py-4 whitespace-nowrap"
									title={case_.expected_output || "N/A"}
								>
									{(case_.expected_output || "N/A").length > 10
										? `${(case_.expected_output || "N/A").substring(0, 10)}...`
										: case_.expected_output || "N/A"}
								</td>
								<td
									className="px-6 py-4 whitespace-nowrap"
									title={case_.context || "N/A"}
								>
									{Array.isArray(case_.context)
										? case_.context.join().length > 10
											? `${case_.context.join("\n").substring(0, 10)}...`
											: case_.context.join("\n")
										: (case_.context || "N/A")}
								</td>
								<td className="px-6 py-4 whitespace-nowrap space-x-2">
									<button
										type="button"
										onClick={() => openEditModal(case_)}
										className="text-blue-600 hover:text-blue-800"
									>
										<Edit2 className="w-5 h-5" />
									</button>
									<button
										type="button"
										onClick={() => deleteCase(case_.id)}
										className="text-red-600 hover:text-red-800"
									>
										<Trash2 className="w-5 h-5" />
									</button>
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>

			{isEditModalOpen && (
				<EditCaseModal
					onClose={() => setEditModalOpen(false)}
					onSuccess={() => {
						setEditModalOpen(false);
						onRefresh();
						showNotification("Case updated successfully!", "success");
					}}
					caseData={selectedCase}
				/>
			)}
		</div>
	);
};

export default CasesView;
