import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Analytics } from "../../types";

const axis = { fill: "#8ba0b5", fontSize: 11 };
const grid = { stroke: "#1e3a5f" };

export function AnalyticsCharts({ data }: { data: Analytics }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard title="People per hour">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data.people_per_hour}>
            <CartesianGrid {...grid} />
            <XAxis dataKey="hour" tick={axis} />
            <YAxis tick={axis} allowDecimals={false} />
            <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1e3a5f" }} />
            <Bar dataKey="count" fill="#3ee0c5" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Camera activity">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data.camera_activity}>
            <CartesianGrid {...grid} />
            <XAxis dataKey="hour" tick={axis} />
            <YAxis tick={axis} />
            <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1e3a5f" }} />
            <Line type="monotone" dataKey="frames" stroke="#6ea8fe" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Zone occupancy (visits)">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data.zone_occupancy}>
            <CartesianGrid {...grid} />
            <XAxis dataKey="zone" tick={axis} />
            <YAxis tick={axis} allowDecimals={false} />
            <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1e3a5f" }} />
            <Bar dataKey="visits" fill="#6ea8fe" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Detection events">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data.detection_events} layout="vertical">
            <CartesianGrid {...grid} />
            <XAxis type="number" tick={axis} />
            <YAxis type="category" dataKey="type" width={150} tick={axis} />
            <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1e3a5f" }} />
            <Bar dataKey="count" fill="#f5a524" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Object detections">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data.object_detections}>
            <CartesianGrid {...grid} />
            <XAxis dataKey="object" tick={axis} />
            <YAxis tick={axis} allowDecimals={false} />
            <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1e3a5f" }} />
            <Bar dataKey="count" fill="#3ee0c5" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Reconstruction coverage">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data.reconstruction_coverage}>
            <CartesianGrid {...grid} />
            <XAxis dataKey="person_id" tick={axis} />
            <YAxis tick={axis} domain={[0, 100]} />
            <Tooltip contentStyle={{ background: "#0d1524", border: "1px solid #1e3a5f" }} />
            <Bar dataKey="coverage" fill="#3ee0c5" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="panel p-3">
      <h3 className="mb-2 text-[11px] uppercase tracking-wider text-muted">{title}</h3>
      {children}
    </div>
  );
}
