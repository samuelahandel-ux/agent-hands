"use client";

import { useEffect, useState } from "react";

function isIos() {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

function isStandalone() {
  if (typeof window === "undefined") return false;
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return nav.standalone === true || window.matchMedia("(display-mode: standalone)").matches;
}

export function InstallPrompt() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!isIos() || isStandalone()) return;
    const dismissed = sessionStorage.getItem("baseline-install-dismissed");
    if (dismissed) return;
    setShow(true);
  }, []);

  if (!show) return null;

  return (
    <div className="install-sheet glass glass-strong">
      <div className="relative z-[1]">
        <p className="brand text-xl">Install on iPhone</p>
        <p className="mt-2 text-sm text-[var(--ink-soft)]">
          Open in Safari → tap <span className="font-semibold text-[var(--ink)]">Share</span> →{" "}
          <span className="font-semibold text-[var(--ink)]">Add to Home Screen</span>. Baseline
          opens like an app — full screen, no browser chrome.
        </p>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className="glass-pill glass-cta px-4 py-2 text-sm"
            onClick={() => setShow(false)}
          >
            Got it
          </button>
          <button
            type="button"
            className="glass-pill px-4 py-2 text-sm"
            onClick={() => {
              sessionStorage.setItem("baseline-install-dismissed", "1");
              setShow(false);
            }}
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}
