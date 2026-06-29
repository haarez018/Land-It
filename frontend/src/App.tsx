import { Route, Routes, Navigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import Jobs from "./pages/Jobs";
import Tailor from "./pages/Tailor";
import Pitcher from "./pages/Pitcher";
import Coach from "./pages/Coach";
import Tracker from "./pages/Tracker";
import Planner from "./pages/Planner";
import Analytics from "./pages/Analytics";
import Onboarding from "./pages/Onboarding";
import Demo from "./pages/Demo";
import Auth from "./pages/Auth";
import AuthCallback from "./pages/AuthCallback";
import AuthGuard from "./components/shared/AuthGuard";
import { useThemeStore } from "./store/useThemeStore";
import { useAuthStore } from "./store/useAuthStore";
import Layout from "./components/cockpit/Layout";
import CenterStage from "./components/cockpit/CenterStage";

function LayoutRoutes() {
  const [searchParams] = useSearchParams();
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);

  const appIdParam = searchParams.get("app");
  const activeAppId = appIdParam || selectedAppId;

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/pipeline" replace />} />
        <Route
          path="/pipeline"
          element={
            <CenterStage
              filter={null}
              selectedAppId={activeAppId}
              onSelectApp={(id) => setSelectedAppId(id)}
            />
          }
        />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/tailor" element={<Tailor />} />
        <Route path="/pitcher" element={<Pitcher />} />
        <Route path="/coach" element={<Coach />} />
        <Route path="/tracker" element={<Tracker />} />
        <Route path="/planner" element={<Planner />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/onboarding" element={<Onboarding />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  const theme = useThemeStore((s) => s.theme);
  const initialize = useAuthStore((s) => s.initialize);

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/auth" element={<Auth />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/demo" element={<Demo />} />

      {/* Protected routes wrapped in Layout */}
      <Route
        path="/*"
        element={
          <AuthGuard>
            <LayoutRoutes />
          </AuthGuard>
        }
      />
    </Routes>
  );
}
