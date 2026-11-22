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
          <CartesianGrid stroke="rgba(26,36,33,0.08)" vertical={false} />
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
          <Tooltip
            contentStyle={{
              background: "rgba(255,255,255,0.92)",
              border: "1px solid rgba(26,36,33,0.12)",
              borderRadius: 0,
              fontSize: 13,
            }}
          />
          <Area
            type="monotone"
            dataKey="deep"
            name="Deep"
            stackId="1"
            stroke="#1f6f63"
            fill="#1f6f63"
            fillOpacity={0.55}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="rem"
            name="REM"
            stackId="1"
            stroke="#3d8f82"
            fill="#3d8f82"
            fillOpacity={0.45}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="light"
            name="Light"
            stackId="1"
            stroke="#8aaba4"
            fill="#a8c4be"
            fillOpacity={0.5}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
