"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DayPoint } from "@/lib/types";

type Props = {
  days: DayPoint[];
};

export function HrvChart({ days }: Props) {
  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={days} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="rgba(19,33,28,0.06)" vertical={false} />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            minTickGap={28}
            tick={{ fontSize: 12 }}
          />
          <YAxis yAxisId="left" tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
          <YAxis
            yAxisId="right"
            orientation="right"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 12 }}
          />
          <Tooltip contentStyle={{ fontSize: 13 }} wrapperClassName="glass-tooltip" />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="hrv"
            name="HRV (ms)"
            stroke="#1a7a6a"
            strokeWidth={2.4}
            dot={false}
            connectNulls
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="rhr"
            name="Lowest HR"
            stroke="#c47a45"
            strokeWidth={1.8}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
