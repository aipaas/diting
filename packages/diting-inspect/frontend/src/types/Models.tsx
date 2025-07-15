import { z } from "zod";

// Create a Zod schema for ModelManagementData
export const ModelManagementDataSchema = z.object({
	id: z
		.string()
		.optional()
		.nullable()
		.describe("Unique identifier for the model"),
	model_type: z
		.enum(["inference", "embedding", "evaluation"])
		.describe("Type of the model (e.g., inference, embedding, evaluation)"),
	model_name: z.string().describe("Name of the model"),
	access_endpoint: z.string().describe("API endpoint for accessing the model"),
	api_key: z.string().describe("API key for authentication"),
	notes: z
		.string()
		.optional()
		.nullable()
		.describe("Additional notes about the model"),
	is_default: z
		.boolean()
		.default(false)
		.describe("Indicates if this model is the default model for its type"),
});

export type ModelManagementData = z.infer<typeof ModelManagementDataSchema>;
