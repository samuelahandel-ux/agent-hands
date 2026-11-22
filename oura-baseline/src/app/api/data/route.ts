import { NextResponse } from "next/server";
import { analyze } from "@/lib/analytics";
import { buildDemoBundle } from "@/lib/demo-data";
import { defaultRange, fetchOuraBundle } from "@/lib/oura";
import { getValidAccessToken } from "@/lib/tokens";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const days = Math.min(90, Math.max(7, Number(url.searchParams.get("days") ?? 30) || 30));
  const forceDemo = url.searchParams.get("demo") === "1";
  const range = defaultRange(days);

  if (forceDemo) {
    const bundle = buildDemoBundle(days);
    return NextResponse.json({
      bundle: {
        source: bundle.source,
        range: bundle.range,
        personalInfo: bundle.personalInfo,
        workouts: bundle.workouts,
        vo2Max: bundle.vo2Max,
        heartRate: bundle.heartRate.slice(-48),
      },
      analytics: analyze(bundle),
    });
  }

  const token = await getValidAccessToken();
  if (!token) {
    const bundle = buildDemoBundle(days);
    return NextResponse.json({
      bundle: {
        source: bundle.source,
        range: bundle.range,
        personalInfo: bundle.personalInfo,
        workouts: bundle.workouts,
        vo2Max: bundle.vo2Max,
        heartRate: bundle.heartRate.slice(-48),
      },
      analytics: analyze(bundle),
      demoFallback: true,
    });
  }

  try {
    const bundle = await fetchOuraBundle(token, range);
    return NextResponse.json({
      bundle: {
        source: bundle.source,
        range: bundle.range,
        personalInfo: bundle.personalInfo,
        workouts: bundle.workouts,
        vo2Max: bundle.vo2Max,
        heartRate: bundle.heartRate.slice(-48),
      },
      analytics: analyze(bundle),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "fetch_failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
