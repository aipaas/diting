import { z } from "zod";

export const NotificationSchema = z.object({
	message: z.string(),
	type: z.enum(["info", "success", "error"]),
});

export type NotificationType = z.infer<typeof NotificationSchema> | null;
