import React from 'react';
import type { EvaluationType } from '../types/Evaluations'; // 导入评估类型

interface EvaluationReportModalProps {
	isOpen: boolean;
	onClose: () => void;
	evaluation: EvaluationType | null; // 评估数据可以为 null
}

interface RunLog {
	[key: string]: any; // 允许任意字段
}

interface Result {
	case_id: string;
	metric_name: string;
	score: number | null;
	error?: string;
	reason?: string | null;
	run_logs?: RunLog;
	evaluated_at: string;
}

interface EvaluationResultProps {
	result: Result;
}


const EvaluationResult: React.FC<EvaluationResultProps> = ({ result }) => {
	return (
		<div className="border p-4 mb-4 rounded shadow">
			<h3 className="font-bold">Metric: {result.metric_name}</h3>
			<p><strong>Case ID:</strong> {result.case_id}</p>
			<p><strong>Score:</strong> {result.score !== null ? result.score : 'N/A'}</p>
			{result.error && <p className="text-red-500"><strong>Error:</strong> {result.error}</p>}
			{result.reason && <p><strong>Reason:</strong> {result.reason}</p>}
			{result.run_logs && Object.keys(result.run_logs).length > 0 && ( // 检查 run_logs 是否存在且有内容
				<div>
					<h4 className="font-semibold">Run Logs:</h4>
					<pre>{JSON.stringify(result.run_logs, null, 2)}</pre> {/* 以 JSON 格式展示 */}
				</div>
			)}
			<p className="text-gray-500 text-sm">Evaluated At: {new Date(result.evaluated_at).toLocaleString()}</p>
		</div>
	);
};

const EvaluationReportModal: React.FC<EvaluationReportModalProps> = ({ isOpen, onClose, evaluation }) => {
	if (!isOpen || !evaluation) return null; // 如果模态框未打开或没有评估数据，则返回 null

	return (
		<div className="fixed inset-0 flex items-center justify-center z-50">
			<div className="fixed inset-0 bg-black opacity-50" onClick={onClose}></div>
			<div className="bg-white rounded-lg shadow-lg p-6 z-10 w-full max-w-3xl flex flex-col" style={{ maxHeight: '90vh' }}>
				<h2 className="text-lg font-bold mb-4">Evaluation Report</h2>
				<p><strong>ID:</strong> {evaluation.id}</p>
				<p><strong>Status:</strong> {evaluation.status}</p>
				<p><strong>Started At:</strong> {new Date(evaluation.started_at).toLocaleString()}</p>
				<p><strong>Completed At:</strong> {evaluation.completed_at ? new Date(evaluation.completed_at).toLocaleString() : "N/A"}</p>
				<h3 className="font-bold mt-4">Results:</h3>
				<div className="flex-1 overflow-y-auto"> {/* 允许内容区域垂直滚动 */}
					{evaluation.results.map((result, index) => (
						<EvaluationResult key={index} result={result} />
					))}
				</div>
				<button onClick={onClose} className="mt-4 bg-blue-500 text-white px-4 py-2 rounded">Close</button>
			</div>
		</div>
	);
};

export default EvaluationReportModal;
