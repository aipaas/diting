import CasesView from './CasesView';
import EvaluationsView from './EvaluationsView';
import FileUploadView from './FileUploadView';

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
}) => {
	return (
		<main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
			{activeTab === 'cases' && (
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

			{activeTab === 'evaluations' && (
				<EvaluationsView
					evaluations={evaluations}
					onRefresh={fetchEvaluations}
					showNotification={showNotification}
				/>
			)}

			{activeTab === 'fileupload' && (
				<FileUploadView onSuccess={fetchCases} />
			)}
		</main>
	);
};

export default MainContent;
