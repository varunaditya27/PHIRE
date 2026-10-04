"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";
import type { ProgressEvent } from "@/lib/api";

/** Seconds since this component mounted; keyed per step, so it restarts for each new stage. */
function Elapsed() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  return seconds >= 3 ? <span className="text-xs text-muted-foreground">{seconds}s</span> : null;
}

/** Live checklist of backend stages: finished steps get a check, the latest spins with an elapsed timer. */
export function ProgressSteps({ steps }: { steps: ProgressEvent[] }) {
  if (steps.length === 0) return null;
  return (
    <ul className="space-y-1.5 text-sm">
      {steps.map((step, i) => {
        const active = i === steps.length - 1;
        return (
          <li
            key={`${step.stage}-${i}`}
            className={active ? "flex items-center gap-2 text-foreground" : "flex items-center gap-2 text-muted-foreground"}
          >
            {active ? (
              <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-[var(--positive)] shrink-0" />
            )}
            <span>{step.message}</span>
            {active && <Elapsed />}
          </li>
        );
      })}
    </ul>
  );
}
