import { Plus, Trash } from "lucide-react";
import type { FormEvent, MouseEvent } from "react";
import { useState } from "react";
import { API_BASE } from "../constants";
import type { CaseType } from "../schemas";

interface EditCaseModalProps {
	onClose: () => void;
	onSuccess: () => void;
	caseData: CaseType;
}

interface FormData {
	input: string;
	actual_output: string;
	expected_output?: string;
	context: string[];
	retrieval_context: string[];
}

const EditCaseModal = ({
	onClose,
	onSuccess,
	caseData,
}: EditCaseModalProps) => {
	const [formData, setFormData] = useState<FormData>({
		input: caseData.input,
		actual_output: caseData.actual_output,
		expected_output: caseData.expected_output || "",
		context: caseData.context || [],
		retrieval_context: caseData.retrieval_context || [],
	});
	const [modalWidth, setModalWidth] = useState<number>(400); // Default width

	const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		try {
			const response = await fetch(`${API_BASE}/cases/${caseData.id}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(formData),
			});
			if (response.ok) {
				onSuccess();
			} else {
				alert("Failed to update case");
			}
		} catch (_error) {
			alert("Error updating case");
		}
	};

	const addContext = () => {
		setFormData({ ...formData, context: [...formData.context, ""] });
	};

	const removeContext = (index: number) => {
		const newContext = formData.context.filter((_, i) => i !== index);
		setFormData({ ...formData, context: newContext });
	};

	const addRetrievalContext = () => {
		setFormData({
			...formData,
			retrieval_context: [...formData.retrieval_context, ""],
		});
	};

	const removeRetrievalContext = (index: number) => {
		const newRetrievalContext = formData.retrieval_context.filter(
			(_, i) => i !== index,
		);
		setFormData({ ...formData, retrieval_context: newRetrievalContext });
	};

	const handleContextChange = (index: number, value: string) => {
		const newContext = [...formData.context];
		newContext[index] = value;
		setFormData({ ...formData, context: newContext });
	};

	const handleRetrievalContextChange = (index: number, value: string) => {
		const newRetrievalContext = [...formData.retrieval_context];
		newRetrievalContext[index] = value;
		setFormData({ ...formData, retrieval_context: newRetrievalContext });
	};

	const handleMouseDown = (e: MouseEvent<HTMLDivElement>) => {
		e.preventDefault();
		document.addEventListener("mousemove", handleMouseMove);
		document.addEventListener("mouseup", handleMouseUp);
	};

	const handleMouseMove = (e: MouseEvent) => {
		setModalWidth(e.clientX - e.target.getBoundingClientRect().left);
	};

	const handleMouseUp = () => {
		document.removeEventListener("mousemove", handleMouseMove);
		document.removeEventListener("mouseup", handleMouseUp);
	};

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
			<div
				className="relative top-20 mx-auto p-5 border shadow-lg rounded-md bg-white"
				style={{ width: modalWidth }}
			>
				<div
					className="resize-handle"
					onMouseDown={handleMouseDown}
					style={{
						cursor: "ew-resize",
						width: "10px",
						height: "100%",
						position: "absolute",
						right: "0",
						top: "0",
					}}
				/>
				<h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">
					Edit Case
				</h3>
				<form onSubmit={handleSubmit}>
					<div className="mb-4">
						<label
							className="block text-sm font-medium text-gray-700"
							htmlFor="form_data_input_id"
						>
							Input
						</label>
						<textarea
							id="form_data_input_id"
							value={formData.input || ""}
							onChange={(e) =>
								setFormData({ ...formData, input: e.target.value })
							}
							className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3"
							required
						/>
					</div>
					<div className="mb-4">
						<label
							className="block text-sm font-medium text-gray-700"
							htmlFor="form_data_actual_output_id"
						>
							Actual Output
						</label>
						<textarea
							id="form_data_actual_output_id"
							value={formData.actual_output || ""}
							onChange={(e) =>
								setFormData({ ...formData, actual_output: e.target.value })
							}
							className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3"
							required
						/>
					</div>
					<div className="mb-4">
						<label
							className="block text-sm font-medium text-gray-700"
							htmlFor="form_data_expected_output_id"
						>
							Expected Output
						</label>
						<textarea
							id="form_data_expected_output_id"
							value={formData.expected_output || ""}
							onChange={(e) =>
								setFormData({ ...formData, expected_output: e.target.value })
							}
							className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3"
						/>
					</div>
					<div className="mb-4">
						<label className="block text-sm font-medium text-gray-700">
							Context
						</label>
						{formData.context.map((ctx, index) => (
							<div key={index} className="flex items-center mb-2">
								<textarea
									value={ctx || ""}
									onChange={(e) => handleContextChange(index, e.target.value)}
									className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3"
								/>
								<button
									type="button"
									onClick={() => removeContext(index)}
									className="text-red-600 ml-2"
								>
									<Trash className="w-4 h-4" />
								</button>
							</div>
						))}
						<button
							type="button"
							onClick={addContext}
							className="text-blue-600"
						>
							<Plus className="w-4 h-4" />
							Add Context
						</button>
					</div>
					<div className="mb-4">
						<label className="block text-sm font-medium text-gray-700">
							Retrieval Context
						</label>
						{formData.retrieval_context.map((retrievalCtx, index) => (
							<div key={index} className="flex items-center mb-2">
								<textarea
									value={retrievalCtx || ""}
									onChange={(e) =>
										handleRetrievalContextChange(index, e.target.value)
									}
									className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3"
								/>
								<button
									type="button"
									onClick={() => removeRetrievalContext(index)}
									className="text-red-600 ml-2"
								>
									<Trash className="w-4 h-4" />
								</button>
							</div>
						))}
						<button
							type="button"
							onClick={addRetrievalContext}
							className="text-blue-600"
						>
							<Plus className="w-4 h-4" />
							Add Retrieval Context
						</button>
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
							Update
						</button>
					</div>
				</form>
			</div>
		</div>
	);
};

export default EditCaseModal;
