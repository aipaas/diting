import { Edit, Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { API_BASE } from "../constants";
import type { ModelManagementData } from "../schemas";
import CreateModelModual from "./CreateModelModual";
import EditModelModal from "./EditModelModal";

interface ModelsViewProps {
	models: ModelManagementData[];
	onRefresh: () => void;
	showNotification: (
		message: string,
		type?: "info" | "success" | "error",
	) => void;
}

const ModelsView = ({
	models,
	onRefresh,
	showNotification,
}: ModelsViewProps) => {
	const [searchTerm, setSearchTerm] = useState<string>("");
	const [selectedModels, setSelectedModels] = useState<string[]>([]);
	const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
	const [isEditModalOpen, setEditModalOpen] = useState<boolean>(false);
	const [selectedModel, setSelectedModel] = useState<
		Partial<ModelManagementData>
	>({ model_name: "", model_type: "inference" });

	const filteredModels = models.filter(
		(model) =>
			model.id.toString().includes(searchTerm) ||
			model.model_name.toLowerCase().includes(searchTerm.toLowerCase()),
	);

	const handleSelectModel = (id: string) => {
		if (selectedModels.includes(id)) {
			setSelectedModels(
				selectedModels.filter((selectedId) => selectedId !== id),
			);
		} else {
			setSelectedModels([...selectedModels, id]);
		}
	};

	const handleDeleteSelected = async () => {
		try {
			await Promise.all(
				selectedModels.map(async (id) => {
					const response = await fetch(`${API_BASE}/models/${id}`, {
						method: "DELETE",
					});
					if (!response.ok) {
						throw new Error(`Failed to delete model with ID: ${id}`);
					}
				}),
			);
			showNotification("Selected models deleted successfully!", "success");
			setSelectedModels([]);
			onRefresh();
		} catch (error) {
			showNotification(error.message, "error");
		}
	};

	const handleAddNewModel = async (modelData: Partial<ModelManagementData>) => {
		try {
			const response = await fetch(`${API_BASE}/models`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(modelData),
			});
			if (!response.ok) {
				throw new Error("Failed to create new model");
			}
			const createdModel = await response.json();

			if (modelData.is_default) {
				const defaultResponse = await fetch(
					`${API_BASE}/models/default/${modelData.model_type}/${createdModel.id}`,
					{
						method: "POST",
					},
				);
				if (!defaultResponse.ok) {
					throw new Error("Failed to set the model as default");
				}
			}

			showNotification("New model created successfully!", "success");
			setIsModalOpen(false);
			onRefresh();
		} catch (error) {
			showNotification(error.message, "error");
		}
	};

	const handleEditModel = (model: ModelManagementData) => {
		setSelectedModel(model);
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
						placeholder="Search models..."
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
						New Model
					</button>
					<button
						type="button"
						onClick={handleDeleteSelected}
						disabled={selectedModels.length === 0}
						className={`inline-flex items-center px-4 py-2 rounded-lg ${selectedModels.length > 0
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
				<CreateModelModual
					isOpen={isModalOpen}
					onClose={() => setIsModalOpen(false)}
					onCreate={handleAddNewModel}
				/>
			)}

			{isEditModalOpen && (
				<EditModelModal
					onClose={() => setEditModalOpen(false)}
					onSuccess={() => {
						setEditModalOpen(false);
						onRefresh();
						showNotification("Model updated successfully!", "success");
					}}
					modelData={selectedModel}
				/>
			)}

			{/* Models Table */}
			<div className="bg-white shadow rounded-lg overflow-hidden">
				<table className="min-w-full divide-y divide-gray-200">
					<thead className="bg-gray-50">
						<tr>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								<input
									type="checkbox"
									checked={
										selectedModels.length === filteredModels.length &&
										filteredModels.length > 0
									}
									onChange={() => {
										if (selectedModels.length === filteredModels.length) {
											setSelectedModels([]);
										} else {
											setSelectedModels(
												filteredModels.map((model) => model.id),
											);
										}
									}}
								/>
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Name
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Model Type
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Notes
							</th>
							<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
								Actions
							</th>
						</tr>
					</thead>
					<tbody className="bg-white divide-y divide-gray-200">
						{filteredModels.length > 0 ? (
							filteredModels.map((model) => (
								<tr key={model.id}>
									<td className="px-6 py-4 whitespace-nowrap">
										<input
											type="checkbox"
											checked={selectedModels.includes(model.id)}
											onChange={() => handleSelectModel(model.id)}
										/>
									</td>
									<td className="px-6 py-4 whitespace-nowrap">
										{model.model_name}
									</td>
									<td className="px-6 py-4 whitespace-nowrap">
										{model.model_type}
									</td>
									<td className="px-6 py-4 whitespace-nowrap">{model.notes}</td>
									<td className="px-6 py-4 whitespace-nowrap">
										<button
											type="button"
											className="text-blue-600 hover:text-blue-800"
											onClick={() => handleEditModel(model)}
										>
											<Edit className="w-5 h-5 mr-2" />
										</button>
									</td>
								</tr>
							))
						) : (
							<tr>
								<td colSpan="5" className="text-center py-4">
									No models found.
								</td>
							</tr>
						)}
					</tbody>
				</table>
			</div>
		</div>
	);
};

export default ModelsView;
