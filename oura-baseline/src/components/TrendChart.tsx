"use client";

import {
  CartesianGrid,
  Legend,
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

export function TrendChart({ days }: Props) {
  return (
    <div className="h-[320px] w-full">
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
          <YAxis
            domain={[40, 100]}
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
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: 8 }} />
          <Line
            type="monotone"
            dataKey="readiness"
            name="Readiness"
            stroke="#1f6f63"
            strokeWidth={2.2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="sleepScore"
            name="Sleep"
            stroke="#b86b3c"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="activityScore"
            name="Activity"
            stroke="#5c6b66"
            strokeWidth={1.6}
            strokeDasharray="4 4"
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
