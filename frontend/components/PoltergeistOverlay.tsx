"use client";

import { useEffect, useMemo, useState } from "react";
import { toPoltergeistPayload, type TelemetryEvent } from "@/lib/types";

export default function PoltergeistOverlay({ event, onDismiss }: { event: TelemetryEvent | null; onDismiss: () => void }) {
  const [shown, setShown] = useState("");
  const p = useMemo(() => (event ? toPoltergeistPayload(event) : null), [event]);
  const text = p
    ? `> agent: interpretans ${p.cause} [${p.severity}]\n${p.latin}\n\n--- original ---\n${p.original}`
    : "";

  useEffect(() => {
    if (!text) {
      setShown("");
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
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
      <div className="terminal backdrop-blur-md">
        <div className="mb-2 flex items-center justify-between">
          <strong className="tracking-widest">POLTERGEIST DETECTED // {p.cause.toUpperCase()}</strong>
          <button className="btn" onClick={onDismiss}>
            Banish
          </button>
        </div>
        <pre>
          {shown}
          <span className="cursor">_</span>
        </pre>
      </div>
    </div>
  );
}
