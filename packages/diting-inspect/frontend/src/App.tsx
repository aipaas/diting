import { useEffect, useState } from "react";
import "./App.css";
import CreateCaseModal from "./components/CreateCaseModal";
import EvaluationModal from "./components/EvaluationModal";
import Header from "./components/Header";
import MainContent from "./components/MainContent";
import NavigationTabs from "./components/NavigationTabs";
import Notification from "./components/Notification";
import { API_BASE } from "./constants";
import {
	EvaluationSchema,
	NotificationSchema,
	type CaseType,
	type EvaluationType,
	type ModelManagementData,
	type NotificationType,
} from "./schemas";
import CreateModelModual from "./components/CreateModelModual";

const App = () => {
	const [cases, setCases] = useState<CaseType[]>([]);
	const [evaluations, setEvaluations] = useState<EvaluationType[]>([]);
	const [models, setModels] = useState<ModelManagementData[]>([]);
	const [loading, setLoading] = useState<boolean>(false);
	const [activeTab, setActiveTab] = useState<string>("cases");
	const [selectedCases, setSelectedCases] = useState<string[]>([]);
	const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
	const [showEvaluationModal, setShowEvaluationModal] =
		useState<boolean>(false);
	const [showModelModal, setShowModelModal] = useState<boolean>(false);
	const [searchTerm, setSearchTerm] = useState<string>("");
	const [notification, setNotification] = useState<NotificationType>(null);

	// Fetch data on component mount
	useEffect(() => {
		fetchCases();
		fetchEvaluations();
		fetchModels();
	}, []);

	const fetchCases = async () => {
		try {
			setLoading(true);
			const response = await fetch(`${API_BASE}/cases`);
			if (response.ok) {
				const data = await response.json();
				// Validate cases with Zod
				const parsedCases = data.map((caseData: any) =>
					caseData,
				);
				setCases(parsedCases);
			} else {
				showNotification("Failed to fetch cases", "error");
			}
		} catch (_error) {
			showNotification("Failed to fetch cases", "error");
		} finally {
			setLoading(false);
		}
	};

	const fetchEvaluations = async () => {
		try {
			const response = await fetch(`${API_BASE}/evaluations`);
			if (response.ok) {
				const data = await response.json();
				// Validate evaluations with Zod
				const parsedEvaluations = data.map((evaluationData: EvaluationType) =>
					EvaluationSchema.parse(evaluationData),
				);
				setEvaluations(parsedEvaluations);
			} else {
				console.error("Failed to fetch evaluations");
			}
		} catch (error) {
			console.error("Failed to fetch evaluations:", error);
		}
	};

	const fetchModels = async () => {
		try {
			const response = await fetch(`${API_BASE}/models`);
			if (response.ok) {
				const data = await response.json();
				setModels(data);
			} else {
				console.error("Failed to fetch models");
			}
		} catch (error) {
			console.error("Failed to fetch models:", error);
		}
	};

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
		try {
			const response = await fetch(`${API_BASE}/models`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(modelData),
			});
			if (!response.ok) {
				throw new Error("Failed to create new model");
			}
			const createdModel = await response.json();

			if (modelData.is_default) {
				const defaultResponse = await fetch(
					`${API_BASE}/models/default/${modelData.model_type}/${createdModel.id}`,
					{
						method: "POST",
					},
				);
				if (!defaultResponse.ok) {
					throw new Error("Failed to set the model as default");
				}
			}

			showNotification("New model created successfully!", "success");
			setShowModelModal(false);
			setActiveTab("models")
			fetchModels();
		} catch (error) {
			showNotification(error.message, "error");
		}
	};

	const filteredCases = cases.filter(
		(case_) =>
			case_.input.toLowerCase().includes(searchTerm.toLowerCase()) ||
			case_.actual_output.toLowerCase().includes(searchTerm.toLowerCase()),
	);

	return (
		<div className="min-h-screen bg-gray-50">
			{/* Header */}
			<Header setShowCreateModal={setShowCreateModal} setShowModelModal={setShowModelModal} />
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
				searchTerm={searchTerm}
				setSearchTerm={setSearchTerm}
				loading={loading}
				fetchCases={fetchCases}
				fetchEvaluations={fetchEvaluations}
				fetchModels={fetchModels}
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
						setActiveTab("cases")
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
