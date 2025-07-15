import { useState } from "react";
import { Plus, Trash2, Search, Edit } from "lucide-react";
import { API_BASE } from "../constants";
import CreateToolConfigModal from "./CreateToolConfigModal";
import EditToolConfigModal from "./EditToolConfigModal";
import type { HttpToolType } from "../types/Tools";

interface ToolConfigsViewProps {
	toolConfigs: HttpToolType[];
	onRefresh: () => void;
	showNotification: (
		message: string,
		type?: "info" | "success" | "error",
	) => void;
}

const ToolConfigsView = ({
	toolConfigs,
	onRefresh,
	showNotification,
}: ToolConfigsViewProps) => {
	const [searchTerm, setSearchTerm] = useState<string>("");
	const [selectedConfigs, setSelectedConfigs] = useState<string[]>([]);
	const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
	const [isEditModalOpen, setEditModalOpen] = useState<boolean>(false);
	const [selectedConfig, setSelectedConfig] = useState<Partial<HttpToolType>>(
		{},
	);

	const filteredConfigs = toolConfigs.filter((config) =>
		config.name.toLowerCase().includes(searchTerm.toLowerCase()),
	);

	const handleSelectConfig = (id: string) => {
		if (selectedConfigs.includes(id)) {
			setSelectedConfigs(
				selectedConfigs.filter((selectedId) => selectedId !== id),
			);
		} else {
			setSelectedConfigs([...selectedConfigs, id]);
		}
	};

	const handleDeleteSelected = async () => {
		try {
			await Promise.all(
				selectedConfigs.map(async (id) => {
					const response = await fetch(`${API_BASE}/toolconfigs/${id}`, {
						method: "DELETE",
					});
					if (!response.ok) {
						throw new Error(`Failed to delete tool config with ID: ${id}`);
					}
				}),
			);
			showNotification(
				"Selected tool configurations deleted successfully!",
				"success",
			);
			setSelectedConfigs([]);
			onRefresh();
		} catch (error) {
			showNotification(error.message, "error");
		}
	};

	const handleAddNewConfig = async (configData: Partial<HttpToolType>) => {
		try {
			const response = await fetch(`${API_BASE}/toolconfigs`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(configData),
			});
			if (!response.ok) {
				throw new Error("Failed to create new tool configuration");
			}
			showNotification(
				"New tool configuration created successfully!",
				"success",
			);
			setIsModalOpen(false);
			onRefresh();
		} catch (error) {
			showNotification(error.message, "error");
		}
	};

	const handleUpdateConfig = async (configData: Partial<HttpToolType>) => {
		try {
			const response = await fetch(`${API_BASE}/toolconfigs/${configData.id}`, {
				method: "PUT",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(configData),
			});
			if (!response.ok) {
				throw new Error("Failed to update tool configuration");
			}
			showNotification("Tool configuration updated successfully!", "success");
			setEditModalOpen(false);
			onRefresh();
		} catch (error) {
			showNotification(error.message, "error");
		}
	};

	const handleEditConfig = (config: HttpToolType) => {
		setSelectedConfig(config);
		setEditModalOpen(true);
	};

	return (
		<div>
			{/* Search and Actions Bar */}
			<div className="flex items-center justify-between mb-4">
				<div className="relative">
					<Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
					<input
						type="text"
						placeholder="Search tool configurations..."
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
						className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div className="flex items-center space-x-2">
					<button
						type="button"
						onClick={() => setIsModalOpen(true)}
						className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
					>
						<Plus className="w-5 h-5 mr-2" />
						New Tool Config
					</button>
					<button
						type="button"
						onClick={handleDeleteSelected}
						disabled={selectedConfigs.length === 0}
						className={`inline-flex items-center px-4 py-2 rounded-lg ${
							selectedConfigs.length > 0
								? "bg-red-600 text-white hover:bg-red-700"
								: "bg-gray-300 text-gray-500 cursor-not-allowed"
						}`}
					>
						<Trash2 className="w-5 h-5 mr-2" />
						Delete
					</button>
				</div>
			</div>

			{isModalOpen && (
				<CreateToolConfigModal
					isOpen={isModalOpen}
					onClose={() => setIsModalOpen(false)}
					onCreate={handleAddNewConfig}
				/>
			)}

			{isEditModalOpen && (
				<EditToolConfigModal
					onClose={() => setEditModalOpen(false)}
					onSuccess={handleUpdateConfig}
					configData={selectedConfig}
				/>
			)}

			{/* Tool Configurations Table */}
			<div className="bg-white shadow rounded-lg overflow-hidden">
				<table className="min-w-full divide-y divide-gray-200">
					<thead className="bg-gray-50">
						<tr>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								<input
									type="checkbox"
									checked={
										selectedConfigs.length === filteredConfigs.length &&
										filteredConfigs.length > 0
									}
									onChange={() => {
										if (selectedConfigs.length === filteredConfigs.length) {
											setSelectedConfigs([]);
										} else {
											setSelectedConfigs(
												filteredConfigs.map((config) => config.id),
											);
										}
									}}
								/>
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Name
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Actions
							</th>
						</tr>
					</thead>
					<tbody className="bg-white divide-y divide-gray-200">
						{filteredConfigs.length > 0 ? (
							filteredConfigs.map((config) => (
								<tr key={config.id}>
									<td className="px-6 py-4 whitespace-nowrap">
										<input
											type="checkbox"
											checked={selectedConfigs.includes(config.id)}
											onChange={() => handleSelectConfig(config.id)}
										/>
									</td>
									<td className="px-6 py-4 whitespace-nowrap">{config.name}</td>
									<td className="px-6 py-4 whitespace-nowrap">
										<button
											type="button"
											className="text-blue-600 hover:text-blue-800"
											onClick={() => handleEditConfig(config)}
										>
											<Edit className="w-5 h-5 mr-2" />
										</button>
									</td>
								</tr>
							))
						) : (
							<tr>
								<td colSpan="3" className="text-center py-4">
									No tool configurations found.
								</td>
							</tr>
						)}
					</tbody>
				</table>
			</div>
		</div>
	);
};

export default ToolConfigsView;
