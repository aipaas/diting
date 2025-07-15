import type { NavigationTabsProps } from "../schemas";

const NavigationTabs = ({ activeTab, setActiveTab }: NavigationTabsProps) => {
	return (
		<nav className="bg-white shadow-sm">
			<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<div className="flex space-x-4">
					{["cases", "evaluations", "models", "tools", "fileupload"].map(
						(tab) => (
							<button
								type={"button"}
								key={tab}
								onClick={() => setActiveTab(tab)}
								className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 ${
									activeTab === tab
										? "bg-white text-blue-600 shadow-sm"
										: "text-blue-600/70 hover:text-blue-600"
								}`}
							>
								{tab.charAt(0).toUpperCase() + tab.slice(1)}
							</button>
						),
					)}
				</div>
			</div>
		</nav>
	);
};

export default NavigationTabs;
