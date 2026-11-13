"use client";

import { useEffect, useState } from "react";
import type { PoltergeistPayload, TelemetryEvent } from "@/lib/types";

export default function PoltergeistOverlay({ event, onDismiss }: { event: TelemetryEvent | null; onDismiss: () => void }) {
  const [shown, setShown] = useState("");
  const p = event?.payload as unknown as PoltergeistPayload | undefined;
  const text = p ? `> agent: translating ${p.cause} [${p.severity}]\n${p.latin}\n\n--- original ---\n${p.original}` : "";

  useEffect(() => {
    if (!text) {
      setShown("");
      return;
    }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setShown(text);
      return;
    }
    let i = 0;
    const t = setInterval(() => {
      i += 3;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(t);
    }, 20);
    return () => clearInterval(t);
  }, [text]);

  if (!event || !p) return null;

  return (
    <div className="poltergeist-overlay" role="alert">
      <div className="terminal">
        <div className="mb-2 flex justify-between">
          <strong>POLTERGEIST DETECTED</strong>
          <button className="btn" onClick={onDismiss}>Banish</button>
        </div>
        <pre>{shown}<span className="cursor">_</span></pre>
      </div>
    </div>
  );
}
