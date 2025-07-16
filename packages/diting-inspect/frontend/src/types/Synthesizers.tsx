import { z } from "zod";
const SynthesizerSchema = z.object({
	name: z.string(),
	debug: z.boolean().nullable(),
});

export type Synthesizer = z.infer<typeof SynthesizerSchema>;
