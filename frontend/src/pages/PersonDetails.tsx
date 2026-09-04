import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { AttributePanel } from "../components/AttributePanel";
import { DigitalTwin } from "../components/DigitalTwin";
import { ObjectPanel } from "../components/ObjectPanel";
import { Timeline } from "../components/Timeline";
import { api } from "../services/api";
import { useLive } from "../context/LiveContext";
import type { DetectedObject, PersonLive, TimelineEvent } from "../types";

export function PersonDetails() {
  const { personId } = useParams();
  const { recon, people } = useLive();
  const [person, setPerson] = useState<PersonLive | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [objects, setObjects] = useState<DetectedObject[]>([]);
  const [zones, setZones] = useState<{ zone_id: string; duration_label: string }[]>([]);

  useEffect(() => {
    if (!personId) return;
    api.person(personId).then((p) => {
      setPerson(p as PersonLive);
      setObjects(((p as { objects?: DetectedObject[] }).objects || []) as DetectedObject[]);
      setZones(((p as { zone_history?: { zone_id: string; duration_label: string }[] }).zone_history || []) as { zone_id: string; duration_label: string }[]);
    });
    api.events(personId).then(setEvents);
  }, [personId]);

  const live = people.find((p) => p.person_id === personId) || person;
  const twin = personId ? recon[personId] : undefined;

  if (!personId) return null;
  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-wider text-muted">Person session</p>
          <h2 className="font-mono text-2xl text-accent">{personId}</h2>
        </div>
        <a className="text-xs text-accent underline" href={`/api/export/people/${personId}.json`}>
          Export session report
        </a>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <DigitalTwin reconstruction={twin} mode="xray" />
        </div>
        <div className="space-y-3">
          <div className="panel p-3 text-xs space-y-1">
            <div>First seen: {live?.first_seen ? new Date(live.first_seen).toLocaleString() : "—"}</div>
            <div>Last seen: {live?.last_seen ? new Date(live.last_seen).toLocaleString() : "—"}</div>
            <div>Duration: {live?.duration_label}</div>
            <div>Coverage: {Math.round(live?.reconstruction_coverage || twin?.coverage || 0)}%</div>
          </div>
          <AttributePanel attributes={live?.attributes} />
          <ObjectPanel objects={objects.length ? objects : live?.objects} />
          <div className="panel p-3">
            <h3 className="mb-2 text-[11px] uppercase text-muted">Zone history</h3>
            {zones.map((z) => (
              <div key={z.zone_id} className="flex justify-between text-xs">
                <span>{z.zone_id}</span>
                <span className="font-mono text-accent">{z.duration_label}</span>
              </div>
            ))}
            {!zones.length && <p className="text-xs text-muted">No zone dwell yet</p>}
          </div>
        </div>
      </div>
      <Timeline events={events} />
    </div>
  );
}
