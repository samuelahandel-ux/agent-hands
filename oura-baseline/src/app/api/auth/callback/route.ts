import { NextResponse } from "next/server";
import { exchangeCode } from "@/lib/oura";
import { clearAuthCookies, consumePkce, setAuthCookies } from "@/lib/tokens";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const error = url.searchParams.get("error");
  if (error) {
    return NextResponse.redirect(new URL(`/?error=${encodeURIComponent(error)}`, url.origin));
  }

  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (!code || !state) {
    return NextResponse.redirect(new URL("/?error=missing_code", url.origin));
  }

  const verifier = await consumePkce(state);
  if (!verifier) {
    return NextResponse.redirect(new URL("/?error=invalid_state", url.origin));
  }

  const redirectUri =
    process.env.OURA_REDIRECT_URI ?? `${url.origin}/api/auth/callback`;

  try {
    const tokens = await exchangeCode({ code, redirectUri, codeVerifier: verifier });
    await setAuthCookies(tokens);
    return NextResponse.redirect(new URL("/?connected=1", url.origin));
  } catch (err) {
    await clearAuthCookies();
    const message = err instanceof Error ? err.message : "oauth_failed";
    return NextResponse.redirect(
      new URL(`/?error=${encodeURIComponent(message.slice(0, 120))}`, url.origin),
    );
  }
}
