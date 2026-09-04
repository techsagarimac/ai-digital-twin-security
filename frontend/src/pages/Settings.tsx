import { SettingsPanel } from "../components/Settings";

export function SettingsPage() {
  return (
    <div className="space-y-4">
      <p className="max-w-3xl text-sm text-muted">
        Configure detection thresholds, retention, and microphone consent. Identity recognition stays off unless
        explicitly authorized. This prototype does not infer race, health, emotion, criminality, or personality.
      </p>
      <SettingsPanel />
    </div>
  );
}
