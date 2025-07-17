import { useState } from "react";
import type { ModelManagementData } from "../types/Models";

interface CreateModelModalProps {
	isOpen: boolean;
	onClose: () => void;
	onCreate: (modelData: Partial<ModelManagementData>) => void;
}

const CreateModelModual = ({
	isOpen,
	onClose,
	onCreate,
}: CreateModelModalProps) => {
	const [newModelData, setNewModelData] = useState<
		Partial<ModelManagementData>
	>({
		model_type: "inference",
		model_name: "",
		access_endpoint: "",
		api_key: "",
		notes: null,
		is_default: false,
	});

	const handleInputChange = (
		e: React.ChangeEvent<
			HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
		>,
	) => {
		const { name, value, type } = e.target;
		const inputValue =
			type === "checkbox" ? (e.target as HTMLInputElement).checked : value;

		setNewModelData((prevData) => ({
			...prevData,
			[name]: inputValue,
		}));
	};

	const handleSubmit = () => {
		onCreate(newModelData);
		onClose();
	};

	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
			<div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
				<h2 className="text-lg font-medium leading-6 text-gray-900 mb-4">
					Add New Model
				</h2>
				<input
					type="text"
					name="model_name"
					placeholder="Model Name"
					value={newModelData.model_name || ""}
					onChange={handleInputChange}
					className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
				/>
				<select
					name="model_type"
					value={newModelData.model_type || ""}
					onChange={handleInputChange}
					className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
				>
					<option value="inference">Inference</option>
					<option value="embedding">Embedding</option>
					<option value="evaluation">Evaluation</option>
				</select>
				<input
					type="text"
					name="access_endpoint"
					placeholder="Access Endpoint"
					value={newModelData.access_endpoint || ""}
					onChange={handleInputChange}
					className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
				/>
				<input
					type="text"
					name="api_key"
					placeholder="API Key"
					value={newModelData.api_key || ""}
					onChange={handleInputChange}
					className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
				/>
				<textarea
					name="notes"
					placeholder="Additional Notes"
					value={newModelData.notes || ""}
					onChange={handleInputChange}
					className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
				/>
				<label className="flex items-center mb-4">
					<input
						type="checkbox"
						name="is_default"
						checked={newModelData.is_default}
						onChange={handleInputChange}
						className="mr-2"
					/>
					Is Default {newModelData.model_type} Model
				</label>
				<div className="flex justify-end space-x-3">
					<button
						type="button"
						onClick={onClose}
						className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={handleSubmit}
						className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
					>
						Create
					</button>
				</div>
			</div>
		</div>
	);
};

export default CreateModelModual;
