import { useState } from "react";
import { z } from "zod";
import {
	ModelManagementDataSchema,
	type ModelManagementData,
} from "../types/Models";
import MetricConfigModal from "./MetricConfigModal";
import type { Synthesizer } from "../types/Synthesizers";
import useFetchAvailableSynthesizers from "../hooks/useFetchAvailableSynthesizers";

const SynthesizerModalPropsSchema = z.object({
	selectedCases: z.array(z.string()),
	onClose: z.function().args().returns(z.void()),
	onSuccess: z.function().args().returns(z.void()),
	modelConfigs: z.array(ModelManagementDataSchema),
});

export type SynthesizerModalProps = z.infer<typeof SynthesizerModalPropsSchema>;

const SynthesizerModal = ({
	selectedCases,
	onClose,
	onSuccess,
	modelConfigs,
}: SynthesizerModalProps) => {
	const [synthesizerConfigs, setSynthesizerConfigs] = useState<Synthesizer[]>([]);
	const [isSynthesizerConfigModalOpen, setIsSynthesizerConfigModalOpen] =
		useState<boolean>(false);
	const [currentSynthesizer, setCurrentSynthesizer] = useState<Synthesizer>({
		name: "",
		debug: null,
	});
	const [selectedModels, setSelectedModels] = useState<{
		[key: string]: ModelManagementData;
	}>({});
	const { availableSynthesizers } = useFetchAvailableSynthesizers();

	const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		const evaluationData = {
			case_ids: selectedCases,
			metric_configs: synthesizerConfigs.map((metric) => ({
				type: metric.name,
				debug: metric.debug,
			})),
			model_configs: Object.values(selectedModels),
		};
		// Assuming createSynthesizer is a function to handle synthesizer creation
		const result = await createSynthesizer(evaluationData);
		if (result) {
			onSuccess();
		} else {
			alert("Failed to start synthesizer");
		}
	};

	const handleModelSelection = (model_id: string, modelType: string) => {
		const model = modelConfigs.find((model) => model.id === model_id);
		if (model) {
			setSelectedModels((prev) => ({
				...prev,
				[modelType]: model,
			}));
		}
	};

	const modelTypes = Array.from(
		new Set(modelConfigs.map((model) => model.model_type)),
	);

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
			<div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
				<h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">
					Run Synthesizer
				</h3>
				<form onSubmit={handleSubmit}>
					<div className="mb-4">
						<label className="block text-sm font-medium text-gray-700">
							Select Synthesizers
						</label>
						{availableSynthesizers.map((synthesizer) => (
							<div key={synthesizer.name} className="flex items-center">
								<input
									type="checkbox"
									id={synthesizer.name}
									onChange={(e) => {
										if (e.target.checked) {
											setSynthesizerConfigs([...synthesizerConfigs, synthesizer]);
										} else {
											setSynthesizerConfigs(
												synthesizerConfigs.filter((m) => m.name !== synthesizer.name),
											);
										}
									}}
								/>
								<label
									htmlFor={synthesizer.name}
									className="ml-2 cursor-pointer"
								// onClick={() => {
								// 	setCurrentSynthesizer(synthesizer);
								// 	setIsSynthesizerConfigModalOpen(true);
								// }}
								>
									{synthesizer.name}
								</label>
							</div>
						))}
					</div>
					<div className="mb-4">
						<label className="block text-sm font-medium text-gray-700">
							Model Configs
						</label>
						{modelTypes.map((type) => (
							<div key={type} className="mb-2">
								<h4 className="font-medium text-gray-800">{type}</h4>
								<select
									className="border rounded-md p-2"
									onChange={(e) => handleModelSelection(e.target.value, type)}
								>
									<option value="">Select a model</option>
									{modelConfigs
										.filter((model) => model.model_type === type)
										.map((model) => (
											<option key={model.id} value={model.id}>
												{model.model_name}
											</option>
										))}
								</select>
							</div>
						))}
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
							Start Synthesizer
						</button>
					</div>
				</form>
				{
					isSynthesizerConfigModalOpen && (
						<MetricConfigModal
							metric={currentSynthesizer}
							onClose={() => setIsSynthesizerConfigModalOpen(false)}
							onSave={(updatedMetric) => {
								setSynthesizerConfigs(
									synthesizerConfigs.map((m) =>
										m.name === updatedMetric.name ? updatedMetric : m,
									),
								);
								setIsSynthesizerConfigModalOpen(false);
							}}
						/>
					)
				}
			</div >
		</div >
	);
};

export default SynthesizerModal;
