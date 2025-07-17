import { useState, useRef, useEffect } from "react";
import { Plus } from "lucide-react";
import type { HeaderProps } from "../types/Headers";

const CreateDropdown = ({
	setShowCreateModal,
	setShowModelModal,
	setShowCreateToolConfig,
}: HeaderProps) => {
	const [isOpen, setIsOpen] = useState(false);
	const dropdownRef = useRef(null);

	const menuItems = [
		{
			id: "new-case",
			label: "New Case",
			icon: <Plus className="w-4 h-4" />,
			description: "Create a new case",
		},
		{
			id: "new-model",
			label: "New Model",
			icon: <Plus className="w-4 h-4" />,
			description: "Create a new model",
		},
		{
			id: "new-tool",
			label: "New Tool",
			icon: <Plus className="w-4 h-4" />,
			description: "Create a new tool",
		},
	];

	useEffect(() => {
		const handleClickOutside = (event) => {
			if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
				setIsOpen(false);
			}
		};

		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, []);

	useEffect(() => {
		const handleKeyDown = (event) => {
			if (event.key === "Escape") {
				setIsOpen(false);
			}
		};

		if (isOpen) {
			document.addEventListener("keydown", handleKeyDown);
			return () => document.removeEventListener("keydown", handleKeyDown);
		}
	}, [isOpen]);

	const handleItemClick = (item) => {
		if (item.id === "new-case") {
			setShowCreateModal(true);
		} else if (item.id === "new-model") {
			setShowModelModal(true);
		} else if (item.id === "new-tool") {
			setShowCreateToolConfig(true);
		}
		setIsOpen(false);
	};

	return (
		<div className="relative inline-block" ref={dropdownRef}>
			<button
				onClick={() => setIsOpen(!isOpen)}
				className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 border border-blue-600 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
				aria-expanded={isOpen}
				aria-haspopup="menu"
			>
				<Plus className="w-4 h-4" />
				<span className="hidden sm:inline"></span>
				<svg
					className={`w-3 h-3 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						strokeWidth={2}
						d="M19 9l-7 7-7-7"
					/>
				</svg>
			</button>

			{isOpen && (
				<div className="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
					<div className="py-1">
						{menuItems.map((item) => (
							<button
								key={item.id}
								onClick={() => handleItemClick(item)}
								className="w-full px-4 py-3 text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none transition-colors"
							>
								<div className="flex items-start gap-3">
									<div className="text-gray-500 mt-0.5">{item.icon}</div>
									<div className="flex-1">
										<div className="text-sm font-medium text-gray-900">
											{item.label}
										</div>
										<div className="text-xs text-gray-500 mt-0.5">
											{item.description}
										</div>
									</div>
								</div>
							</button>
						))}
					</div>
				</div>
			)}
		</div>
	);
};

const Header = ({
	setShowCreateModal,
	setShowModelModal,
	setShowCreateToolConfig,
}: HeaderProps) => {
	return (
		<header className="bg-white shadow-sm">
			<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
				<div className="flex items-center justify-between">
					<div className="flex items-center space-x-4">
						{/* <img src="/logo.png" alt="Logo" className="h-10 w-10" /> */}
						<h1 className="text-2xl font-bold text-gray-900">
							DiTing Inspect Tool
						</h1>
					</div>
					<CreateDropdown
						setShowCreateModal={setShowCreateModal}
						setShowModelModal={setShowModelModal}
						setShowCreateToolConfig={setShowCreateToolConfig}
					/>
				</div>
			</div>
		</header>
	);
};

export default Header;
