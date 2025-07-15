import { z } from "zod";
// Define the Zod schema for Metric
const MetricSchema = z.object({
	name: z.string(),
	threshold: z.number().nullable(),
	debug: z.boolean().nullable(),
});

// Define the TypeScript interface for Metric
export type Metric = z.infer<typeof MetricSchema>;
