import { useState } from "react";
import { z } from "zod";
import { HttpTool } from "../types/Tools";
import { API_BASE } from "../constants";

const ToolExecutionModalPropsSchema = z.object({
	selectedCases: z.array(z.string()),
	onClose: z.function().args().returns(z.void()),
	onSuccess: z.function().args().returns(z.void()),
	toolConfigs: z.array(HttpTool),
});

export type ToolExecutionModalProps = z.infer<
	typeof ToolExecutionModalPropsSchema
>;

const ToolExecutionModal = ({
	selectedCases,
	onClose,
	onSuccess,
	toolConfigs,
}: ToolExecutionModalProps) => {
	const [selectedTool, setSelectedTool] = useState<string>("");

	const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		const input = e.currentTarget.input.value;
		const output = e.currentTarget.output.value;

		const toolExecuteData = {
			input: input,
			tool_id: selectedTool,
			output: output,
			case_ids: selectedCases,
		};
		const response = await fetch(`${API_BASE}/toolconfigs/execute`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(toolExecuteData),
		});

		if (response.ok) {
			onSuccess();
		} else {
			alert("Failed to start synthesizer");
		}
	};

	const handleToolSelection = (tool_id: string) => {
		const tool = toolConfigs.find((tool) => tool.id === tool_id);
		if (tool) {
			setSelectedTool(tool.id);
		}
	};

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
			<div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
				<h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">
					Run Tool
				</h3>
				<form onSubmit={handleSubmit}>
					<div className="flex mb-4 space-x-4">
						<div className="flex-1">
							<label className="block text-sm font-medium text-gray-700">
								Input
							</label>
							<select
								name="input"
								className="border rounded-md p-2 w-full"
								defaultValue="user_input"
							>
								<option value="user_input">User Input</option>
								<option value="actual_output">Actual Output</option>
								<option value="expected_output">Expected Output</option>
								<option value="context">Context</option>
								<option value="retrieval_context">Retrieval Context</option>
							</select>
						</div>
						<div className="flex-1">
							<label className="block text-sm font-medium text-gray-700">
								Tool
							</label>
							<select
								className="border rounded-md p-2 w-full"
								onChange={(e) => handleToolSelection(e.target.value)}
							>
								<option value="">Select a tool</option>
								{toolConfigs.map((tool) => (
									<option key={tool.id} value={tool.id}>
										{tool.name}
									</option>
								))}
							</select>
						</div>
						<div className="flex-1">
							<label className="block text-sm font-medium text-gray-700">
								Output
							</label>
							<select
								name="output"
								className="border rounded-md p-2 w-full"
								defaultValue="actual_output"
							>
								<option value="user_input">User Input</option>
								<option value="actual_output">Actual Output</option>
								<option value="expected_output">Expected Output</option>
								<option value="context">Context</option>
								<option value="retrieval_context">Retrieval Context</option>
							</select>
						</div>
					</div>
					<div className="flex justify-end space-x-3">
						<button
							type="button"
							onClick={onClose}
							className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
						>
							Cancel
						</button>
						<button
							type="submit"
							className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
						>
							Start Tool
						</button>
					</div>
				</form>
			</div>
		</div>
	);
};

export default ToolExecutionModal;
