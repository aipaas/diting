import { useEffect, useState } from "react";
import { API_BASE } from "../constants";
import type { Synthesizer } from "../types/Synthesizers";

const useFetchAvailableSynthesizers = () => {
	const [availableSynthesizers, setAvailableSynthesizers] = useState<Synthesizer[]>([]);
	const [error, setError] = useState<string | null>(null);

	const fetchAvailableSynthesizers = async () => {
		try {
			const response = await fetch(`${API_BASE}/synthesizers_schemas`);
			if (response.ok) {
				const synthesizers = await response.json();
				setAvailableSynthesizers(synthesizers);
			} else {
				setError("Failed to fetch available synthesizers");
			}
		} catch (error) {
			setError("Error fetching available synthesizers");
		}
	};

	useEffect(() => {
		fetchAvailableSynthesizers();
	}, []);

	return { availableSynthesizers, error };
};

export default useFetchAvailableSynthesizers;
