import { useState, useEffect } from "react";
import { API_BASE } from "../constants";
import { EvaluationSchema, type EvaluationType } from "../types/Evaluations";

const useFetchEvaluations = () => {
	const [evaluations, setEvaluations] = useState<EvaluationType[]>([]);
	const [loading, setLoading] = useState<boolean>(false);
	const [error, setError] = useState<string | null>(null);

	const fetchEvaluations = async () => {
		try {
			setLoading(true);
			const response = await fetch(`${API_BASE}/evaluations`);
			if (response.ok) {
				const data = await response.json();
				const parsedEvaluations = data.map((evaluationData: EvaluationType) =>
					EvaluationSchema.parse(evaluationData),
				);
				setEvaluations(parsedEvaluations);
			} else {
				setError("Failed to fetch evaluations");
			}
		} catch (_error) {
			setError("Failed to fetch evaluations");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchEvaluations();
	}, []);

	return { evaluations, loading, error, fetchEvaluations };
};

export default useFetchEvaluations;
