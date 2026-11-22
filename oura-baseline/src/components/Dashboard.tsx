"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { HrvChart } from "@/components/HrvChart";
import { SleepChart } from "@/components/SleepChart";
import { TrendChart } from "@/components/TrendChart";
import type { Analytics, Insight } from "@/lib/types";

type Status = { connected: boolean; oauthConfigured: boolean };

type Payload = {
  analytics: Analytics;
  bundle: {
    source: "live" | "demo";
    range: { start: string; end: string };
    personalInfo: { age?: number | null; biological_sex?: string | null } | null;
    workouts: { day: string; activity?: string | null; calories?: number | null }[];
    vo2Max: { day: string; vo2_max?: number | null }[];
  };
  demoFallback?: boolean;
  error?: string;
};

const RANGES = [7, 14, 30, 90] as const;

function toneClass(tone: Insight["tone"]) {
  if (tone === "positive") return "text-[var(--good)]";
  if (tone === "watch") return "text-[var(--watch)]";
  return "text-[var(--muted)]";
}

function formatNum(n: number | null | undefined, digits = 0) {
  if (n == null || Number.isNaN(n)) return "—";
  return digits ? n.toFixed(digits) : String(Math.round(n));
}

export function Dashboard() {
  const [status, setStatus] = useState<Status | null>(null);
  const [days, setDays] = useState<(typeof RANGES)[number]>(30);
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthError = params.get("error");
    if (oauthError) setError(oauthError);
  }, []);

  useEffect(() => {
    fetch("/api/auth/status")
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus({ connected: false, oauthConfigured: false }));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    startTransition(() => {
      fetch(`/api/data?days=${days}`, { signal: controller.signal })
        .then(async (r) => {
          const json = (await r.json()) as Payload;
          if (!r.ok) throw new Error(json.error ?? "Failed to load data");
          setData(json);
        })
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setError(err instanceof Error ? err.message : "Failed to load");
        });
    });
    return () => controller.abort();
  }, [days]);

  const analytics = data?.analytics;
  const isDemo = data?.bundle.source === "demo";

  const workoutCount = useMemo(
    () => data?.bundle.workouts.length ?? 0,
    [data?.bundle.workouts],
  );

  return (
    <main className="liquid-scene pb-24">
      <div className="liquid-scene__glow" aria-hidden>
        <div className="liquid-scene__orb liquid-scene__orb--a" />
        <div className="liquid-scene__orb liquid-scene__orb--b" />
        <div className="liquid-scene__orb liquid-scene__orb--c" />
        <div className="liquid-caustic" />
      </div>

      <div className="shell pt-10 md:pt-14">
        <header className="rise grid gap-8 md:grid-cols-[1.35fr_1fr] md:items-end">
          <div>
            <p className="brand brand-sheen text-5xl leading-none md:text-7xl">Baseline</p>
            <p className="mt-4 max-w-xl text-lg text-[var(--ink-soft)] md:text-xl">
              Trends your Oura ring already measured — sleep debt, HRV direction, and
              readiness patterns the stock app keeps buried.
            </p>
          </div>
          <div className="flex flex-col items-start gap-3 md:items-end">
            <div className="glass-pill gap-1 p-1">
              {RANGES.map((range) => (
                <button
                  key={range}
                  type="button"
                  onClick={() => setDays(range)}
                  className={`glass-pill px-3.5 py-1.5 text-sm ${
                    days === range ? "is-active" : "border-0 bg-transparent shadow-none"
                  }`}
                >
                  {range}d
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {status?.connected ? (
                <a href="/api/auth/logout" className="glass-pill px-4 py-2 text-sm">
                  Disconnect
                </a>
              ) : status?.oauthConfigured ? (
                <a href="/api/auth/login" className="glass-pill glass-cta px-4 py-2 text-sm">
                  Connect Oura
                </a>
              ) : (
                <span className="glass-pill px-4 py-2 text-sm text-[var(--muted)]">
                  Add Oura API credentials
                </span>
              )}
              <span className="glass-pill px-3 py-1.5 text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
                {pending ? "Updating…" : isDemo ? "Demo data" : "Live ring data"}
              </span>
            </div>
          </div>
        </header>

        {error ? (
          <p className="glass glass-pad rise mt-6 text-sm text-[var(--watch)]">{error}</p>
        ) : null}

        {!status?.connected && !status?.oauthConfigured ? (
          <section className="glass glass-strong glass-pad rise rise-delay-1 mt-8">
            <h2 className="brand relative z-[1] text-2xl">Connect your ring</h2>
            <ol className="relative z-[1] mt-4 space-y-2 text-[var(--ink-soft)]">
              <li>
                1. Create an application at{" "}
                <a
                  className="underline decoration-[var(--accent)] underline-offset-4"
                  href="https://cloud.ouraring.com/oauth/applications"
                  target="_blank"
                  rel="noreferrer"
                >
                  cloud.ouraring.com/oauth/applications
                </a>
              </li>
              <li>
                2. Set redirect URI to{" "}
                <code className="text-[var(--ink)]">http://127.0.0.1:3000/api/auth/callback</code>{" "}
                (or your deployed origin + <code>/api/auth/callback</code>).
              </li>
              <li>
                3. Add secrets <code className="text-[var(--ink)]">OURA_CLIENT_ID</code> and{" "}
                <code className="text-[var(--ink)]">OURA_CLIENT_SECRET</code>, restart, then tap
                Connect Oura.
              </li>
            </ol>
            <p className="relative z-[1] mt-4 text-sm text-[var(--muted)]">
              The ring syncs through the Oura cloud (desktop/phone). Baseline reads that cloud
              data — Bluetooth pairing alone is not enough for the API. Demo trends are shown
              below until you connect.
            </p>
          </section>
        ) : null}

        {analytics ? (
          <>
            <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                {
                  label: "Readiness",
                  value: formatNum(analytics.latest?.readiness),
                  sub: analytics.trends.readiness.label,
                  delay: "rise-delay-1",
                },
                {
                  label: "Sleep score",
                  value: formatNum(analytics.latest?.sleepScore),
                  sub: analytics.trends.sleepScore.label,
                  delay: "rise-delay-2",
                },
                {
                  label: "Overnight HRV",
                  value: formatNum(analytics.latest?.hrv),
                  sub: analytics.trends.hrv.label,
                  delay: "rise-delay-3",
                },
                {
                  label: "Sleep debt",
                  value: `${analytics.sleepDebtHours > 0 ? "+" : ""}${formatNum(analytics.sleepDebtHours, 1)}h`,
                  sub: "vs 7.5h nightly target",
                  delay: "rise-delay-4",
                },
              ].map((m) => (
                <div key={m.label} className={`glass glass-pad rise ${m.delay}`}>
                  <p className="relative z-[1] text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                    {m.label}
                  </p>
                  <p className="metric-value relative z-[1] mt-3 text-5xl md:text-6xl">{m.value}</p>
                  <p className="relative z-[1] mt-2 text-sm text-[var(--muted)]">{m.sub}</p>
                </div>
              ))}
            </section>

            <section className="rise rise-delay-2 mt-10">
              <h2 className="brand text-3xl">What the Oura app undersells</h2>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                {analytics.insights.map((insight) => (
                  <article key={insight.id} className="glass glass-pad">
                    <p
                      className={`relative z-[1] text-[11px] uppercase tracking-[0.14em] ${toneClass(insight.tone)}`}
                    >
                      {insight.tone}
                    </p>
                    <h3 className="relative z-[1] mt-2 text-xl font-medium">{insight.title}</h3>
                    <p className="relative z-[1] mt-2 text-[var(--ink-soft)]">{insight.body}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="glass glass-pad rise rise-delay-3 mt-10">
              <div className="relative z-[1] mb-4">
                <h2 className="brand text-3xl">Score overlay</h2>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Readiness, sleep, and activity on one timeline · {data?.bundle.range.start} →{" "}
                  {data?.bundle.range.end}
                </p>
              </div>
              <div className="relative z-[1]">
                <TrendChart days={analytics.days} />
              </div>
            </section>

            <section className="mt-6 grid gap-4 lg:grid-cols-2">
              <div className="glass glass-pad">
                <h2 className="brand relative z-[1] text-3xl">Sleep architecture</h2>
                <p className="relative z-[1] mt-1 text-sm text-[var(--muted)]">
                  Deep / REM / light hours · avg {formatNum(analytics.averages.sleepHours, 1)}h
                </p>
                <div className="relative z-[1] mt-4">
                  <SleepChart days={analytics.days} />
                </div>
              </div>
              <div className="glass glass-pad">
                <h2 className="brand relative z-[1] text-3xl">HRV vs resting HR</h2>
                <p className="relative z-[1] mt-1 text-sm text-[var(--muted)]">
                  Avg HRV {formatNum(analytics.averages.hrv)} ms · RHR{" "}
                  {formatNum(analytics.averages.rhr)} bpm
                </p>
                <div className="relative z-[1] mt-4">
                  <HrvChart days={analytics.days} />
                </div>
              </div>
            </section>

            <section className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="glass glass-pad">
                <p className="relative z-[1] text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                  Bedtime consistency
                </p>
                <p className="metric-value relative z-[1] mt-3 text-4xl">
                  {analytics.bedtimeConsistencyMinutes == null
                    ? "—"
                    : `±${analytics.bedtimeConsistencyMinutes}m`}
                </p>
                <p className="relative z-[1] mt-2 text-sm text-[var(--muted)]">
                  Standard deviation of bedtime across the window
                </p>
              </div>
              <div className="glass glass-pad">
                <p className="relative z-[1] text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                  Late night tax
                </p>
                <p className="metric-value relative z-[1] mt-3 text-4xl">
                  {formatNum(analytics.correlations.lateBedtimeReadinessDelta, 1)}
                </p>
                <p className="relative z-[1] mt-2 text-sm text-[var(--muted)]">
                  Readiness delta after midnight bedtimes vs earlier nights
                </p>
              </div>
              <div className="glass glass-pad">
                <p className="relative z-[1] text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                  Movement carryover
                </p>
                <p className="metric-value relative z-[1] mt-3 text-4xl">
                  {formatNum(analytics.correlations.highStepsReadinessDelta, 1)}
                </p>
                <p className="relative z-[1] mt-2 text-sm text-[var(--muted)]">
                  Next-day readiness after higher-step days
                </p>
              </div>
            </section>

            <section className="glass glass-pad mt-6">
              <h2 className="brand relative z-[1] text-3xl">Weekday pattern</h2>
              <p className="relative z-[1] mt-1 text-sm text-[var(--muted)]">
                Average readiness by day of week — find the weekly dip the daily cards miss
              </p>
              <div className="relative z-[1] mt-5 grid grid-cols-7 gap-2">
                {analytics.weekday.map((d) => (
                  <div key={d.day} className="glass-pill flex-col px-1 py-3 text-center">
                    <p className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                      {d.day}
                    </p>
                    <p className="metric-value mt-2 text-xl md:text-3xl">
                      {formatNum(d.readiness)}
                    </p>
                    <p className="mt-1 text-[10px] text-[var(--muted)]">
                      {formatNum(d.sleepHours, 1)}h
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="glass glass-pad">
                <p className="relative z-[1] text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                  Avg steps
                </p>
                <p className="metric-value relative z-[1] mt-3 text-4xl">
                  {formatNum(analytics.averages.steps)}
                </p>
              </div>
              <div className="glass glass-pad">
                <p className="relative z-[1] text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                  Workouts logged
                </p>
                <p className="metric-value relative z-[1] mt-3 text-4xl">{workoutCount}</p>
              </div>
              <div className="glass glass-pad">
                <p className="relative z-[1] text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">
                  Latest VO₂ max
                </p>
                <p className="metric-value relative z-[1] mt-3 text-4xl">
                  {formatNum(
                    data?.bundle.vo2Max[data.bundle.vo2Max.length - 1]?.vo2_max ?? null,
                    1,
                  )}
                </p>
              </div>
            </section>
          </>
        ) : (
          <p className="glass glass-pad mt-16 text-[var(--muted)]">Loading ring trends…</p>
        )}

        <footer className="mt-12 text-sm text-[var(--muted)]">
          Baseline uses the official Oura Cloud API. Keep the ring synced in the Oura desktop or
          mobile app so new nights appear here.
        </footer>
      </div>
    </main>
  );
}
