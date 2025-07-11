import { z } from "zod";

export const NotificationSchema = z.object({
	message: z.string(),
	type: z.enum(["info", "success", "error"]),
});

export type NotificationType = z.infer<typeof NotificationSchema> | null;

// Create a Zod schema for Case
export const CaseSchema = z.object({
	id: z.string(),
	input: z.string(),
	actual_output: z.string(),
	expected_output: z.string().optional(),
	context: z.array(z.string()).optional().nullable(),
	retrieval_context: z.array(z.string()).optional().nullable(),
});

export type CaseType = z.infer<typeof CaseSchema>;

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
// 	     z.object({
// 	id: z.string(),
// 	case_ids: z.array(z.string()),
// 	metric_configs: z.array(
// 		z.object({
// 			type: z.string(),
// 			threshold: z.number().nullable(),
// 			debug: z.boolean().nullable(),
// 		}),
// 	),
// 	model_configs: z.array(ModelManagementDataSchema).optional().nullable(),
// 	results: z.array(
// 		z.object({
// 			case_id: z.string(),
// 			metric_name: z.string(),
// 			score: z.number().optional().nullable(),
// 			evaluated_at: z.string().optional().nullable(), // ISO 8601 date string
// 			error: z.string().optional().nullable(),
// 		}),
// 	).optional().nullable(),
// 	status: z.string(),
// 	started_at: z.string(), // ISO 8601 date string
// 	completed_at: z.string(), // ISO 8601 date string
// 	total_cases: z.number(),
// 	total_metrics: z.number(),
// 	error: z.string().nullable(),
// });

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
