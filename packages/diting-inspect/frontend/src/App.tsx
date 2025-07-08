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
	CaseSchema,
	EvaluationSchema,
	NotificationSchema,
	type CaseType,
	type EvaluationType,
	type NotificationType,
} from "./schemas";

const App = () => {
	const [cases, setCases] = useState<CaseType[]>([]);
	const [evaluations, setEvaluations] = useState<EvaluationType[]>([]);
	const [loading, setLoading] = useState<boolean>(false);
	const [activeTab, setActiveTab] = useState<string>("cases");
	const [selectedCases, setSelectedCases] = useState<string[]>([]);
	const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
	const [showEvaluationModal, setShowEvaluationModal] =
		useState<boolean>(false);
	const [searchTerm, setSearchTerm] = useState<string>("");
	const [notification, setNotification] = useState<NotificationType>(null);

	// Fetch data on component mount
	useEffect(() => {
		fetchCases();
		fetchEvaluations();
	}, []);

	const fetchCases = async () => {
		try {
			setLoading(true);
			const response = await fetch(`${API_BASE}/cases`);
			if (response.ok) {
				const data = await response.json();
				// Validate cases with Zod
				const parsedCases = data.map((caseData: CaseType) =>
					CaseSchema.parse(caseData),
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

	const filteredCases = cases.filter(
		(case_) =>
			case_.input.toLowerCase().includes(searchTerm.toLowerCase()) ||
			case_.actual_output.toLowerCase().includes(searchTerm.toLowerCase()),
	);

	return (
		<div className="min-h-screen bg-gray-50">
			{/* Header */}
			<Header setShowCreateModal={setShowCreateModal} />
			{/* Navigation Tabs */}
			<NavigationTabs activeTab={activeTab} setActiveTab={setActiveTab} />
			{/* Main Content */}
			<MainContent
				activeTab={activeTab}
				filteredCases={filteredCases}
				selectedCases={selectedCases}
				setSelectedCases={setSelectedCases}
				evaluations={evaluations}
				searchTerm={searchTerm}
				setSearchTerm={setSearchTerm}
				loading={loading}
				fetchCases={fetchCases}
				fetchEvaluations={fetchEvaluations}
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
						showNotification("Case created successfully!", "success");
					}}
				/>
			)}

			{showEvaluationModal && (
				<EvaluationModal
					selectedCases={selectedCases}
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
