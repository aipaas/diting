import { useEffect, useState } from "react";
import { API_BASE } from "../constants";
import type { ModelManagementData } from "../types/Models";

interface EditModelModalProps {
	onClose: () => void;
	onSuccess: () => void;
	modelData: Partial<ModelManagementData>;
}

const EditModelModal = ({
	onClose,
	onSuccess,
	modelData,
}: EditModelModalProps) => {
	const [formData, setFormData] = useState<Partial<ModelManagementData>>({
		...modelData,
	});

	useEffect(() => {
		setFormData({ ...modelData });
	}, [modelData]);

	const handleInputChange = (
		e: React.ChangeEvent<
			HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
		>,
	) => {
		const { name, value, type } = e.target;
		const inputValue =
			type === "checkbox" ? (e.target as HTMLInputElement).checked : value;

		setFormData((prevData) => ({
			...prevData,
			[name]: inputValue,
		}));
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		try {
			const response = await fetch(`${API_BASE}/models/${modelData.id}`, {
				method: "PUT",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(formData),
			});
			if (!response.ok) {
				throw new Error("Failed to update model");
			}
			onSuccess();
		} catch (error) {
			console.error(error);
		}
	};

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
			<div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
				<h2 className="text-lg font-medium leading-6 text-gray-900 mb-4">
					Edit Model
				</h2>
				<form onSubmit={handleSubmit}>
					<label className="block mb-2" htmlFor="model_name">
						Model Name
					</label>
					<input
						type="text"
						name="model_name"
						id="model_name"
						value={formData.model_name || ""}
						onChange={handleInputChange}
						placeholder="Model Name"
						className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
						required
					/>
					<label className="block mb-2" htmlFor="model_type">
						Model Type
					</label>
					<select
						name="model_type"
						id="model_type"
						value={formData.model_type || ""}
						onChange={handleInputChange}
						className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
						required
					>
						<option value="inference">Inference</option>
						<option value="embedding">Embedding</option>
						<option value="evaluation">Evaluation</option>
					</select>
					<label className="block mb-2" htmlFor="endpoint">
						Endpoint
					</label>
					<input
						type="text"
						name="endpoint"
						id="endpoint"
						value={formData.access_endpoint || ""}
						onChange={handleInputChange}
						placeholder="Endpoint"
						className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
					/>
					<label className="block mb-2" htmlFor="apikey">
						API Key
					</label>
					<input
						type="text"
						name="apikey"
						id="apikey"
						value={formData.api_key || ""}
						onChange={handleInputChange}
						placeholder="API Key"
						className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
					/>
					<label className="block mb-2" htmlFor="notes">
						Notes
					</label>
					<textarea
						name="notes"
						id="notes"
						value={formData.notes || ""}
						onChange={handleInputChange}
						placeholder="Notes"
						className="border border-gray-300 rounded-lg p-2 mb-4 w-full"
					/>
					<label className="flex items-center mb-4">
						<input
							type="checkbox"
							name="is_default"
							checked={formData.is_default || false}
							onChange={handleInputChange}
							className="mr-2"
						/>
						Is Default {formData.model_type} Model
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
							type="submit"
							className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
						>
							Save
						</button>
					</div>
				</form>
			</div>
		</div>
	);
};

export default EditModelModal;
