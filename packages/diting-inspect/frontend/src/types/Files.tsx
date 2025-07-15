import { z } from "zod";

export const FileSchema = z.object({
	file: z.instanceof(File).optional(),
});
