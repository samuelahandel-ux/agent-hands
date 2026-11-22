import { cookies } from "next/headers";
import { refreshAccessToken } from "./oura";

const ACCESS = "oura_access";
const REFRESH = "oura_refresh";
const EXPIRES = "oura_expires";
const VERIFIER = "oura_pkce";
const STATE = "oura_state";

export async function setPkceCookies(state: string, verifier: string) {
  const jar = await cookies();
  jar.set(STATE, state, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 600 });
  jar.set(VERIFIER, verifier, { httpOnly: true, sameSite: "lax", path: "/", maxAge: 600 });
}

export async function consumePkce(state: string): Promise<string | null> {
  const jar = await cookies();
  const expected = jar.get(STATE)?.value;
  const verifier = jar.get(VERIFIER)?.value;
  jar.delete(STATE);
  jar.delete(VERIFIER);
  if (!expected || !verifier || expected !== state) return null;
  return verifier;
}

export async function setAuthCookies(tokens: {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}) {
  const jar = await cookies();
  const maxAge = Math.max(tokens.expires_in, 60 * 60 * 24 * 30);
  jar.set(ACCESS, tokens.access_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: tokens.expires_in,
  });
  jar.set(REFRESH, tokens.refresh_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge,
  });
  jar.set(EXPIRES, String(Date.now() + tokens.expires_in * 1000), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge,
  });
}

export async function clearAuthCookies() {
  const jar = await cookies();
  jar.delete(ACCESS);
  jar.delete(REFRESH);
  jar.delete(EXPIRES);
}

export async function getValidAccessToken(): Promise<string | null> {
  const jar = await cookies();
  const access = jar.get(ACCESS)?.value;
  const refresh = jar.get(REFRESH)?.value;
  const expiresAt = Number(jar.get(EXPIRES)?.value ?? 0);

  if (access && Date.now() < expiresAt - 60_000) {
    return access;
  }

  if (!refresh) return access ?? null;

  try {
    const next = await refreshAccessToken(refresh);
    await setAuthCookies(next);
    return next.access_token;
  } catch {
    return access ?? null;
  }
}

export async function isConnected(): Promise<boolean> {
  const jar = await cookies();
  return Boolean(jar.get(ACCESS)?.value || jar.get(REFRESH)?.value);
}
