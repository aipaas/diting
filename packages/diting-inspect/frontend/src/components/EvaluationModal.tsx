import { useEffect, useState } from "react";
import { API_BASE } from "../constants";
import type {
	EvaluationModalProps,
	Metric,
	ModelManagementData,
} from "../schemas";
import MetricConfigModal from "./MetricConfigModal";

const EvaluationModal = ({
	selectedCases,
	onClose,
	onSuccess,
	modelConfigs,
}: EvaluationModalProps) => {
	const [metricConfigs, setMetricConfigs] = useState<Metric[]>([]);
	const [isMetricConfigModalOpen, setIsMetricConfigModalOpen] =
		useState<boolean>(false);
	const [currentMetric, setCurrentMetric] = useState<Metric>({
		name: "",
		threshold: null,
		debug: null,
	});
	const [availableMetrics, setAvailableMetrics] = useState<Array<Metric>>([]);
	const [selectedModels, setSelectedModels] = useState<{
		[key: string]: ModelManagementData;
	}>({});

	const fetchAvailableMetrics = async () => {
		try {
			const response = await fetch(`${API_BASE}/metrics_schemas`);
			if (response.ok) {
				const metrics = await response.json();
				setAvailableMetrics(metrics);
			} else {
				console.error("Failed to fetch available metrics");
			}
		} catch (error) {
			console.error("Error fetching available metrics:", error);
		}
	};

	useEffect(() => {
		fetchAvailableMetrics();
	}, []);

	const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		try {
			const response = await fetch(`${API_BASE}/evaluations`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					case_ids: selectedCases,
					metric_configs: metricConfigs.map((metric) => ({
						type: metric.name,
						threshold: metric.threshold,
						debug: metric.debug,
					})),
					model_configs: Object.values(selectedModels),
				}),
			});
			if (response.ok) {
				onSuccess();
			} else {
				alert("Failed to start evaluation");
			}
		} catch (_error) {
			alert("Error starting evaluation");
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
					Run Evaluation
				</h3>
				<form onSubmit={handleSubmit}>
					<div className="mb-4">
						<label className="block text-sm font-medium text-gray-700">
							Select Metrics
						</label>
						{availableMetrics.map((metric) => (
							<div key={metric.name} className="flex items-center">
								<input
									type="checkbox"
									id={metric.name}
									onChange={(e) => {
										if (e.target.checked) {
											setMetricConfigs([...metricConfigs, metric]);
										} else {
											setMetricConfigs(
												metricConfigs.filter((m) => m.name !== metric.name),
											);
										}
									}}
								/>
								<label
									htmlFor={metric.name}
									className="ml-2 cursor-pointer"
									onClick={() => {
										setCurrentMetric(metric);
										setIsMetricConfigModalOpen(true);
									}}
								>
									{metric.name}
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
							Start Evaluation
						</button>
					</div>
				</form>
				{isMetricConfigModalOpen && (
					<MetricConfigModal
						metric={currentMetric}
						onClose={() => setIsMetricConfigModalOpen(false)}
						onSave={(updatedMetric) => {
							setMetricConfigs(
								metricConfigs.map((m) =>
									m.name === updatedMetric.name ? updatedMetric : m,
								),
							);
							setIsMetricConfigModalOpen(false);
						}}
					/>
				)}
			</div>
		</div>
	);
};

export default EvaluationModal;
