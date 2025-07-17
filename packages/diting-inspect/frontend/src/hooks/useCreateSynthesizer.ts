import { useState } from "react";
import { API_BASE } from "../constants";

const useCreateSynthesizer = () => {
	const [error, setError] = useState<string | null>(null);

	const createSynthesizer = async (synthesizerData: Partial<any>) => {
		try {
			const response = await fetch(`${API_BASE}/synthesizers`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(synthesizerData),
			});
			if (!response.ok) {
				throw new Error("Failed to create new synthesizer");
			}
			return await response.json();
		} catch (_error) {
			setError("Failed to create new synthesizer");
			return null;
		}
	};

	return { createSynthesizer, error };
};

export default useCreateSynthesizer;
