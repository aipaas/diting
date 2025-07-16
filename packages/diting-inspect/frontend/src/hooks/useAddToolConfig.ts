import { useState } from "react";
import { API_BASE } from "../constants";
import type { HttpToolType } from "../types/Tools";

const useAddToolConfig = (
	onRefresh: () => void,
	showNotification: (
		message: string,
		type?: "info" | "success" | "error",
	) => void,
) => {
	const [isLoading, setIsLoading] = useState(false);

	const addToolConfig = async (configData: Partial<HttpToolType>) => {
		setIsLoading(true);
		try {
			const response = await fetch(`${API_BASE}/toolconfigs`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(configData),
			});
			if (!response.ok) {
				throw new Error("Failed to create new tool configuration");
			}
			showNotification(
				"New tool configuration created successfully!",
				"success",
			);
			onRefresh();
		} catch (error) {
			showNotification(error.message, "error");
		} finally {
			setIsLoading(false);
		}
	};

	return { addToolConfig, isLoading };
};
export default useAddToolConfig;
