import { format, parseISO } from "date-fns";
import type {
  Analytics,
  DayPoint,
  Insight,
  OuraBundle,
  SleepSession,
  Trend,
} from "./types";

function avg(nums: number[]): number | null {
  if (!nums.length) return null;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function round1(n: number | null): number | null {
  if (n == null || Number.isNaN(n)) return null;
  return Math.round(n * 10) / 10;
}

function bedtimeHour(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  let h = d.getHours() + d.getMinutes() / 60;
  if (h < 12) h += 24;
  return h;
}

function primarySleep(sessions: SleepSession[]): SleepSession | null {
  const long = sessions.filter((s) => s.type === "long_sleep" || !s.type);
  if (!long.length) return sessions[0] ?? null;
  return long.reduce((best, cur) =>
    (cur.total_sleep_duration ?? 0) > (best.total_sleep_duration ?? 0) ? cur : best,
  );
}

function mapByDay<T extends { day: string }>(rows: T[]): Map<string, T> {
  const map = new Map<string, T>();
  for (const row of rows) map.set(row.day, row);
  return map;
}

function trendOf(values: (number | null)[]): Trend {
  const clean = values.filter((v): v is number => v != null);
  if (clean.length < 4) {
    return { direction: "flat", delta: null, label: "Not enough data" };
  }
  const half = Math.floor(clean.length / 2);
  const first = avg(clean.slice(0, half));
  const second = avg(clean.slice(half));
  if (first == null || second == null) {
    return { direction: "flat", delta: null, label: "Stable" };
  }
  const delta = round1(second - first);
  if (delta == null) return { direction: "flat", delta: null, label: "Stable" };
  if (Math.abs(delta) < 1.2) return { direction: "flat", delta, label: "Stable" };
  if (delta > 0) return { direction: "up", delta, label: `+${delta} vs earlier half` };
  return { direction: "down", delta, label: `${delta} vs earlier half` };
}

function stdDev(values: number[]): number | null {
  if (values.length < 2) return null;
  const mean = avg(values);
  if (mean == null) return null;
  const variance = avg(values.map((v) => (v - mean) ** 2));
  return variance == null ? null : Math.sqrt(variance);
}

export function buildDayPoints(bundle: OuraBundle): DayPoint[] {
  const sleepMap = mapByDay(bundle.dailySleep);
  const readyMap = mapByDay(bundle.dailyReadiness);
  const actMap = mapByDay(bundle.dailyActivity);
  const stressMap = mapByDay(bundle.stress);
  const spo2Map = mapByDay(bundle.spo2);
  const resMap = mapByDay(bundle.resilience);

  const sessionsByDay = new Map<string, SleepSession[]>();
  for (const s of bundle.sleep) {
    const list = sessionsByDay.get(s.day) ?? [];
    list.push(s);
    sessionsByDay.set(s.day, list);
  }

  const days = new Set<string>([
    ...sleepMap.keys(),
    ...readyMap.keys(),
    ...actMap.keys(),
    ...sessionsByDay.keys(),
  ]);

  return [...days]
    .sort()
    .map((day) => {
      const session = primarySleep(sessionsByDay.get(day) ?? []);
      return {
        day,
        label: format(parseISO(day), "MMM d"),
        readiness: readyMap.get(day)?.score ?? null,
        sleepScore: sleepMap.get(day)?.score ?? null,
        activityScore: actMap.get(day)?.score ?? null,
        hrv: session?.average_hrv ?? null,
        rhr: session?.lowest_heart_rate ?? null,
        sleepHours: session?.total_sleep_duration
          ? session.total_sleep_duration / 3600
          : null,
        deepHours: session?.deep_sleep_duration
          ? session.deep_sleep_duration / 3600
          : null,
        remHours: session?.rem_sleep_duration
          ? session.rem_sleep_duration / 3600
          : null,
        lightHours: session?.light_sleep_duration
          ? session.light_sleep_duration / 3600
          : null,
        efficiency: session?.efficiency ?? null,
        bedtimeHour: bedtimeHour(session?.bedtime_start),
        steps: actMap.get(day)?.steps ?? null,
        activeCalories: actMap.get(day)?.active_calories ?? null,
        tempDeviation: readyMap.get(day)?.temperature_deviation ?? null,
        stressHigh: stressMap.get(day)?.stress_high ?? null,
        recoveryHigh: stressMap.get(day)?.recovery_high ?? null,
        spo2: spo2Map.get(day)?.spo2_percentage?.average ?? null,
        resilience: resMap.get(day)?.level ?? null,
      };
    });
}

function buildInsights(
  days: DayPoint[],
  sleepDebtHours: number,
  consistencyMin: number | null,
  correlations: Analytics["correlations"],
  trends: Analytics["trends"],
): Insight[] {
  const insights: Insight[] = [];

  if (trends.hrv.direction === "up") {
    insights.push({
      id: "hrv-up",
      title: "HRV is climbing",
      body: `Overnight HRV averaged higher in the second half of this window (${trends.hrv.label}). Recovery capacity looks to be improving.`,
      tone: "positive",
    });
  } else if (trends.hrv.direction === "down") {
    insights.push({
      id: "hrv-down",
      title: "HRV is softening",
      body: `Overnight HRV drifted lower (${trends.hrv.label}). Watch load, alcohol, and late nights for the next few days.`,
      tone: "watch",
    });
  }

  if (sleepDebtHours > 3) {
    insights.push({
      id: "sleep-debt",
      title: `${round1(sleepDebtHours)}h sleep debt`,
      body: "Cumulative shortfall versus a 7.5h target. A couple of earlier nights will clear this faster than one long catch-up sleep.",
      tone: "watch",
    });
  } else if (sleepDebtHours < -2) {
    insights.push({
      id: "sleep-surplus",
      title: "Sleep bank is healthy",
      body: `You're about ${round1(Math.abs(sleepDebtHours))}h ahead of a 7.5h nightly target across this range.`,
      tone: "positive",
    });
  }

  if (consistencyMin != null) {
    if (consistencyMin <= 35) {
      insights.push({
        id: "bedtime-steady",
        title: "Bedtime is consistent",
        body: `Bedtime variance is ~${Math.round(consistencyMin)} minutes. That regularity usually shows up in readiness more than raw sleep duration.`,
        tone: "positive",
      });
    } else if (consistencyMin >= 70) {
      insights.push({
        id: "bedtime-drift",
        title: "Bedtime is drifting",
        body: `Bedtime swings by ~${Math.round(consistencyMin)} minutes. Tightening the window often lifts readiness before sleep score does.`,
        tone: "watch",
      });
    }
  }

  if (correlations.lateBedtimeReadinessDelta != null) {
    const d = correlations.lateBedtimeReadinessDelta;
    if (d <= -4) {
      insights.push({
        id: "late-bed",
        title: "Late nights cost readiness",
        body: `Days after a bedtime past midnight average ${Math.abs(round1(d) ?? d)} points lower readiness than earlier nights.`,
        tone: "watch",
      });
    }
  }

  if (correlations.highStepsReadinessDelta != null) {
    const d = correlations.highStepsReadinessDelta;
    if (d >= 3) {
      insights.push({
        id: "steps-help",
        title: "Movement supports recovery",
        body: `Higher-step days are followed by about +${round1(d)} readiness the next morning versus quieter days.`,
        tone: "positive",
      });
    } else if (d <= -3) {
      insights.push({
        id: "steps-tax",
        title: "High load may be catching up",
        body: `Busier step days are followed by about ${round1(d)} readiness the next morning. Ease evening intensity when scores are already low.`,
        tone: "watch",
      });
    }
  }

  const recent = days.slice(-7);
  const lowReady = recent.filter((d) => (d.readiness ?? 100) < 70).length;
  if (lowReady >= 3) {
    insights.push({
      id: "ready-cluster",
      title: "Readiness cluster below 70",
      body: `${lowReady} of the last 7 mornings landed under 70. Treat this as a recovery block, not a motivation problem.`,
      tone: "watch",
    });
  }

  if (!insights.length) {
    insights.push({
      id: "steady",
      title: "Signals look steady",
      body: "No sharp pattern jumps in this window. Keep the same sleep window and watch HRV if training load rises.",
      tone: "neutral",
    });
  }

  return insights.slice(0, 5);
}

export function analyze(bundle: OuraBundle): Analytics {
  const days = buildDayPoints(bundle);
  const latest = days[days.length - 1] ?? null;

  const averages = {
    readiness: round1(avg(days.map((d) => d.readiness).filter((v): v is number => v != null))),
    sleepScore: round1(
      avg(days.map((d) => d.sleepScore).filter((v): v is number => v != null)),
    ),
    hrv: round1(avg(days.map((d) => d.hrv).filter((v): v is number => v != null))),
    rhr: round1(avg(days.map((d) => d.rhr).filter((v): v is number => v != null))),
    sleepHours: round1(
      avg(days.map((d) => d.sleepHours).filter((v): v is number => v != null)),
    ),
    steps: round1(avg(days.map((d) => d.steps).filter((v): v is number => v != null))),
  };

  const trends = {
    readiness: trendOf(days.map((d) => d.readiness)),
    sleepScore: trendOf(days.map((d) => d.sleepScore)),
    hrv: trendOf(days.map((d) => d.hrv)),
    rhr: trendOf(days.map((d) => d.rhr)),
  };

  const sleepHours = days
    .map((d) => d.sleepHours)
    .filter((v): v is number => v != null);
  const sleepDebtHours =
    sleepHours.reduce((sum, h) => sum + (7.5 - h), 0);

  const bedtimeHours = days
    .map((d) => d.bedtimeHour)
    .filter((v): v is number => v != null);
  const bedtimeConsistencyMinutes =
    bedtimeHours.length >= 4 ? (stdDev(bedtimeHours) ?? 0) * 60 : null;

  const weekdayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const weekday = weekdayNames.map((name, idx) => {
    const subset = days.filter((d) => parseISO(d.day).getUTCDay() === idx);
    return {
      day: name,
      readiness: round1(
        avg(subset.map((d) => d.readiness).filter((v): v is number => v != null)),
      ),
      sleepHours: round1(
        avg(subset.map((d) => d.sleepHours).filter((v): v is number => v != null)),
      ),
    };
  });

  const late = days.filter((d) => (d.bedtimeHour ?? 0) >= 24);
  const early = days.filter((d) => (d.bedtimeHour ?? 99) < 23.5);
  const lateReady = avg(late.map((d) => d.readiness).filter((v): v is number => v != null));
  const earlyReady = avg(early.map((d) => d.readiness).filter((v): v is number => v != null));
  const lateBedtimeReadinessDelta =
    lateReady != null && earlyReady != null ? round1(lateReady - earlyReady) : null;

  const stepVals = days.map((d) => d.steps).filter((v): v is number => v != null);
  const stepMedian = stepVals.length
    ? [...stepVals].sort((a, b) => a - b)[Math.floor(stepVals.length / 2)]
    : null;
  let highStepsReadinessDelta: number | null = null;
  if (stepMedian != null) {
    const nextReady = (day: string) => {
      const idx = days.findIndex((d) => d.day === day);
      return idx >= 0 ? days[idx + 1]?.readiness ?? null : null;
    };
    const high = days
      .filter((d) => (d.steps ?? 0) >= stepMedian)
      .map((d) => nextReady(d.day))
      .filter((v): v is number => v != null);
    const low = days
      .filter((d) => (d.steps ?? Infinity) < stepMedian)
      .map((d) => nextReady(d.day))
      .filter((v): v is number => v != null);
    const highAvg = avg(high);
    const lowAvg = avg(low);
    if (highAvg != null && lowAvg != null) {
      highStepsReadinessDelta = round1(highAvg - lowAvg);
    }
  }

  const correlations = { lateBedtimeReadinessDelta, highStepsReadinessDelta };
  const insights = buildInsights(
    days,
    sleepDebtHours,
    bedtimeConsistencyMinutes,
    correlations,
    trends,
  );

  return {
    days,
    latest,
    averages,
    trends,
    sleepDebtHours: round1(sleepDebtHours) ?? 0,
    bedtimeConsistencyMinutes:
      bedtimeConsistencyMinutes == null ? null : Math.round(bedtimeConsistencyMinutes),
    weekday,
    insights,
    correlations,
  };
}
