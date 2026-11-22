import type { OuraBundle, SleepSession } from "./types";
import { defaultRange } from "./oura";

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function mulberry32(seed: number) {
  return () => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function buildDemoBundle(days = 30): OuraBundle {
  const range = defaultRange(days);
  const rand = mulberry32(42);
  const start = new Date(`${range.start}T12:00:00.000Z`);

  const dailySleep = [];
  const dailyReadiness = [];
  const dailyActivity = [];
  const sleep: SleepSession[] = [];
  const stress = [];
  const spo2 = [];
  const resilience = [];
  const workouts = [];
  const vo2Max = [];
  const heartRate = [];

  for (let i = 0; i < days; i++) {
    const dayDate = new Date(start);
    dayDate.setUTCDate(start.getUTCDate() + i);
    const day = dayDate.toISOString().slice(0, 10);
    const weekday = dayDate.getUTCDay();
    const weekend = weekday === 0 || weekday === 6;
    const wave = Math.sin(i / 4.2) * 8;
    const noise = (rand() - 0.5) * 10;
    const lateNight = weekend && rand() > 0.45;

    const sleepScore = Math.round(clamp(78 + wave + noise - (lateNight ? 8 : 0), 55, 96));
    const readiness = Math.round(
      clamp(76 + wave * 0.8 + noise * 0.7 - (lateNight ? 10 : 0), 52, 95),
    );
    const activity = Math.round(clamp(70 + (weekend ? -6 : 5) + (rand() - 0.5) * 14, 45, 98));
    const hrv = Math.round(clamp(42 + wave * 0.6 + (rand() - 0.5) * 12 - (lateNight ? 6 : 0), 22, 78));
    const rhr = Math.round(clamp(54 - wave * 0.2 + (rand() - 0.5) * 4 + (lateNight ? 3 : 0), 46, 68));
    const totalSleep = Math.round(
      (6.4 + (weekend ? 0.7 : 0) + wave / 20 + (rand() - 0.5) * 0.8 - (lateNight ? 0.6 : 0)) *
        3600,
    );
    const deep = Math.round(totalSleep * (0.16 + rand() * 0.06));
    const rem = Math.round(totalSleep * (0.2 + rand() * 0.05));
    const light = Math.max(0, totalSleep - deep - rem);
    const bedtimeHour = lateNight ? 24.5 + rand() * 1.2 : 22.4 + rand() * 1.1;
    const bedtime = new Date(dayDate);
    bedtime.setUTCDate(bedtime.getUTCDate() - 1);
    bedtime.setUTCHours(Math.floor(bedtimeHour), Math.round((bedtimeHour % 1) * 60), 0, 0);
    const wake = new Date(bedtime.getTime() + (totalSleep + 25 * 60) * 1000);

    dailySleep.push({
      id: `sleep-${day}`,
      day,
      score: sleepScore,
      contributors: {
        deep_sleep: Math.round(70 + rand() * 20),
        efficiency: Math.round(80 + rand() * 15),
        rem_sleep: Math.round(70 + rand() * 20),
        total_sleep: Math.round(70 + rand() * 20),
      },
    });

    dailyReadiness.push({
      id: `ready-${day}`,
      day,
      score: readiness,
      temperature_deviation: Number(((rand() - 0.5) * 0.4).toFixed(2)),
      contributors: {
        hrv_balance: Math.round(70 + rand() * 20),
        resting_heart_rate: Math.round(70 + rand() * 20),
        sleep_balance: Math.round(65 + rand() * 25),
        previous_night: sleepScore,
      },
    });

    const steps = Math.round(6200 + (weekend ? -900 : 1800) + rand() * 4500);
    dailyActivity.push({
      id: `act-${day}`,
      day,
      score: activity,
      steps,
      active_calories: Math.round(320 + steps * 0.03 + rand() * 120),
      sedentary_time: Math.round(5.5 * 3600 + rand() * 2 * 3600),
    });

    sleep.push({
      id: `sess-${day}`,
      day,
      average_hrv: hrv,
      average_heart_rate: rhr + 4,
      lowest_heart_rate: rhr,
      total_sleep_duration: totalSleep,
      deep_sleep_duration: deep,
      rem_sleep_duration: rem,
      light_sleep_duration: light,
      efficiency: Math.round(86 + rand() * 10),
      bedtime_start: bedtime.toISOString(),
      bedtime_end: wake.toISOString(),
      time_in_bed: totalSleep + 25 * 60,
      type: "long_sleep",
    });

    stress.push({
      id: `stress-${day}`,
      day,
      stress_high: Math.round((weekend ? 40 : 90) + rand() * 80),
      recovery_high: Math.round(70 + rand() * 90),
      day_summary: readiness > 80 ? "restored" : readiness < 65 ? "stressful" : "normal",
    });

    spo2.push({
      id: `spo2-${day}`,
      day,
      spo2_percentage: { average: Number((96.5 + rand() * 1.8).toFixed(1)) },
    });

    resilience.push({
      id: `res-${day}`,
      day,
      level: readiness > 82 ? "strong" : readiness < 65 ? "limited" : "solid",
    });

    if (rand() > 0.72) {
      workouts.push({
        id: `wo-${day}`,
        day,
        activity: rand() > 0.5 ? "running" : "cycling",
        calories: Math.round(220 + rand() * 280),
        intensity: rand() > 0.5 ? "moderate" : "high",
        distance: Math.round(3000 + rand() * 7000),
      });
    }

    if (i % 7 === 0) {
      vo2Max.push({ id: `vo2-${day}`, day, vo2_max: Number((44 + rand() * 6).toFixed(1)) });
    }
  }

  for (let m = 0; m < 36; m++) {
    const ts = new Date();
    ts.setMinutes(ts.getMinutes() - m * 5);
    heartRate.push({
      bpm: Math.round(58 + Math.sin(m / 3) * 8 + rand() * 6),
      source: m > 24 ? "sleep" : "awake",
      timestamp: ts.toISOString(),
    });
  }

  return {
    personalInfo: { age: 34, biological_sex: "male", weight: 76, height: 178 },
    dailySleep,
    dailyReadiness,
    dailyActivity,
    sleep,
    stress,
    spo2,
    resilience,
    workouts,
    vo2Max,
    heartRate,
    range,
    source: "demo",
  };
}
