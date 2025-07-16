import { useEffect, useState } from "react";
import { API_BASE } from "../constants";
import type { Metric } from "../types/Metrics";

const useFetchAvailableMetrics = () => {
	const [availableMetrics, setAvailableMetrics] = useState<Metric[]>([]);
	const [error, setError] = useState<string | null>(null);

	const fetchAvailableMetrics = async () => {
		try {
			const response = await fetch(`${API_BASE}/metrics_schemas`);
			if (response.ok) {
				const metrics = await response.json();
				setAvailableMetrics(metrics);
			} else {
				setError("Failed to fetch available metrics");
			}
		} catch (error) {
			setError("Error fetching available metrics");
		}
	};

	useEffect(() => {
		fetchAvailableMetrics();
	}, []);

	return { availableMetrics, error };
};

export default useFetchAvailableMetrics;
