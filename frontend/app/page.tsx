"use client";

import { useEffect, useState, useMemo } from "react";
import { api, TimelineResponse, ObservationRead } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Activity, Clock, FileText, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Dashboard() {
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [observations, setObservations] = useState<ObservationRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Try fetching both. If backend is empty, it might return empty arrays.
        const [timelineData, obsData] = await Promise.all([
          api.timeline.get(),
          api.observations.list(),
        ]);
        setTimeline(timelineData);
        setObservations(obsData);
      } catch (err: any) {
        setError(err.message || "Failed to load dashboard data. Ensure backend is running.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Transform timeline series into a flat array of data points for Recharts
  // Note: Recharts prefers an array of objects where each object is a point in time
  // { date: '2026-08-20', 'LDL Cholesterol': 162, 'Heart Rate': 72 }
  const chartData = useMemo(() => {
    if (!timeline?.series) return [];
    const dataByDate: Record<string, any> = {};
    timeline.series.forEach(series => {
      series.points.forEach(point => {
        if (!dataByDate[point.observed_date]) {
          dataByDate[point.observed_date] = { date: point.observed_date };
        }
        dataByDate[point.observed_date][series.name] = point.value_numeric;
      });
    });
    // Sort by date
    return Object.values(dataByDate).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [timeline]);

  // Generate colors for lines based on DESIGN.md palette (oxide, ochre, ink)
  const colors = ["#8C3F2B", "#96742A", "#55503F", "#7A755F", "#9C9782"];

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
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl tracking-tight text-foreground font-[family-name:var(--font-editorial)] font-medium">Patient Overview</h1>
        <p className="text-muted-foreground mt-1">Holistic view of health trends and recent observations.</p>
      </div>

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
            
            {chartData.length > 0 ? (
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="date" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', borderRadius: '8px' }}
                      itemStyle={{ color: 'var(--foreground)' }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '14px' }} />
                    {timeline?.series.map((series, idx) => (
                      <Line 
                        key={series.name}
                        type="monotone" 
                        dataKey={series.name} 
                        stroke={colors[idx % colors.length]} 
                        strokeWidth={3}
                        dot={{ r: 4, fill: colors[idx % colors.length], strokeWidth: 0 }}
                        activeDot={{ r: 6 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
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
              Recent Observations
            </h2>
            
            <div className="flex-1 overflow-y-auto pr-2 space-y-4 custom-scrollbar">
              {observations.length > 0 ? (
                observations.map((obs, i) => (
                  <div key={i} className="p-4 rounded-lg bg-card border border-border hover:border-primary/50 transition-colors shadow-sm">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-medium text-foreground">{obs.name}</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-secondary text-secondary-foreground uppercase tracking-wider font-semibold">
                        {obs.type}
                      </span>
                    </div>
                    <div className="text-2xl font-semibold text-foreground font-[family-name:var(--font-mono)]">
                      {obs.value} <span className="text-sm font-normal text-muted-foreground font-[family-name:var(--font-sans)]">{obs.unit}</span>
                    </div>
                    <div className="flex justify-between items-center mt-3 text-xs text-muted-foreground">
                      <span className="flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {obs.observed_date}
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
