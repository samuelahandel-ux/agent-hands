export type DailySleep = {
  id: string;
  day: string;
  score: number | null;
  contributors?: {
    deep_sleep?: number | null;
    efficiency?: number | null;
    latency?: number | null;
    rem_sleep?: number | null;
    restfulness?: number | null;
    timing?: number | null;
    total_sleep?: number | null;
  };
};

export type DailyReadiness = {
  id: string;
  day: string;
  score: number | null;
  temperature_deviation?: number | null;
  temperature_trend_deviation?: number | null;
  contributors?: {
    activity_balance?: number | null;
    body_temperature?: number | null;
    hrv_balance?: number | null;
    previous_day_activity?: number | null;
    previous_night?: number | null;
    recovery_index?: number | null;
    resting_heart_rate?: number | null;
    sleep_balance?: number | null;
    sleep_regularity?: number | null;
  };
};

export type DailyActivity = {
  id: string;
  day: string;
  score: number | null;
  active_calories?: number | null;
  steps?: number | null;
  equivalent_walking_distance?: number | null;
  high_activity_time?: number | null;
  medium_activity_time?: number | null;
  low_activity_time?: number | null;
  sedentary_time?: number | null;
  resting_time?: number | null;
  non_wear_time?: number | null;
  total_calories?: number | null;
  target_calories?: number | null;
  meters_to_target?: number | null;
  target_meters?: number | null;
  inactivity_alerts?: number | null;
};

export type SleepSession = {
  id: string;
  day: string;
  average_breath?: number | null;
  average_heart_rate?: number | null;
  average_hrv?: number | null;
  awake_time?: number | null;
  bedtime_end?: string | null;
  bedtime_start?: string | null;
  deep_sleep_duration?: number | null;
  efficiency?: number | null;
  latency?: number | null;
  light_sleep_duration?: number | null;
  lowest_heart_rate?: number | null;
  rem_sleep_duration?: number | null;
  restless_periods?: number | null;
  time_in_bed?: number | null;
  total_sleep_duration?: number | null;
  type?: string | null;
};

export type DailyStress = {
  id: string;
  day: string;
  stress_high?: number | null;
  recovery_high?: number | null;
  day_summary?: string | null;
};

export type DailySpo2 = {
  id: string;
  day: string;
  spo2_percentage?: { average?: number | null } | null;
  breathing_disturbance_index?: number | null;
};

export type DailyResilience = {
  id: string;
  day: string;
  level?: string | null;
  contributors?: {
    sleep_recovery?: number | null;
    daytime_recovery?: number | null;
    stress?: number | null;
  };
};

export type Workout = {
  id: string;
  activity?: string | null;
  calories?: number | null;
  day: string;
  distance?: number | null;
  end_datetime?: string | null;
  intensity?: string | null;
  label?: string | null;
  start_datetime?: string | null;
  source?: string | null;
};

export type HeartRateSample = {
  bpm: number;
  source: string;
  timestamp: string;
};

export type PersonalInfo = {
  id?: string;
  age?: number | null;
  weight?: number | null;
  height?: number | null;
  biological_sex?: string | null;
  email?: string | null;
};

export type Vo2Max = {
  id: string;
  day: string;
  vo2_max?: number | null;
};

export type OuraBundle = {
  personalInfo: PersonalInfo | null;
  dailySleep: DailySleep[];
  dailyReadiness: DailyReadiness[];
  dailyActivity: DailyActivity[];
  sleep: SleepSession[];
  stress: DailyStress[];
  spo2: DailySpo2[];
  resilience: DailyResilience[];
  workouts: Workout[];
  vo2Max: Vo2Max[];
  heartRate: HeartRateSample[];
  range: { start: string; end: string };
  source: "live" | "demo";
};

export type DayPoint = {
  day: string;
  label: string;
  readiness: number | null;
  sleepScore: number | null;
  activityScore: number | null;
  hrv: number | null;
  rhr: number | null;
  sleepHours: number | null;
  deepHours: number | null;
  remHours: number | null;
  lightHours: number | null;
  efficiency: number | null;
  bedtimeHour: number | null;
  steps: number | null;
  activeCalories: number | null;
  tempDeviation: number | null;
  stressHigh: number | null;
  recoveryHigh: number | null;
  spo2: number | null;
  resilience: string | null;
};

export type Insight = {
  id: string;
  title: string;
  body: string;
  tone: "positive" | "neutral" | "watch";
};

export type Analytics = {
  days: DayPoint[];
  latest: DayPoint | null;
  averages: {
    readiness: number | null;
    sleepScore: number | null;
    hrv: number | null;
    rhr: number | null;
    sleepHours: number | null;
    steps: number | null;
  };
  trends: {
    readiness: Trend;
    sleepScore: Trend;
    hrv: Trend;
    rhr: Trend;
  };
  sleepDebtHours: number;
  bedtimeConsistencyMinutes: number | null;
  weekday: { day: string; readiness: number | null; sleepHours: number | null }[];
  insights: Insight[];
  correlations: {
    lateBedtimeReadinessDelta: number | null;
    highStepsReadinessDelta: number | null;
  };
};

export type Trend = {
  direction: "up" | "down" | "flat";
  delta: number | null;
  label: string;
};
