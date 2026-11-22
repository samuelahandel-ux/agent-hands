# Baseline for iPhone

Two ways to run Baseline as an iPhone app:

## 1. Home Screen app (recommended, no install store)

1. Open the Baseline URL in **Safari** on your iPhone.
2. Tap **Share** → **Add to Home Screen**.
3. Tap **Add**. Baseline opens full-screen like a native app.

## 2. Expo Go (native shell)

1. Install **Expo Go** from the App Store.
2. From this folder run: `npx expo start --tunnel`
3. Scan the QR code with the Camera app / Expo Go.

The Expo app wraps Baseline in a native WebView (`EXPO_PUBLIC_BASELINE_URL` overrides the default host).

### App Store builds

A real App Store binary needs a Mac, Xcode, and an Apple Developer account (`eas build -p ios`). This project is ready for that path later.
