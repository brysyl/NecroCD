"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import PoltergeistOverlay from "@/components/PoltergeistOverlay";
import { useTelemetry } from "@/lib/useTelemetry";
import type { Grave } from "@/lib/types";

const CemeteryCanvas = dynamic(() => import("@/components/CemeteryCanvas"), {
  ssr: false,
  loading: () => <p className="p-8 text-emerald-400">Initializing cemetery render...</p>,
});

function Stat({ label, value, tone }: { label: string; value: string | number; tone?: "crimson" | "spectral" }) {
  const cls = tone === "crimson" ? "stat stat-crimson" : tone === "spectral" ? "stat stat-spectral" : "stat";
  return (
    <div className={cls}>
      <div className="text-[10px] uppercase tracking-widest text-zinc-400">{label}</div>
      <div className="text-xl font-bold text-zinc-100">{value}</div>
    </div>
  );
}

export default function Home() {
  const { graves, events, eventCount, poltergeist, connected, mock, simulate, dismiss } = useTelemetry();
  const [selected, setSelected] = useState<Grave | null>(null);
  const [fullEvents, setFullEvents] = useState(false);

  const broken = graves.filter((g) => g.status === "broken").length;
  const restable = graves.length - broken;

  return (
    <main className={`relative h-screen w-screen overflow-hidden ${poltergeist ? "shake" : ""}`}>
      <div className="absolute inset-0" data-testid="cemetery">
        <CemeteryCanvas graves={graves} selected={selected} onSelect={setSelected} haunted={!!poltergeist} />
      </div>

      <header className="glass absolute left-4 right-4 top-4 flex flex-wrap items-center gap-x-8 gap-y-3 px-5 py-3">
        <div>
          <h1 className="title text-2xl font-bold">NecroCD</h1>
          <p className="text-[11px] uppercase tracking-widest text-zinc-400">SRE control room // git graveyard</p>
        </div>
        <Stat label="Total graves" value={graves.length} />
        <Stat label="Broken / corrupted" value={broken} tone="crimson" />
        <Stat label="Restable" value={restable} tone="spectral" />
        <Stat label="Events received" value={eventCount} />
        <div className="ml-auto flex items-center gap-3 text-xs">
          <span className="flex items-center gap-2">
            <span className={`inline-block h-2.5 w-2.5 rounded-full ${connected ? "bg-emerald-400 shadow-[0_0_8px_#39ff14]" : "bg-red-600 shadow-[0_0_8px_#ff1100]"}`} />
            {connected ? "LINK ESTABLISHED" : "LINK SEVERED, RETRYING"}
          </span>
          {mock && <span className="rounded border border-amber-500/50 px-2 py-0.5 text-amber-300">MOCK DATA</span>}
        </div>
      </header>

      <aside className="glass absolute bottom-4 left-4 w-80 p-4 text-sm">
        <h2 className="mb-2 font-bold text-emerald-400">{selected ? selected.branch : "No grave selected"}</h2>
        {selected ? (
          <ul className="space-y-1">
            <li>
              Status:{" "}
              <span className={selected.status === "broken" ? "text-red-500" : "text-sky-400"}>
                {selected.status === "broken" ? "corrupted" : "restable"}
              </span>
            </li>
            <li>Dormant: {selected.staleness_days} days</li>
            <li>Last commit: {selected.last_commit.slice(0, 8)}</li>
            <li>Last commit date: {selected.last_commit_date}</li>
            <li>Findings: {selected.findings}</li>
          </ul>
        ) : (
          <p className="text-zinc-400">Click a gravestone to inspect it. Click empty ground to deselect. Drag to orbit, right-drag to pan.</p>
        )}
      </aside>

      <aside className="glass glass-crimson absolute bottom-4 right-4 max-h-64 w-80 overflow-auto p-4 text-xs">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-bold text-red-400">Telemetry feed</h2>
          <button className="btn" onClick={() => setFullEvents((v) => !v)}>
            {fullEvents ? "less" : "more"}
          </button>
        </div>
        {events.slice(0, fullEvents ? 30 : 6).map((e) => (
          <div key={e.id} className="mb-1">
            <span className="text-zinc-500">{new Date(e.ts).toLocaleTimeString()}</span>{" "}
            <span className={/poltergeist|fail|error/i.test(e.type) ? "text-red-400" : "text-emerald-300"}>{e.type}</span>
          </div>
        ))}
        {events.length === 0 && <p className="text-zinc-500">Awaiting signal...</p>}
        <button className="btn mt-3" onClick={simulate}>
          Simulate Poltergeist
        </button>
      </aside>

      <PoltergeistOverlay event={poltergeist} onDismiss={dismiss} />
    </main>
  );
}
