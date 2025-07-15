import { z } from "zod";

const HeaderPropsSchema = z.object({
	setShowCreateModal: z.function().args(z.boolean()).returns(z.void()),
	setShowModelModal: z.function().args(z.boolean()).returns(z.void()),
});

export type HeaderProps = z.infer<typeof HeaderPropsSchema>;
