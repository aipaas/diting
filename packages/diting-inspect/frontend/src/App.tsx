import './App.css';
import { useState, useEffect } from 'react';
import Header from './components/Header';
import NavigationTabs from './components/NavigationTabs';
import Notification from './components/Notification';
import CreateCaseModal from './components/CreateCaseModal';
import { API_BASE } from './constants';
import EvaluationModal from './components/EvaluationModal';
import MainContent from './components/MainContent';

const App = () => {
	const [cases, setCases] = useState([]);
	const [evaluations, setEvaluations] = useState([]);
	const [loading, setLoading] = useState(false);
	const [activeTab, setActiveTab] = useState('cases');
	const [selectedCases, setSelectedCases] = useState([]);
	const [showCreateModal, setShowCreateModal] = useState(false);
	const [showEvaluationModal, setShowEvaluationModal] = useState(false);
	const [searchTerm, setSearchTerm] = useState('');
	const [notification, setNotification] = useState(null);

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
				setCases(data);
			} else {
				showNotification('Failed to fetch cases', 'error');
			}
		} catch (error) {
			showNotification('Failed to fetch cases', 'error');
		} finally {
			setLoading(false);
		}
	};

	const fetchEvaluations = async () => {
		try {
			const response = await fetch(`${API_BASE}/evaluations`);
			if (response.ok) {
				const data = await response.json();
				setEvaluations(data);
			} else {
				console.error('Failed to fetch evaluations');
			}
		} catch (error) {
			console.error('Failed to fetch evaluations:', error);
		}
	};

	const showNotification = (message, type = 'info') => {
		setNotification({ message, type });
		setTimeout(() => setNotification(null), 3000);
	};

	const filteredCases = cases.filter(case_ =>
		case_.input.toLowerCase().includes(searchTerm.toLowerCase()) ||
		case_.actual_output.toLowerCase().includes(searchTerm.toLowerCase())
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
						showNotification('Case created successfully!', 'success');
					}}
				/>
			)}

			{showEvaluationModal && (
				<EvaluationModal
					selectedCases={selectedCases}
					onClose={() => setShowEvaluationModal(false)}
					onSuccess={() => {
						setShowEvaluationModal(false);
						showNotification('Evaluation started!', 'success');
						fetchEvaluations();
					}}
				/>
			)}

			{/* Notification */}
			{notification && (
				<Notification notification={notification} />
			)}
		</div>
	);
};

export default App;
