import type {
  DailyActivity,
  DailyReadiness,
  DailyResilience,
  DailySleep,
  DailySpo2,
  DailyStress,
  HeartRateSample,
  OuraBundle,
  PersonalInfo,
  SleepSession,
  Vo2Max,
  Workout,
} from "./types";

const API = "https://api.ouraring.com";
const USER_AGENT = "BaselineOuraTrends/1.0";

export const OURA_SCOPES = [
  "email",
  "personal",
  "daily",
  "heartrate",
  "workout",
  "tag",
  "session",
  "spo2",
].join(" ");

type CollectionResponse<T> = { data: T[]; next_token?: string | null };

async function ouraFetch<T>(
  path: string,
  accessToken: string,
  query: Record<string, string> = {},
): Promise<T> {
  const url = new URL(`${API}${path}`);
  for (const [key, value] of Object.entries(query)) {
    if (value) url.searchParams.set(key, value);
  }

  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "User-Agent": USER_AGENT,
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Oura ${path} failed (${res.status}): ${text.slice(0, 200)}`);
  }

  return res.json() as Promise<T>;
}

async function collectAll<T>(
  path: string,
  accessToken: string,
  query: Record<string, string>,
): Promise<T[]> {
  const items: T[] = [];
  let nextToken: string | undefined;

  do {
    const page = await ouraFetch<CollectionResponse<T>>(path, accessToken, {
      ...query,
      ...(nextToken ? { next_token: nextToken } : {}),
    });
    items.push(...(page.data ?? []));
    nextToken = page.next_token ?? undefined;
  } while (nextToken);

  return items;
}

function dateOnly(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function defaultRange(days = 30): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setUTCDate(end.getUTCDate() - (days - 1));
  return { start: dateOnly(start), end: dateOnly(end) };
}

export async function refreshAccessToken(refreshToken: string): Promise<{
  access_token: string;
  refresh_token: string;
  expires_in: number;
}> {
  const clientId = process.env.OURA_CLIENT_ID;
  const clientSecret = process.env.OURA_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    throw new Error("OURA_CLIENT_ID and OURA_CLIENT_SECRET are required");
  }

  const body = new URLSearchParams({
    grant_type: "refresh_token",
    refresh_token: refreshToken,
    client_id: clientId,
    client_secret: clientSecret,
  });

  const res = await fetch(`${API}/oauth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": USER_AGENT,
    },
    body,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Token refresh failed (${res.status}): ${text.slice(0, 200)}`);
  }

  return res.json();
}

export async function exchangeCode(params: {
  code: string;
  redirectUri: string;
  codeVerifier: string;
}): Promise<{
  access_token: string;
  refresh_token: string;
  expires_in: number;
}> {
  const clientId = process.env.OURA_CLIENT_ID;
  const clientSecret = process.env.OURA_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    throw new Error("OURA_CLIENT_ID and OURA_CLIENT_SECRET are required");
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code: params.code,
    redirect_uri: params.redirectUri,
    client_id: clientId,
    client_secret: clientSecret,
    code_verifier: params.codeVerifier,
  });

  const res = await fetch(`${API}/oauth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": USER_AGENT,
    },
    body,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Code exchange failed (${res.status}): ${text.slice(0, 200)}`);
  }

  return res.json();
}

export async function fetchOuraBundle(
  accessToken: string,
  range: { start: string; end: string },
): Promise<OuraBundle> {
  const dateQuery = { start_date: range.start, end_date: range.end };
  const hrStart = new Date(`${range.end}T00:00:00.000Z`);
  hrStart.setUTCDate(hrStart.getUTCDate() - 2);

  const [
    personalInfo,
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
  ] = await Promise.all([
    ouraFetch<PersonalInfo>("/v2/usercollection/personal_info", accessToken).catch(
      () => null,
    ),
    collectAll<DailySleep>("/v2/usercollection/daily_sleep", accessToken, dateQuery),
    collectAll<DailyReadiness>(
      "/v2/usercollection/daily_readiness",
      accessToken,
      dateQuery,
    ),
    collectAll<DailyActivity>(
      "/v2/usercollection/daily_activity",
      accessToken,
      dateQuery,
    ),
    collectAll<SleepSession>("/v2/usercollection/sleep", accessToken, dateQuery),
    collectAll<DailyStress>("/v2/usercollection/daily_stress", accessToken, dateQuery).catch(
      () => [] as DailyStress[],
    ),
    collectAll<DailySpo2>("/v2/usercollection/daily_spo2", accessToken, dateQuery).catch(
      () => [] as DailySpo2[],
    ),
    collectAll<DailyResilience>(
      "/v2/usercollection/daily_resilience",
      accessToken,
      dateQuery,
    ).catch(() => [] as DailyResilience[]),
    collectAll<Workout>("/v2/usercollection/workout", accessToken, dateQuery).catch(
      () => [] as Workout[],
    ),
    collectAll<Vo2Max>("/v2/usercollection/vO2_max", accessToken, dateQuery).catch(
      () => [] as Vo2Max[],
    ),
    collectAll<HeartRateSample>("/v2/usercollection/heartrate", accessToken, {
      start_datetime: hrStart.toISOString(),
      end_datetime: new Date(`${range.end}T23:59:59.000Z`).toISOString(),
    }).catch(() => [] as HeartRateSample[]),
  ]);

  return {
    personalInfo,
    dailySleep,
    dailyReadiness,
    dailyActivity,
    sleep: sleep.filter((s) => s.type !== "deleted"),
    stress,
    spo2,
    resilience,
    workouts,
    vo2Max,
    heartRate,
    range,
    source: "live",
  };
}

export function oauthConfigured(): boolean {
  return Boolean(process.env.OURA_CLIENT_ID && process.env.OURA_CLIENT_SECRET);
}
