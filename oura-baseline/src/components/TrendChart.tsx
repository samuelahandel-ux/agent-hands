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
          <CartesianGrid stroke="rgba(19,33,28,0.06)" vertical={false} />
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
            contentStyle={{ fontSize: 13 }}
            wrapperClassName="glass-tooltip"
          />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: 8 }} />
          <Line
            type="monotone"
            dataKey="readiness"
            name="Readiness"
            stroke="#1a7a6a"
            strokeWidth={2.4}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="sleepScore"
            name="Sleep"
            stroke="#c47a45"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="activityScore"
            name="Activity"
            stroke="#5a756c"
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
