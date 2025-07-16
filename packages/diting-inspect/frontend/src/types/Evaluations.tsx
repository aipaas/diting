import { z } from "zod";
// Create a Zod schema for Evaluation
export const EvaluationSchema = z.any();

export type EvaluationType = z.infer<typeof EvaluationSchema>;
