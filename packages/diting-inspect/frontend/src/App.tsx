import { useState } from "react";
import "./App.css";
import CreateCaseModal from "./components/CreateCaseModal";
import EvaluationModal from "./components/EvaluationModal";
import Header from "./components/Header";
import MainContent from "./components/MainContent";
import NavigationTabs from "./components/NavigationTabs";
import Notification from "./components/Notification";
import CreateModelModual from "./components/CreateModelModual";
import type { ModelManagementData } from "./types/Models";
import {
	NotificationSchema,
	type NotificationType,
} from "./types/Notification";
import useFetchCases from "./hooks/useFetchCases";
import useFilterCases from "./hooks/useFilterCases";
import useFetchModels from "./hooks/useFetchModels";
import useCreateModel from "./hooks/useCreateModel";
import useManageModels from "./hooks/useManageModels";
import useFetchEvaluations from "./hooks/useFetchEvaluations";
import useFetchToolConfigs from "./hooks/useFetchToolConfigs";

const App = () => {
	const { cases, loading: loadingCases, fetchCases } = useFetchCases();
	const { models, loading: loadingModels, fetchModels } = useFetchModels();
	const {
		evaluations,
		loading: loadingEvaluations,
		fetchEvaluations,
	} = useFetchEvaluations();
	const { createModel } = useCreateModel();
	const { setDefaultModel } = useManageModels();
	const {
		toolConfigs,
		loading: loadingToolConfigs,
		fetchToolConfigs,
	} = useFetchToolConfigs();
	const [activeTab, setActiveTab] = useState<string>("cases");
	const [selectedCases, setSelectedCases] = useState<string[]>([]);
	const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
	const [showEvaluationModal, setShowEvaluationModal] =
		useState<boolean>(false);
	const [showModelModal, setShowModelModal] = useState<boolean>(false);
	const { filteredCases, searchTerm, setSearchTerm } = useFilterCases(cases);
	const [notification, setNotification] = useState<NotificationType>(null);

	const showNotification = (
		message: string,
		type: "info" | "success" | "error" = "info",
	) => {
		const notificationData = NotificationSchema.safeParse({ message, type });
		if (notificationData.success) {
			setNotification(notificationData.data);
			setTimeout(() => setNotification(null), 3000);
		}
	};

	const handleAddNewModel = async (modelData: Partial<ModelManagementData>) => {
		const createdModel = await createModel(modelData);
		if (createdModel) {
			if (modelData.is_default) {
				await setDefaultModel(createdModel);
			}
			showNotification("New model created successfully!", "success");
			setShowModelModal(false);
			setActiveTab("models");
		} else {
			showNotification("Failed to create new model", "error");
		}
	};

	return (
		<div className="min-h-screen bg-gray-50">
			{/* Header */}
			<Header
				setShowCreateModal={setShowCreateModal}
				setShowModelModal={setShowModelModal}
			/>
			{/* Navigation Tabs */}
			<NavigationTabs activeTab={activeTab} setActiveTab={setActiveTab} />
			{/* Main Content */}
			<MainContent
				activeTab={activeTab}
				filteredCases={filteredCases}
				selectedCases={selectedCases}
				setSelectedCases={setSelectedCases}
				evaluations={evaluations}
				models={models}
				toolConfigs={toolConfigs}
				searchTerm={searchTerm}
				setSearchTerm={setSearchTerm}
				loading={
					loadingCases ||
					loadingModels ||
					loadingEvaluations ||
					loadingToolConfigs
				}
				fetchCases={fetchCases}
				fetchEvaluations={fetchEvaluations}
				fetchModels={fetchModels}
				fetchToolConfigs={fetchToolConfigs}
				showNotification={showNotification}
				setShowEvaluationModal={setShowEvaluationModal}
			/>
			{/* Modals */}
			{showCreateModal && (
				<CreateCaseModal
					onClose={() => setShowCreateModal(false)}
					onSuccess={() => {
						fetchCases();
						setShowCreateModal(false);
						setActiveTab("cases");
						showNotification("Case created successfully!", "success");
					}}
				/>
			)}

			{showModelModal && (
				<CreateModelModual
					isOpen={showModelModal}
					onClose={() => setShowModelModal(false)}
					onCreate={handleAddNewModel}
				/>
			)}

			{showEvaluationModal && (
				<EvaluationModal
					selectedCases={selectedCases}
					modelConfigs={models}
					onClose={() => setShowEvaluationModal(false)}
					onSuccess={() => {
						setShowEvaluationModal(false);
						showNotification("Evaluation started!", "success");
						fetchEvaluations();
					}}
				/>
			)}

			{/* Notification */}
			{notification && <Notification notification={notification} />}
		</div>
	);
};

export default App;
