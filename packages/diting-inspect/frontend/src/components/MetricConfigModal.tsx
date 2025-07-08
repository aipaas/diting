import { useState } from "react";
import type { Metric } from "../schemas";

interface MetricConfigModalProps {
	metric: Metric;
	onClose: () => void;
	onSave: (metric: Metric) => void;
}

const MetricConfigModal = ({
	metric,
	onClose,
	onSave,
}: MetricConfigModalProps) => {
	const [threshold, setThreshold] = useState(metric.threshold);
	const [debug, setDebug] = useState(metric.debug);

	const handleSave = () => {
		onSave({ ...metric, threshold, debug });
		onClose();
	};

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
			<div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
				<h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">
					Configure {metric.name}
				</h3>
				{threshold && (
					<div className="mb-4">
						<label
							className="block text-sm font-medium text-gray-700"
							htmlFor="threshold_input_id"
						>
							Threshold
						</label>
						<input
							id="threshold_input_id"
							type="number"
							value={threshold}
							onChange={(e) => setThreshold(parseFloat(e.target.value))}
							className="border border-gray-300 rounded-md p-2 w-full"
						/>
					</div>
				)}
				{debug !== null && (
					<div className="mb-4">
						<label className="flex items-center">
							<input
								type="checkbox"
								checked={debug}
								onChange={(e) => setDebug(e.target.checked)}
							/>
							<span className="ml-2">Enable Debug</span>
						</label>
					</div>
				)}
				<div className="flex justify-end space-x-3">
					<button
						type="button"
						onClick={onClose}
						className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={handleSave}
						className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
					>
						Save
					</button>
				</div>
			</div>
		</div>
	);
};

export default MetricConfigModal;
