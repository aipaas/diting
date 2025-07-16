import { useState } from "react";
import { API_BASE } from "../constants";
import type { ModelManagementData } from "../types/Models";

const useManageModels = () => {
	const [error, setError] = useState<string | null>(null);

	const setDefaultModel = async (modelData: ModelManagementData) => {
		try {
			const response = await fetch(
				`${API_BASE}/models/default/${modelData.model_type}/${modelData.id}`,
				{
					method: "POST",
				},
			);
			if (!response.ok) {
				throw new Error("Failed to set the model as default");
			}
		} catch (_error) {
			setError("Failed to set the model as default");
		}
	};

	return { setDefaultModel, error };
};

export default useManageModels;
