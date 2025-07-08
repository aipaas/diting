import type { CaseType, EvaluationType } from "../schemas";
import CasesView from "./CasesView";
import EvaluationsView from "./EvaluationsView";
import FileUploadView from "./FileUploadView";

interface MainContentProps {
	activeTab: string;
	filteredCases: CaseType[];
	selectedCases: string[];
	setSelectedCases: (cases: string[]) => void;
	evaluations: EvaluationType[];
	searchTerm: string;
	setSearchTerm: (term: string) => void;
	loading: boolean;
	fetchCases: () => Promise<void>;
	fetchEvaluations: () => Promise<void>;
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
	searchTerm,
	setSearchTerm,
	loading,
	fetchCases,
	fetchEvaluations,
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
		</main>
	);
};

export default MainContent;
