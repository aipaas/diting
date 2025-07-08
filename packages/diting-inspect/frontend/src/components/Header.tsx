import { Plus } from 'lucide-react';

const Header = ({ setShowCreateModal }) => {
	return (
		<header className="bg-white shadow-sm">
			<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
				<div className="flex items-center justify-between">
					<div className="flex items-center space-x-4">
						{ /* <img src="/logo.png" alt="Logo" className="h-10 w-10" /> */}
						<h1 className="text-2xl font-bold text-gray-900">DiTing Evaluation Tool</h1>
					</div>
					<button
						onClick={() => setShowCreateModal(true)}
						className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-shadow duration-200 shadow-lg hover:shadow-xl"
					>
						<Plus className="w-5 h-5 mr-2" />
						New Case
					</button>
				</div>
			</div>
		</header>
	);
};

export default Header;
