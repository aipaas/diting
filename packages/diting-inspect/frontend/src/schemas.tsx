import { z } from "zod";

export const NotificationSchema = z.object({
	message: z.string(),
	type: z.enum(["info", "success", "error"]),
});

export type NotificationType = z.infer<typeof NotificationSchema> | null;

const BaseID = z.object({
	id: z.string(),
});

// Create a Zod schema for Case
export const CaseSchema = z.object({
	input: z.string().optional(),
	actual_output: z.string().optional(),
	expected_output: z.string().optional(),
	context: z.array(z.string()).optional().nullable(),
	retrieval_context: z.array(z.string()).optional().nullable(),
});

const CaseTypeData = BaseID.extend({
	input: z.string(),
	actual_output: z.string(),
	expected_output: z.string().optional(),
	context: z.array(z.string()).optional().nullable(),
	retrieval_context: z.array(z.string()).optional().nullable(),
});
export type CaseType = z.infer<typeof CaseTypeData>;

// Create a Zod schema for GenericBox
export const GenericBoxSchema = z.object({
	input: CaseSchema,
	tool: z.string().describe("Tool ID"),
	output: CaseSchema,
});

export type GenericBoxType = z.infer<typeof GenericBoxSchema>;

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

// Create a Zod schema for Evaluation
export const EvaluationSchema = z.any();

export type EvaluationType = z.infer<typeof EvaluationSchema>;

const HeaderPropsSchema = z.object({
	setShowCreateModal: z.function().args(z.boolean()).returns(z.void()),
	setShowModelModal: z.function().args(z.boolean()).returns(z.void()),
});

export type HeaderProps = z.infer<typeof HeaderPropsSchema>;

const NavigationTabsPropsSchema = z.object({
	activeTab: z.string(),
	setActiveTab: z.function().args(z.string()).returns(z.void()),
});

export type NavigationTabsProps = z.infer<typeof NavigationTabsPropsSchema>;

const CreateCaseModalPropsSchema = z.object({
	onClose: z.function().args().returns(z.void()),
	onSuccess: z.function().args().returns(z.void()),
});

export type CreateCaseModalProps = z.infer<typeof CreateCaseModalPropsSchema>;

const EvaluationModalPropsSchema = z.object({
	selectedCases: z.array(z.string()),
	onClose: z.function().args().returns(z.void()),
	onSuccess: z.function().args().returns(z.void()),
	modelConfigs: z.array(ModelManagementDataSchema),
});

export type EvaluationModalProps = z.infer<typeof EvaluationModalPropsSchema>;

// Define the Zod schema for Metric
const MetricSchema = z.object({
	name: z.string(),
	threshold: z.number().nullable(),
	debug: z.boolean().nullable(),
});

// Define the TypeScript interface for Metric
export type Metric = z.infer<typeof MetricSchema>;

export const FileSchema = z.object({
	file: z.instanceof(File).optional(),
});

// Define the Tool schema
export const ToolSchema = z.object({
	name: z.string().describe("Name of the tool"),
	description: z.string().describe("Description of the tool"),
	method: z.string().default("GET").describe("HTTP method for the tool"),
	endpoint: z.string().describe("API endpoint for the tool"),
	headers: z.record(z.any()).describe("Headers for the request"),
	headersOrder: z.array(z.string()).default([]).describe("Order of headers"),
	args: z.array(z.string()).default([]).describe("Arguments for the request"),
	requestBody: z.string().describe("Request body for the tool"),
	responseBody: z.string().describe("Expected response body from the tool"),
});

// Define the ToolConfig schema
export const ToolConfigSchema = z.object({
	name: z.string().describe("Name of the tool configuration"),
	tools: z.array(ToolSchema).describe("List of tools in the configuration"),
	createdAt: z.date().default(new Date()).describe("Creation timestamp"),
	updatedAt: z.date().default(new Date()).describe("Last updated timestamp"),
});

export type ToolConfig = z.infer<typeof ToolConfigSchema>;
