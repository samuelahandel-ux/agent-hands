# Baseline

Minimal Oura trends app. Pulls sleep, readiness, activity, HRV, stress, SpO₂, workouts, and related daily data from the Oura Cloud API, then surfaces patterns the stock app undersells: sleep debt, HRV direction, bedtime consistency, late-night readiness tax, and weekday dips.

## Why OAuth (not Bluetooth)

Your ring syncs to Oura’s cloud via the desktop or phone app. Baseline reads that cloud data with OAuth. Direct Bluetooth access is not supported by Oura for third-party apps.

Personal access tokens were deprecated; use an OAuth application.

## Setup

1. Create an application at [Oura developer applications](https://cloud.ouraring.com/oauth/applications).
2. Add redirect URI: `http://127.0.0.1:3000/api/auth/callback`
3. Copy `.env.example` to `.env.local` and fill in `OURA_CLIENT_ID` / `OURA_CLIENT_SECRET`.
4. Run:

```bash
npm install
npm run dev
```

5. Open `http://127.0.0.1:3000` and click **Connect Oura**.

Until credentials are set, the UI loads realistic demo trends so you can evaluate the layout.

## Scripts

- `npm run dev` — local development
- `npm run build` — production build
- `npm start` — serve the production build
