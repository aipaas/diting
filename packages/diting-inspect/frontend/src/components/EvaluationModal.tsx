import { useState } from 'react';
import { API_BASE } from '../constants';
import MetricConfigModal from './MetricConfigModal';

const EvaluationModal = ({ selectedCases, onClose, onSuccess }) => {
	const [metricConfigs, setMetricConfigs] = useState([]);
	const [isMetricConfigModalOpen, setIsMetricConfigModalOpen] = useState(false);
	const [currentMetric, setCurrentMetric] = useState(null);

	const availableMetrics = [
		{ name: 'exact_match', threshold: 1.0, debug: false },
		{ name: 'levenshtein', threshold: 0.8, debug: false },
		{ name: 'token_overlap', threshold: 0.7, debug: false },
		{ name: 'length_ratio', threshold: 0.7, debug: false },
	];

	const handleSubmit = async (e) => {
		e.preventDefault();
		try {
			const response = await fetch(`${API_BASE}/evaluations`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					case_ids: selectedCases,
					metric_configs: metricConfigs.map((metric) => ({
						type: metric.name,
						threshold: metric.threshold,
						debug: metric.debug,
					})),
				}),
			});
			if (response.ok) {
				onSuccess();
			} else {
				alert('Failed to start evaluation');
			}
		} catch (error) {
			alert('Error starting evaluation');
		}
	};

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
			<div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
				<h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Run Evaluation</h3>
				<form onSubmit={handleSubmit}>
					<div className="mb-4">
						<label className="block text-sm font-medium text-gray-700">Select Metrics</label>
						{availableMetrics.map((metric) => (
							<div key={metric.name} className="flex items-center">
								<input
									type="checkbox"
									id={metric.name}
									onChange={(e) => {
										if (e.target.checked) {
											setMetricConfigs([...metricConfigs, metric]);
										} else {
											setMetricConfigs(metricConfigs.filter((m) => m.name !== metric.name));
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
							setMetricConfigs(metricConfigs.map((m) => (m.name === updatedMetric.name ? updatedMetric : m)));
							setIsMetricConfigModalOpen(false);
						}}
					/>
				)}
			</div>
		</div>
	);
};

export default EvaluationModal;
