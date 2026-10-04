"use client";

import { useEffect, useState, useMemo } from "react";
import { api, TimelineResponse, TimelineSeries, ObservationRead } from "@/lib/api";
import { TimelineChart } from "@/components/timeline-chart";
import { latestPerMetric, splitReading } from "@/lib/readings";
import Link from "next/link";
import { Activity, Clock, FileText, AlertCircle, CalendarClock } from "lucide-react";

export default function Dashboard() {
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [observations, setObservations] = useState<ObservationRead[]>([]);
  const [needDate, setNeedDate] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Try fetching both. If backend is empty, it might return empty arrays.
        const [timelineData, obsData, docs] = await Promise.all([
          api.timeline.get(),
          api.observations.list(),
          api.documents.list(),
        ]);
        setTimeline(timelineData);
        setObservations(obsData);
        setNeedDate(docs.filter((d) => d.needs_date).length);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data. Ensure backend is running.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Series with no numeric reading (e.g. the compound "148/92" blood pressure, whose systolic/diastolic
  // components are charted instead) have nothing to draw. The rest are grouped by unit, one chart each.
  const unitGroups = useMemo(() => {
    const groups = new Map<string, TimelineSeries[]>();
    for (const s of timeline?.series ?? []) {
      if (!s.points.some((p) => p.value_numeric !== null)) continue;
      const unit = s.points.find((p) => p.unit)?.unit ?? "value";
      groups.set(unit, [...(groups.get(unit) ?? []), s]);
    }
    return [...groups.entries()];
  }, [timeline]);

  const latest = useMemo(() => latestPerMetric(observations), [observations]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center text-muted-foreground">
          <Activity className="h-12 w-12 mb-4 text-muted-foreground" />
          <p>Loading patient data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl tracking-tight text-foreground font-[family-name:var(--font-editorial)] font-medium">Patient Overview</h1>
        <p className="text-muted-foreground mt-1">Holistic view of health trends and recent observations.</p>
      </div>

      {needDate > 0 && (
        <Link
          href="/documents"
          className="flex items-center gap-2 rounded-lg border border-[var(--warning,#C79A2C)] bg-[var(--warning-soft,rgba(199,154,44,0.12))] p-3 text-sm text-foreground hover:opacity-90"
        >
          <CalendarClock className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
          {needDate === 1 ? "1 document needs a date" : `${needDate} documents need a date`} — its readings are shown at the
          upload date until you confirm it. Add it on the Documents page.
        </Link>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900 flex items-start">
          <AlertCircle className="h-5 w-5 text-red-500 mr-3 mt-0.5" />
          <div className="text-red-700 dark:text-red-400 text-sm">{error}</div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card rounded-xl p-6 shadow-sm border border-border">
            <h2 className="text-xl font-semibold mb-6 flex items-center text-foreground">
              <Activity className="w-5 h-5 mr-2 text-foreground" />
              Health Timeline
            </h2>
            
            {unitGroups.length > 0 ? (
              <div className="space-y-8">
                {unitGroups.map(([unit, series], i) => (
                  <div key={unit}>
                    <p className="text-xs tracking-wider text-muted-foreground mb-2">{unit}</p>
                    <TimelineChart
                      series={series}
                      colorOffset={unitGroups.slice(0, i).reduce((n, [, g]) => n + g.length, 0)}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[400px] flex items-center justify-center text-muted-foreground bg-muted/30 rounded-lg border border-dashed border-border">
                No timeline data available. Upload a medical document to generate trends.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-card rounded-xl p-6 shadow-sm border border-border h-[500px] flex flex-col">
            <h2 className="text-xl font-semibold mb-4 flex items-center text-foreground">
              <FileText className="w-5 h-5 mr-2 text-foreground" />
              Latest Readings
            </h2>
            
            <div className="flex-1 overflow-y-auto pr-2 space-y-4 custom-scrollbar">
              {latest.length > 0 ? (
                latest.map((obs) => (
                  <div key={obs.id} className="p-4 rounded-lg bg-card border border-border hover:border-primary/50 transition-colors shadow-sm">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-medium text-foreground">{obs.name}</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-secondary text-secondary-foreground uppercase tracking-wider font-semibold">
                        {obs.type}
                      </span>
                    </div>
                    <div className="text-2xl font-semibold text-foreground font-[family-name:var(--font-mono)]">
                      {splitReading(obs).main}{" "}
                      <span className="text-sm font-normal text-muted-foreground font-[family-name:var(--font-sans)]">{splitReading(obs).unit}</span>
                    </div>
                    <div className="flex justify-between items-center mt-3 text-xs text-muted-foreground">
                      <span className="flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {obs.observed_date ?? "undated"}
                      </span>
                      {obs.interpretation && (
                        <span className="px-2 py-0.5 rounded text-xs bg-surface-subtle text-foreground border border-border">
                          {obs.interpretation}
                        </span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  No observations found.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
