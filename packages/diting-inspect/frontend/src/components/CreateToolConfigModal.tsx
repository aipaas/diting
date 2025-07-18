import { useState } from "react";
import {
	Plus,
	Trash2,
	Save,
	X,
	Play,
	CheckCircle,
	XCircle,
	Clock,
	AlertCircle,
} from "lucide-react";

interface CreateToolConfigModalPros {
	isOpen: boolean;
	onClose: () => void;
	onCreate: (tool) => void;
	initialTool: any;
}

const CreateToolConfigModal = ({
	isOpen,
	onClose,
	onCreate,
	initialTool = null,
}: CreateToolConfigModalPros) => {
	const [tool, setTool] = useState(
		initialTool || {
			name: "",
			type: "http",
			config: {
				method: "GET",
				url: "",
				headers: [],
				params: [],
				body: "",
				timeout: 30000,
				retries: 3,
				authentication: {
					type: "none",
					credentials: {},
				},
				schema: {
					request: "",
					response: "",
				},
			},
		},
	);

	const [testingTool, setTestingTool] = useState(false);
	const [testResult, setTestResult] = useState(null);

	const httpMethods = [
		"GET",
		"POST",
		"PUT",
		"DELETE",
		"PATCH",
		"HEAD",
		"OPTIONS",
	];
	const authTypes = ["none", "bearer", "basic", "api-key", "oauth2"];

	const handleSave = () => {
		if (tool.name.trim() && tool.config.url.trim()) {
			onCreate(tool);
		}
	};

	const addKeyValuePair = (type, key = "", value = "") => {
		const updated = { ...tool };
		updated.config[type].push({ key, value, id: Date.now() });
		setTool(updated);
	};

	const updateKeyValuePair = (type, pairId, key, value) => {
		const updated = { ...tool };
		const pairIndex = updated.config[type].findIndex((p) => p.id === pairId);
		if (pairIndex !== -1) {
			updated.config[type][pairIndex] = {
				...updated.config[type][pairIndex],
				key,
				value,
			};
			setTool(updated);
		}
	};

	const removeKeyValuePair = (type, pairId) => {
		const updated = { ...tool };
		updated.config[type] = updated.config[type].filter((p) => p.id !== pairId);
		setTool(updated);
	};

	const buildRequestOptions = (toolConfig) => {
		const options = {
			method: toolConfig.config.method,
			headers: {},
		};

		// Add headers
		toolConfig.config.headers.forEach((header) => {
			if (header.key && header.value) {
				options.headers[header.key] = header.value;
			}
		});

		// Add authentication
		if (
			toolConfig.config.authentication.type === "bearer" &&
			toolConfig.config.authentication.credentials.token
		) {
			options.headers["Authorization"] =
				`Bearer ${toolConfig.config.authentication.credentials.token}`;
		} else if (
			toolConfig.config.authentication.type === "basic" &&
			toolConfig.config.authentication.credentials.username
		) {
			const credentials = btoa(
				`${toolConfig.config.authentication.credentials.username}:${toolConfig.config.authentication.credentials.password || ""}`,
			);
			options.headers["Authorization"] = `Basic ${credentials}`;
		} else if (
			toolConfig.config.authentication.type === "api-key" &&
			toolConfig.config.authentication.credentials.apiKey
		) {
			const headerName =
				toolConfig.config.authentication.credentials.headerName || "X-API-Key";
			options.headers[headerName] =
				toolConfig.config.authentication.credentials.apiKey;
		}

		// Add body for non-GET requests
		if (toolConfig.config.method !== "GET" && toolConfig.config.body) {
			options.body = toolConfig.config.body;
		}

		return options;
	};

	const buildUrl = (toolConfig) => {
		let url = toolConfig.config.url;

		// Add query parameters
		if (toolConfig.config.params.length > 0) {
			const params = new URLSearchParams();
			toolConfig.config.params.forEach((param) => {
				if (param.key && param.value) {
					params.append(param.key, param.value);
				}
			});
			const queryString = params.toString();
			if (queryString) {
				url += (url.includes("?") ? "&" : "?") + queryString;
			}
		}

		return url;
	};

	const executeHttpRequest = async () => {
		setTestingTool(true);
		setTestResult({
			status: "loading",
			startTime: Date.now(),
			data: null,
			error: null,
		});

		try {
			const url = buildUrl(tool);
			const options = buildRequestOptions(tool);

			const controller = new AbortController();
			const timeoutId = setTimeout(
				() => controller.abort(),
				tool.config.timeout,
			);

			const response = await fetch(url, {
				...options,
				signal: controller.signal,
			});

			clearTimeout(timeoutId);

			let responseData;
			const contentType = response.headers.get("content-type");

			if (contentType && contentType.includes("application/json")) {
				responseData = await response.json();
			} else {
				responseData = await response.text();
			}

			const result = {
				status: response.ok ? "success" : "error",
				startTime: Date.now(),
				data: {
					status: response.status,
					statusText: response.statusText,
					headers: Object.fromEntries(response.headers.entries()),
					body: responseData,
					url: url,
					requestOptions: options,
				},
				error: response.ok
					? null
					: `HTTP ${response.status}: ${response.statusText}`,
			};

			setTestResult(result);
		} catch (error) {
			const result = {
				status: "error",
				startTime: Date.now(),
				data: null,
				error: error.name === "AbortError" ? "Request timeout" : error.message,
			};

			setTestResult(result);
		} finally {
			setTestingTool(false);
		}
	};

	const getStatusIcon = (status) => {
		switch (status) {
			case "loading":
				return <Clock className="animate-spin text-blue-500" size={16} />;
			case "success":
				return <CheckCircle className="text-green-500" size={16} />;
			case "error":
				return <XCircle className="text-red-500" size={16} />;
			default:
				return <AlertCircle className="text-gray-400" size={16} />;
		}
	};

	const KeyValueEditor = ({ type, title }) => (
		<div className="space-y-2">
			<div className="flex justify-between items-center">
				<label className="text-sm font-medium text-gray-700">{title}</label>
				<button
					onClick={() => addKeyValuePair(type)}
					className="text-blue-600 hover:text-blue-800"
				>
					<Plus size={16} />
				</button>
			</div>
			{tool.config[type].map((pair) => (
				<div key={pair.id} className="flex gap-2 items-center">
					<input
						type="text"
						placeholder="Key"
						value={pair.key}
						onChange={(e) =>
							updateKeyValuePair(type, pair.id, e.target.value, pair.value)
						}
						className="flex-1 px-3 py-1 border border-gray-300 rounded-md text-sm"
					/>
					<input
						type="text"
						placeholder="Value"
						value={pair.value}
						onChange={(e) =>
							updateKeyValuePair(type, pair.id, pair.key, e.target.value)
						}
						className="flex-1 px-3 py-1 border border-gray-300 rounded-md text-sm"
					/>
					<button
						onClick={() => removeKeyValuePair(type, pair.id)}
						className="text-red-600 hover:text-red-800"
					>
						<Trash2 size={16} />
					</button>
				</div>
			))}
		</div>
	);

	const AuthenticationConfig = () => (
		<div className="space-y-3">
			<label className="text-sm font-medium text-gray-700">
				Authentication
			</label>
			<select
				value={tool.config.authentication.type}
				onChange={(e) => {
					const updated = { ...tool };
					updated.config.authentication.type = e.target.value;
					updated.config.authentication.credentials = {};
					setTool(updated);
				}}
				className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
			>
				{authTypes.map((type) => (
					<option key={type} value={type}>
						{type}
					</option>
				))}
			</select>

			{tool.config.authentication.type === "bearer" && (
				<input
					type="password"
					placeholder="Bearer Token"
					value={tool.config.authentication.credentials.token || ""}
					onChange={(e) => {
						const updated = { ...tool };
						updated.config.authentication.credentials.token = e.target.value;
						setTool(updated);
					}}
					className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
				/>
			)}

			{tool.config.authentication.type === "basic" && (
				<div className="grid grid-cols-2 gap-2">
					<input
						type="text"
						placeholder="Username"
						value={tool.config.authentication.credentials.username || ""}
						onChange={(e) => {
							const updated = { ...tool };
							updated.config.authentication.credentials.username =
								e.target.value;
							setTool(updated);
						}}
						className="px-3 py-2 border border-gray-300 rounded-md text-sm"
					/>
					<input
						type="password"
						placeholder="Password"
						value={tool.config.authentication.credentials.password || ""}
						onChange={(e) => {
							const updated = { ...tool };
							updated.config.authentication.credentials.password =
								e.target.value;
							setTool(updated);
						}}
						className="px-3 py-2 border border-gray-300 rounded-md text-sm"
					/>
				</div>
			)}

			{tool.config.authentication.type === "api-key" && (
				<div className="grid grid-cols-2 gap-2">
					<input
						type="text"
						placeholder="Header Name"
						value={tool.config.authentication.credentials.headerName || ""}
						onChange={(e) => {
							const updated = { ...tool };
							updated.config.authentication.credentials.headerName =
								e.target.value;
							setTool(updated);
						}}
						className="px-3 py-2 border border-gray-300 rounded-md text-sm"
					/>
					<input
						type="password"
						placeholder="API Key"
						value={tool.config.authentication.credentials.apiKey || ""}
						onChange={(e) => {
							const updated = { ...tool };
							updated.config.authentication.credentials.apiKey = e.target.value;
							setTool(updated);
						}}
						className="px-3 py-2 border border-gray-300 rounded-md text-sm"
					/>
				</div>
			)}
		</div>
	);

	const TestResultsPanel = () => {
		if (!testResult) return null;

		return (
			<div className="mt-4 p-4 bg-gray-50 rounded-lg">
				<div className="flex items-center gap-2 mb-3">
					{getStatusIcon(testResult.status)}
					<h4 className="font-medium">Test Results</h4>
				</div>

				{testResult.status === "loading" && (
					<p className="text-blue-600">Executing request...</p>
				)}

				{testResult.status === "error" && (
					<div className="text-red-600">
						<p className="font-medium">Error:</p>
						<p className="text-sm">{testResult.error}</p>
					</div>
				)}

				{testResult.status === "success" && testResult.data && (
					<div className="space-y-3">
						<div className="grid grid-cols-2 gap-4 text-sm">
							<div>
								<span className="font-medium">Status:</span>{" "}
								{testResult.data.status} {testResult.data.statusText}
							</div>
							<div>
								<span className="font-medium">URL:</span> {testResult.data.url}
							</div>
						</div>

						<div>
							<h5 className="font-medium mb-2">Response Headers:</h5>
							<pre className="bg-white p-2 rounded border text-xs overflow-x-auto">
								{JSON.stringify(testResult.data.headers, null, 2)}
							</pre>
						</div>

						<div>
							<h5 className="font-medium mb-2">Response Body:</h5>
							<pre className="bg-white p-2 rounded border text-xs overflow-x-auto max-h-40 overflow-y-auto">
								{typeof testResult.data.body === "string"
									? testResult.data.body
									: JSON.stringify(testResult.data.body, null, 2)}
							</pre>
						</div>
					</div>
				)}
			</div>
		);
	};

	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
			<div className="relative top-20 mx-auto p-5 border max-w-full w-auto shadow-lg rounded-md bg-white">
				<h2 className="text-lg font-medium leading-6 text-gray-900 mb-4">
					{initialTool ? "Edit Tool Configuration" : "Create New Tool"}
				</h2>
				<div className="flex justify-between items-center mb-6">
					<div className="flex gap-2">
						<button
							onClick={executeHttpRequest}
							disabled={testingTool || !tool.config.url}
							className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
						>
							<Play size={16} />
							Test
						</button>
						<button
							onClick={onClose}
							className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
						>
							<X size={16} />
							Cancel
						</button>
						<button
							onClick={handleSave}
							disabled={!tool.name.trim() || !tool.config.url.trim()}
							className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
						>
							<Save size={16} />
							{initialTool ? "Update" : "Create"}
						</button>
					</div>
				</div>

				<div className="space-y-6">
					{/* Basic Configuration */}
					<div className="bg-gray-50 p-4 rounded-lg">
						<h2 className="text-lg font-semibold mb-4">Basic Configuration</h2>
						<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
							<div>
								<label className="block text-sm font-medium text-gray-700 mb-1">
									Tool Name
								</label>
								<input
									type="text"
									value={tool.name}
									onChange={(e) => setTool({ ...tool, name: e.target.value })}
									className="w-full px-3 py-2 border border-gray-300 rounded-md"
									placeholder="Enter tool name"
								/>
							</div>
							<div>
								<label className="block text-sm font-medium text-gray-700 mb-1">
									Type
								</label>
								<select
									value={tool.type}
									onChange={(e) => setTool({ ...tool, type: e.target.value })}
									className="w-full px-3 py-2 border border-gray-300 rounded-md"
								>
									<option value="http">HTTP Client</option>
									<option value="webhook">Webhook</option>
									<option value="api">API Gateway</option>
								</select>
							</div>
						</div>
					</div>

					{/* HTTP Configuration */}
					<div className="bg-white border border-gray-200 rounded-lg p-4">
						<h2 className="text-lg font-semibold mb-4">HTTP Configuration</h2>
						<div className="space-y-4">
							<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
								<div>
									<label className="block text-sm font-medium text-gray-700 mb-1">
										HTTP Method
									</label>
									<select
										value={tool.config.method}
										onChange={(e) =>
											setTool({
												...tool,
												config: { ...tool.config, method: e.target.value },
											})
										}
										className="w-full px-3 py-2 border border-gray-300 rounded-md"
									>
										{httpMethods.map((method) => (
											<option key={method} value={method}>
												{method}
											</option>
										))}
									</select>
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700 mb-1">
										URL
									</label>
									<input
										type="url"
										value={tool.config.url}
										onChange={(e) =>
											setTool({
												...tool,
												config: { ...tool.config, url: e.target.value },
											})
										}
										className="w-full px-3 py-2 border border-gray-300 rounded-md"
										placeholder="https://api.example.com/endpoint"
									/>
								</div>
							</div>

							<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
								<div>
									<label className="block text-sm font-medium text-gray-700 mb-1">
										Timeout (ms)
									</label>
									<input
										type="number"
										value={tool.config.timeout}
										onChange={(e) =>
											setTool({
												...tool,
												config: {
													...tool.config,
													timeout: parseInt(e.target.value),
												},
											})
										}
										className="w-full px-3 py-2 border border-gray-300 rounded-md"
									/>
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700 mb-1">
										Retries
									</label>
									<input
										type="number"
										value={tool.config.retries}
										onChange={(e) =>
											setTool({
												...tool,
												config: {
													...tool.config,
													retries: parseInt(e.target.value),
												},
											})
										}
										className="w-full px-3 py-2 border border-gray-300 rounded-md"
									/>
								</div>
							</div>

							<KeyValueEditor type="headers" title="Headers" />
							<KeyValueEditor type="params" title="Query Parameters" />

							<AuthenticationConfig />

							<div>
								<label className="block text-sm font-medium text-gray-700 mb-1">
									Request Body
								</label>
								<textarea
									value={tool.config.body}
									onChange={(e) =>
										setTool({
											...tool,
											config: { ...tool.config, body: e.target.value },
										})
									}
									className="w-full px-3 py-2 border border-gray-300 rounded-md"
									rows="4"
									placeholder='{"app_id": "9dab3804-ffff-4f78-9199-5e4f72467ba1","stream":false,"query":"{{user_input}}"}'
								/>
							</div>

							<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
								<div>
									<label className="block text-sm font-medium text-gray-700 mb-1">
										Request Schema
									</label>
									<textarea
										value={tool.config.schema.request}
										onChange={(e) =>
											setTool({
												...tool,
												config: {
													...tool.config,
													schema: {
														...tool.config.schema,
														request: e.target.value,
													},
												},
											})
										}
										className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
										rows="3"
										placeholder="JSON Schema for request validation"
									/>
								</div>
								<div>
									<label className="block text-sm font-medium text-gray-700 mb-1">
										Response Schema
									</label>
									<textarea
										value={tool.config.schema.response}
										onChange={(e) =>
											setTool({
												...tool,
												config: {
													...tool.config,
													schema: {
														...tool.config.schema,
														response: e.target.value,
													},
												},
											})
										}
										className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
										rows="3"
										placeholder="{{body}}"
									/>
								</div>
							</div>
						</div>
					</div>

					<TestResultsPanel />
				</div>
			</div>
		</div>
	);
};

export default CreateToolConfigModal;
