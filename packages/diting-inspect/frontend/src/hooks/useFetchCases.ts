import { useState, useEffect } from "react";
import { API_BASE } from "../constants";
import type { CaseType } from "../types/Cases";

const useFetchCases = () => {
	const [cases, setCases] = useState<CaseType[]>([]);
	const [loading, setLoading] = useState<boolean>(false);
	const [error, setError] = useState<string | null>(null);

	const fetchCases = async () => {
		try {
			setLoading(true);
			const response = await fetch(`${API_BASE}/cases`);
			if (response.ok) {
				const data = await response.json();
				// Validate cases with Zod
				const parsedCases = data.map((caseData: any) => caseData);
				setCases(parsedCases);
			} else {
				setError("Failed to fetch cases");
			}
		} catch (_error) {
			setError("Failed to fetch cases");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchCases();
	}, []);

	return { cases, loading, error, fetchCases };
};

export default useFetchCases;
