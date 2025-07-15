import { useState, useEffect } from "react";
import { API_BASE } from "../constants";
import type { ModelManagementData } from "../types/Models";

const useFetchModels = () => {
	const [models, setModels] = useState<ModelManagementData[]>([]);
	const [loading, setLoading] = useState<boolean>(false);
	const [error, setError] = useState<string | null>(null);

	const fetchModels = async () => {
		try {
			setLoading(true);
			const response = await fetch(`${API_BASE}/models`);
			if (response.ok) {
				const data = await response.json();
				setModels(data);
			} else {
				setError("Failed to fetch models");
			}
		} catch (_error) {
			setError("Failed to fetch models");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchModels();
	}, []);

	return { models, loading, error, fetchModels };
};

export default useFetchModels;
