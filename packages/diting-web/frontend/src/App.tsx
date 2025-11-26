import { Routes, Route, Navigate } from "react-router-dom";
import { UserProvider } from "./contexts/UserContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Synthesis from "./pages/Synthesis";
import Datasets from "./pages/Datasets";
import DatasetDetail from "./pages/DatasetDetail";
import TaskDetail from "./pages/TaskDetail";
import Prompts from "./pages/Prompts";
import Optimization from "./pages/Optimization";
import Models from "./pages/Models";
import TasksPage from "./pages/evaluation/TasksPage";
import EvaluatorsPage from "./pages/evaluation/EvaluatorsPage";
import MetricsPage from "./pages/evaluation/MetricsPage";
import { Users } from "./pages/Users";
import ErrorBoundary from "./components/ErrorBoundary";

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = localStorage.getItem("isAuthenticated") === "true";
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}

export default function App() {
  return (
    <ErrorBoundary>
      <UserProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          
          {/* Protected routes */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            
            {/* Admin Only Routes */}
            <Route path="/users" element={<Users />} />
            
            {/* Evaluation */}
            <Route path="/evaluation" element={<Navigate to="/evaluation/tasks" replace />} />
            <Route path="/evaluation/tasks" element={<TasksPage />} />
            <Route path="/evaluation/evaluators" element={<EvaluatorsPage />} />
            <Route path="/evaluation/metrics" element={<MetricsPage />} />
            
            {/* Synthesis */}
            <Route path="/synthesis" element={<Navigate to="/synthesis/generation" replace />} />
            <Route path="/synthesis/generation" element={<Synthesis defaultTab="generation" />} />
            <Route path="/synthesis/hard-negative" element={<Synthesis defaultTab="hard_negative" />} />
            <Route path="/synthesis/distillation" element={<Synthesis defaultTab="distillation" />} />
            
            {/* Resources */}
            <Route path="/datasets" element={<Datasets />} />
            <Route path="/datasets/:datasetId" element={<DatasetDetail />} />
            <Route path="/tasks/:taskId" element={<TaskDetail />} />
            <Route path="/prompts" element={<Prompts />} />
            <Route path="/optimization" element={<Optimization />} />
            <Route path="/models" element={<Models />} />
          </Route>
        </Routes>
      </UserProvider>
    </ErrorBoundary>
  );
}
