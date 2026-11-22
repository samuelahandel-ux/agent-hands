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
          <CartesianGrid stroke="rgba(26,36,33,0.08)" vertical={false} />
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
          <Tooltip
            contentStyle={{
              background: "rgba(255,255,255,0.92)",
              border: "1px solid rgba(26,36,33,0.12)",
              borderRadius: 0,
              fontSize: 13,
            }}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="hrv"
            name="HRV (ms)"
            stroke="#1f6f63"
            strokeWidth={2.2}
            dot={false}
            connectNulls
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="rhr"
            name="Lowest HR"
            stroke="#b86b3c"
            strokeWidth={1.8}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
