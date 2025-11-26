import { useState } from "react";
import TaskList from "./TaskList";
import EvaluatorManagement from "./evaluation/EvaluatorManagement";
import MetricManagement from "./evaluation/MetricManagement";

type TabType = "tasks" | "evaluators" | "metrics";

export default function Evaluation() {
  const [activeTab, setActiveTab] = useState<TabType>("tasks");

  const tabs = [
    { key: "tasks" as TabType, label: "评估任务", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" },
    { key: "evaluators" as TabType, label: "评估器", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" },
    { key: "metrics" as TabType, label: "评估维度", icon: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" },
  ];

  return (
    <div className="max-w-[1600px] mx-auto px-4 py-3 space-y-4">
      {/* Page title is intentionally hidden to reduce visual clutter while preserving a11y */}
      <h1 className="sr-only">评估任务</h1>

      {/* Tabs */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="border-b border-gray-200">
          <nav className="flex gap-2 px-4 pt-3">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                data-tab={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg font-medium text-sm transition-all ${
                  activeTab === tab.key
                    ? "bg-green-50 text-green-700 border-b-2 border-green-600"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d={tab.icon} />
                </svg>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-4">
          {activeTab === "tasks" && <TaskList />}
          {activeTab === "evaluators" && <EvaluatorManagement />}
          {activeTab === "metrics" && <MetricManagement />}
        </div>
      </div>
    </div>
  );
}
