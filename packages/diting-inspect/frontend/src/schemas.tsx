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
	context: z.array(z.string()).optional(),
	retrieval_context: z.array(z.string()).optional(),
});

export type CaseType = z.infer<typeof CaseSchema>;

// Create a Zod schema for Evaluation
export const EvaluationSchema = z.object({
	id: z.string(),
	case_ids: z.array(z.string()),
	metric_configs: z.array(
		z.object({
			type: z.string(),
			threshold: z.number().nullable(),
			debug: z.boolean().nullable(),
		}),
	),
	results: z.array(
		z.object({
			case_id: z.string(),
			metric_name: z.string(),
			score: z.number(),
			evaluated_at: z.string(), // ISO 8601 date string
		}),
	),
	status: z.string(),
	started_at: z.string(), // ISO 8601 date string
	completed_at: z.string(), // ISO 8601 date string
	total_cases: z.number(),
	total_metrics: z.number(),
	error: z.string().nullable(),
});

export type EvaluationType = z.infer<typeof EvaluationSchema>;

const HeaderPropsSchema = z.object({
	setShowCreateModal: z.function().args(z.boolean()).returns(z.void()),
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
