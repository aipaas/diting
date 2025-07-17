import { z } from "zod";

const BaseID = z.object({
	id: z.string(),
});

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
	tags: z.array(z.string()).optional().nullable(),
	metadata: z.record(z.any()).optional().nullable(),
});
export type CaseType = z.infer<typeof CaseTypeData>;
