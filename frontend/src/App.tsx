import { useEffect, useMemo, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LayoutShell } from "./components/Layout";
import { LiveContext } from "./context/LiveContext";
import { useLiveFeed } from "./hooks/useLiveFeed";
import { AnalyticsPage } from "./pages/Analytics";
import { Dashboard } from "./pages/Dashboard";
import { PersonDetails } from "./pages/PersonDetails";
import { SettingsPage } from "./pages/Settings";
import { api } from "./services/api";

export default function App() {
  const live = useLiveFeed();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [eventsToday, setEventsToday] = useState(0);
  const [peopleTotal, setPeopleTotal] = useState(0);

  useEffect(() => {
    api.analytics()
      .then((a) => {
        setEventsToday(a.events_today);
        setPeopleTotal(a.people_detected);
      })
      .catch(() => undefined);
  }, [live.events.length]);

  const value = useMemo(
    () => ({ ...live, selectedId, setSelectedId }),
    [live, selectedId],
  );

  const stats = {
    people: Math.max(peopleTotal, live.people.length),
    active: live.people.length,
    camera: live.frame ? (live.frame.demo_mode ? "DEMO" : "RUNNING") : "IDLE",
    fps: live.frame?.fps || 0,
    events: eventsToday + live.events.length,
    device: live.frame?.device || live.frame?.model_status?.device || "CPU",
    mic: live.frame?.microphone || "OFF",
    demo: Boolean(live.frame?.demo_mode),
  };

  return (
    <LiveContext.Provider value={value}>
      <BrowserRouter>
        <LayoutShell stats={stats}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/people/:personId" element={<PersonDetails />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </LayoutShell>
      </BrowserRouter>
    </LiveContext.Provider>
  );
}
