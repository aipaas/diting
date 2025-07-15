import { useState, useEffect } from "react";
import type { HttpToolType } from "../types/Tools";
import { API_BASE } from "../constants";

const useFetchToolConfigs = () => {
	const [toolConfigs, setToolConfigs] = useState<HttpToolType[]>([]);
	const [loading, setLoading] = useState<boolean>(true);
	const [error, setError] = useState<string | null>(null);

	const fetchToolConfigs = async () => {
		try {
			const response = await fetch(`${API_BASE}/toolconfigs`);
			if (response.ok) {
				const data = await response.json();
				setToolConfigs(data);
			} else {
				setError("Failed to fetch tool configurations");
			}
		} catch (error) {
			setError("Failed to fetch tool configurations: " + error);
		} finally {
			setLoading(false);
		}
	};
	useEffect(() => {
		fetchToolConfigs();
	}, []);
	return { toolConfigs, loading, error, fetchToolConfigs };
};

export default useFetchToolConfigs;
