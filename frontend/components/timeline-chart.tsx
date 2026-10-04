"use client";

import { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { TimelineSeries } from "@/lib/api";

// Mid-lightness hues that stay legible on both the light and dark backgrounds, one per series
// (the old 5-colour palette repeated across 7 series, and its darkest ink vanished in dark mode).
export const SERIES_COLORS = ["#C2563A", "#C79A2C", "#5C8F6A", "#4F7CAC", "#9B6BB0", "#C46E8F", "#6E9E9E", "#8A8F3C"];

/** One chart for series sharing a unit, so unlike scales (HbA1c ~6 vs blood pressure ~140) never share an axis. */
export function TimelineChart({ series, colorOffset = 0 }: { series: TimelineSeries[]; colorOffset?: number }) {
  const data = useMemo(() => {
    const byDate: Record<string, Record<string, string | number | null>> = {};
    for (const s of series) {
      for (const point of s.points) {
        byDate[point.observed_date] ??= { date: point.observed_date };
        byDate[point.observed_date][s.name] = point.value_numeric;
      }
    }
    return Object.values(byDate).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }, [series]);

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="date" stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="var(--muted-foreground)" fontSize={12} tickLine={false} axisLine={false} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", borderRadius: "8px" }}
            itemStyle={{ color: "var(--foreground)" }}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: "13px" }} />
          {series.map((s, i) => {
            const color = SERIES_COLORS[(colorOffset + i) % SERIES_COLORS.length];
            return (
              <Line
                key={s.name}
                type="monotone"
                dataKey={s.name}
                stroke={color}
                strokeWidth={3}
                dot={{ r: 4, fill: color, strokeWidth: 0 }}
                activeDot={{ r: 6 }}
                connectNulls
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
