import type { CaseType } from "../types/Cases";
import type { EvaluationType } from "../types/Evaluations";
import type { ModelManagementData } from "../types/Models";
import type { HttpToolType } from "../types/Tools";
import CasesView from "./CasesView";
import EvaluationsView from "./EvaluationsView";
import FileUploadView from "./FileUploadView";
import ModelsView from "./ModelsView";
import ToolConfigsView from "./ToolConfigsView";

interface MainContentProps {
	activeTab: string;
	filteredCases: CaseType[];
	selectedCases: string[];
	setSelectedCases: (cases: string[]) => void;
	evaluations: EvaluationType[];
	models: ModelManagementData[];
	toolConfigs: HttpToolType[];
	searchTerm: string;
	setSearchTerm: (term: string) => void;
	loading: boolean;
	fetchCases: () => Promise<void>;
	fetchEvaluations: () => Promise<void>;
	fetchModels: () => Promise<void>;
	fetchToolConfigs: () => Promise<void>;
	showNotification: (
		message: string,
		type?: "info" | "success" | "error",
	) => void;
	setShowEvaluationModal: (show: boolean) => void;
}

const MainContent = ({
	activeTab,
	filteredCases,
	selectedCases,
	setSelectedCases,
	evaluations,
	models,
	toolConfigs,
	searchTerm,
	setSearchTerm,
	loading,
	fetchCases,
	fetchEvaluations,
	fetchModels,
	fetchToolConfigs,
	showNotification,
	setShowEvaluationModal,
}: MainContentProps) => {
	return (
		<main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
			{activeTab === "cases" && (
				<CasesView
					cases={filteredCases}
					selectedCases={selectedCases}
					setSelectedCases={setSelectedCases}
					searchTerm={searchTerm}
					setSearchTerm={setSearchTerm}
					loading={loading}
					onRefresh={fetchCases}
					onEvaluate={() => setShowEvaluationModal(true)}
					showNotification={showNotification}
				/>
			)}

			{activeTab === "evaluations" && (
				<EvaluationsView
					evaluations={evaluations}
					onRefresh={fetchEvaluations}
					showNotification={showNotification}
				/>
			)}

			{activeTab === "fileupload" && <FileUploadView onSuccess={fetchCases} />}

			{activeTab === "models" && (
				<ModelsView
					models={models}
					onRefresh={fetchModels}
					showNotification={showNotification}
				/>
			)}

			{activeTab === "tools" && (
				<ToolConfigsView
					toolConfigs={toolConfigs}
					onRefresh={fetchToolConfigs}
					showNotification={showNotification}
				/>
			)}
		</main>
	);
};

export default MainContent;
