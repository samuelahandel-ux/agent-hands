import { randomBytes, createHash } from "node:crypto";
import { NextResponse } from "next/server";
import { OURA_SCOPES, oauthConfigured } from "@/lib/oura";
import { setPkceCookies } from "@/lib/tokens";

function base64Url(buf: Buffer) {
  return buf
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

export async function GET(request: Request) {
  if (!oauthConfigured()) {
    return NextResponse.json(
      {
        error:
          "Set OURA_CLIENT_ID and OURA_CLIENT_SECRET to connect. Create an app at https://cloud.ouraring.com/oauth/applications",
      },
      { status: 400 },
    );
  }

  const url = new URL(request.url);
  const redirectUri =
    process.env.OURA_REDIRECT_URI ?? `${url.origin}/api/auth/callback`;

  const state = base64Url(randomBytes(24));
  const verifier = base64Url(randomBytes(48));
  const challenge = base64Url(createHash("sha256").update(verifier).digest());

  await setPkceCookies(state, verifier);

  const auth = new URL("https://cloud.ouraring.com/oauth/authorize");
  auth.searchParams.set("response_type", "code");
  auth.searchParams.set("client_id", process.env.OURA_CLIENT_ID!);
  auth.searchParams.set("redirect_uri", redirectUri);
  auth.searchParams.set("scope", OURA_SCOPES);
  auth.searchParams.set("state", state);
  auth.searchParams.set("code_challenge", challenge);
  auth.searchParams.set("code_challenge_method", "S256");

  return NextResponse.redirect(auth.toString());
}
