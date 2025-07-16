import { z } from "zod";

// HTTP Methods enum
const HttpMethod = z.enum([
	"GET",
	"POST",
	"PUT",
	"DELETE",
	"PATCH",
	"HEAD",
	"OPTIONS",
]);

// Authentication types enum
const AuthType = z.enum(["none", "bearer", "basic", "api-key", "oauth2"]);

// Key-value pair schema for headers and parameters
const KeyValuePair = z.object({
	id: z.number(),
	key: z.string(),
	value: z.string(),
});

// Authentication credentials schemas
const NoAuthCredentials = z.object({});

const BearerCredentials = z.object({
	token: z.string().optional(),
});

const BasicCredentials = z.object({
	username: z.string().optional(),
	password: z.string().optional(),
});

const ApiKeyCredentials = z.object({
	apiKey: z.string().optional(),
	headerName: z.string().optional(),
});

const OAuth2Credentials = z.object({
	clientId: z.string().optional(),
	clientSecret: z.string().optional(),
	authUrl: z.string().url().optional(),
	tokenUrl: z.string().url().optional(),
	scope: z.string().optional(),
	accessToken: z.string().optional(),
	refreshToken: z.string().optional(),
});

// Authentication schema with discriminated union
const Authentication = z.discriminatedUnion("type", [
	z.object({
		type: z.literal("none"),
		credentials: NoAuthCredentials,
	}),
	z.object({
		type: z.literal("bearer"),
		credentials: BearerCredentials,
	}),
	z.object({
		type: z.literal("basic"),
		credentials: BasicCredentials,
	}),
	z.object({
		type: z.literal("api-key"),
		credentials: ApiKeyCredentials,
	}),
	z.object({
		type: z.literal("oauth2"),
		credentials: OAuth2Credentials,
	}),
]);

// Schema validation for request/response
const SchemaConfig = z.object({
	request: z.string().optional(),
	response: z.string().optional(),
});

// HTTP tool configuration schema
const HttpToolConfig = z.object({
	method: HttpMethod,
	url: z.string().url().or(z.string().min(1, "URL is required")),
	headers: z.array(KeyValuePair).default([]),
	params: z.array(KeyValuePair).default([]),
	body: z.string().optional(),
	timeout: z.number().int().min(1000).max(300000).default(30000), // 1s to 5min
	retries: z.number().int().min(0).max(10).default(3),
	authentication: Authentication.default({ type: "none", credentials: {} }),
	schema: SchemaConfig.default({ request: "", response: "" }),
});

// Tool types enum
const ToolType = z.enum(["http", "webhook", "api"]);

// Base tool schema
const BaseTool = z.object({
	id: z.number(),
	name: z.string().min(1, "Tool name is required"),
	type: ToolType,
});

// HTTP tool schema
const HttpTool = BaseTool.extend({
	type: z.literal("http"),
	config: HttpToolConfig,
});

// Future tool types can be added here
const WebhookTool = BaseTool.extend({
	type: z.literal("webhook"),
	config: z.object({
		// Webhook-specific configuration
		endpoint: z.string().url(),
		secret: z.string().optional(),
		events: z.array(z.string()).default([]),
	}),
});

const ApiTool = BaseTool.extend({
	type: z.literal("api"),
	config: z.object({
		// API Gateway-specific configuration
		baseUrl: z.string().url(),
		version: z.string().default("v1"),
		rateLimits: z
			.object({
				requestsPerSecond: z.number().positive().default(10),
				requestsPerMinute: z.number().positive().default(100),
			})
			.default({ requestsPerSecond: 10, requestsPerMinute: 100 }),
	}),
});

// Discriminated union for all tool types
const Tool = z.discriminatedUnion("type", [HttpTool, WebhookTool, ApiTool]);

// Test result status enum
const TestStatus = z.enum(["loading", "success", "error", "idle"]);

// HTTP response data schema
const HttpResponseData = z.object({
	status: z.number(),
	statusText: z.string(),
	headers: z.record(z.string()),
	body: z.unknown(),
	url: z.string(),
	requestOptions: z.object({
		method: z.string(),
		headers: z.record(z.string()),
		body: z.string().optional(),
	}),
});

// Test result schema
const TestResult = z.object({
	status: TestStatus,
	startTime: z.number(),
	data: HttpResponseData.nullable(),
	error: z.string().nullable(),
});

// New tool form schema (for validation before creation)
const NewToolForm = z.object({
	name: z.string().min(1, "Tool name is required"),
	type: ToolType,
	config: z.unknown(), // Will be validated based on type
});

// Tools collection schema
const ToolsCollection = z.array(Tool);

// Test results collection schema
const TestResultsCollection = z.record(z.string(), TestResult);

// Application state schema
const AppState = z.object({
	tools: ToolsCollection,
	editingTool: Tool.nullable(),
	testingTool: z.number().nullable(),
	testResults: TestResultsCollection,
	newTool: NewToolForm,
});

// Export all schemas
export {
	HttpMethod,
	AuthType,
	KeyValuePair,
	Authentication,
	HttpToolConfig,
	ToolType,
	Tool,
	HttpTool,
	WebhookTool,
	ApiTool,
	TestStatus,
	TestResult,
	NewToolForm,
	ToolsCollection,
	TestResultsCollection,
	AppState,
};

// Export types
export type HttpMethodType = z.infer<typeof HttpMethod>;
export type AuthTypeType = z.infer<typeof AuthType>;
export type KeyValuePairType = z.infer<typeof KeyValuePair>;
export type AuthenticationType = z.infer<typeof Authentication>;
export type HttpToolConfigType = z.infer<typeof HttpToolConfig>;
export type ToolTypeType = z.infer<typeof ToolType>;
export type ToolType = z.infer<typeof Tool>;
export type HttpToolType = z.infer<typeof HttpTool>;
export type TestStatusType = z.infer<typeof TestStatus>;
export type TestResultType = z.infer<typeof TestResult>;
export type NewToolFormType = z.infer<typeof NewToolForm>;
export type AppStateType = z.infer<typeof AppState>;

// Validation helpers
export const validateTool = (tool: unknown): tool is ToolType => {
	try {
		Tool.parse(tool);
		return true;
	} catch {
		return false;
	}
};

export const validateHttpTool = (tool: unknown): tool is HttpToolType => {
	try {
		HttpTool.parse(tool);
		return true;
	} catch {
		return false;
	}
};

export const validateNewToolForm = (form: unknown): form is NewToolFormType => {
	try {
		NewToolForm.parse(form);
		return true;
	} catch {
		return false;
	}
};

// Schema validation functions that return results
export const parseToolSafely = (tool: unknown) => {
	return Tool.safeParse(tool);
};

export const parseHttpToolSafely = (tool: unknown) => {
	return HttpTool.safeParse(tool);
};

export const parseNewToolFormSafely = (form: unknown) => {
	return NewToolForm.safeParse(form);
};

// Default values
export const defaultHttpToolConfig: HttpToolConfigType = {
	method: "GET",
	url: "",
	headers: [],
	params: [],
	body: "",
	timeout: 30000,
	retries: 3,
	authentication: { type: "none", credentials: {} },
	schema: { request: "", response: "" },
};

export const defaultNewTool: NewToolFormType = {
	name: "",
	type: "http",
	config: defaultHttpToolConfig,
};

// Example usage and validation
export const createHttpTool = (
	id: number,
	name: string,
	config: Partial<HttpToolConfigType> = {},
): HttpToolType => {
	const fullConfig = { ...defaultHttpToolConfig, ...config };

	return HttpTool.parse({
		id,
		name,
		type: "http",
		config: fullConfig,
	});
};

// URL validation helper
export const isValidUrl = (url: string): boolean => {
	try {
		new URL(url);
		return true;
	} catch {
		return false;
	}
};

// Authentication validation helpers
export const validateAuthentication = (auth: unknown) => {
	return Authentication.safeParse(auth);
};

// Custom validation functions
export const validateTimeout = (timeout: number): boolean => {
	return timeout >= 1000 && timeout <= 300000;
};

export const validateRetries = (retries: number): boolean => {
	return retries >= 0 && retries <= 10;
};

export const validateJsonSchema = (schema: string): boolean => {
	if (!schema.trim()) return true; // Empty schema is valid
	try {
		JSON.parse(schema);
		return true;
	} catch {
		return false;
	}
};

// Error handling utilities
export const getValidationErrors = (
	result: z.SafeParseReturnType<any, any>,
) => {
	if (result.success) return [];
	return result.error.issues.map((issue) => ({
		path: issue.path.join("."),
		message: issue.message,
	}));
};
