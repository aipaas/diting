import { useState } from "react";
import { API_BASE } from "../constants";
import type { EvaluationType } from "../types/Evaluations";

const useCreateEvaluation = () => {
	const [error, setError] = useState<string | null>(null);

	const createEvaluation = async (evaluationData: Partial<EvaluationType>) => {
		try {
			const response = await fetch(`${API_BASE}/evaluations`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(evaluationData),
			});
			if (!response.ok) {
				throw new Error("Failed to create new evaluation");
			}
			return await response.json();
		} catch (_error) {
			setError("Failed to create new evaluation");
			return null;
		}
	};

	return { createEvaluation, error };
};

export default useCreateEvaluation;
