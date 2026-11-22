import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/tokens";

export async function POST() {
  await clearAuthCookies();
  return NextResponse.json({ ok: true });
}

export async function GET(request: Request) {
  await clearAuthCookies();
  return NextResponse.redirect(new URL("/", new URL(request.url).origin));
}
