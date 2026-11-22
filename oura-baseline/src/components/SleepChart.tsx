"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DayPoint } from "@/lib/types";

type Props = {
  days: DayPoint[];
};

export function SleepChart({ days }: Props) {
  const data = days.map((d) => ({
    ...d,
    deep: d.deepHours,
    rem: d.remHours,
    light: d.lightHours,
  }));

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="rgba(19,33,28,0.06)" vertical={false} />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            minTickGap={28}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 12 }}
            unit="h"
          />
          <Tooltip contentStyle={{ fontSize: 13 }} wrapperClassName="glass-tooltip" />
          <Area
            type="monotone"
            dataKey="deep"
            name="Deep"
            stackId="1"
            stroke="#1a7a6a"
            fill="#1a7a6a"
            fillOpacity={0.5}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="rem"
            name="REM"
            stackId="1"
            stroke="#3d9a8a"
            fill="#3d9a8a"
            fillOpacity={0.4}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="light"
            name="Light"
            stackId="1"
            stroke="#8eb8ae"
            fill="#b5d4cc"
            fillOpacity={0.45}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
