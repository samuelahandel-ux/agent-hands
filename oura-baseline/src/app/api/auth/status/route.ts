import { NextResponse } from "next/server";
import { oauthConfigured } from "@/lib/oura";
import { isConnected } from "@/lib/tokens";

export async function GET() {
  return NextResponse.json({
    connected: await isConnected(),
    oauthConfigured: oauthConfigured(),
  });
}
