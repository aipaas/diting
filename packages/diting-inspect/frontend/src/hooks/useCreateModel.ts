import { useState } from "react";
import { API_BASE } from "../constants";
import type { ModelManagementData } from "../types/Models";

const useCreateModel = () => {
	const [error, setError] = useState<string | null>(null);

	const createModel = async (modelData: Partial<ModelManagementData>) => {
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
			return await response.json();
		} catch (_error) {
			setError("Failed to create new model");
			return null;
		}
	};

	return { createModel, error };
};

export default useCreateModel;
