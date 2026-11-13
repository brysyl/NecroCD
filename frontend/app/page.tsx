"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import PoltergeistOverlay from "@/components/PoltergeistOverlay";
import { useTelemetry } from "@/lib/useTelemetry";
import type { Grave } from "@/lib/types";

const CemeteryCanvas = dynamic(() => import("@/components/CemeteryCanvas"), {
  ssr: false,
  loading: () => <p className="p-8 italic">Summoning the cemetery...</p>,
});

export default function Home() {
  const { graves, events, poltergeist, connected, mock, simulate, dismiss } = useTelemetry();
  const [selected, setSelected] = useState<Grave | null>(null);
  const [fullEvents, setFullEvents] = useState(false);

  return (
    <main className={`relative h-screen w-screen overflow-hidden ${poltergeist ? "shake" : ""}`}>
      <div className="absolute inset-0">
        <CemeteryCanvas graves={graves} onSelect={setSelected} haunted={!!poltergeist} />
      </div>

      <header className="pointer-events-none absolute left-0 top-0 p-6">
        <h1 className="title text-4xl">NecroCD</h1>
        <p className="italic opacity-80">A seance for abandoned branches</p>
        <p className="mt-2 text-sm">
          <span className={connected ? "text-sky-300" : "text-red-400"}>
            {connected ? "Spirits connected" : "Spirits silent"}
          </span>
          {mock && <span className="ml-2 opacity-70">(visions only: mock data)</span>}
        </p>
      </header>

      <aside className="parchment absolute bottom-4 left-4 w-80 p-4 text-sm">
        <h2 className="mb-2 font-bold">{selected ? selected.branch : "Select a gravestone"}</h2>
        {selected ? (
          <ul>
            <li>Status: {selected.status}</li>
            <li>Dormant: {selected.staleness_days} days</li>
            <li>Last commit: {selected.last_commit.slice(0, 8)}</li>
            <li>Findings: {selected.findings}</li>
          </ul>
        ) : (
          <p className="italic">Hover or click a stone to read its epitaph.</p>
        )}
      </aside>

      <aside className="parchment absolute right-4 top-4 max-h-64 w-72 overflow-auto p-4 text-xs">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-bold">Telemetry</h2>
          <button className="btn" onClick={() => setFullEvents((v) => !v)}>
            {fullEvents ? "less" : "more"}
          </button>
        </div>
        {events.slice(0, fullEvents ? 30 : 6).map((e) => (
          <div key={e.id} className="mb-1">
            <span className="opacity-60">{new Date(e.ts).toLocaleTimeString()}</span> {e.type}
          </div>
        ))}
        {events.length === 0 && <p className="italic">Silence.</p>}
        <button className="btn mt-3" onClick={simulate}>
          Simulate Poltergeist
        </button>
      </aside>

      <PoltergeistOverlay event={poltergeist} onDismiss={dismiss} />
    </main>
  );
}
