import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Baseline",
    short_name: "Baseline",
    description: "Oura ring trends beyond the stock app — sleep debt, HRV, readiness.",
    start_url: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#c8ddd6",
    theme_color: "#1a7a6a",
    categories: ["health", "lifestyle"],
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
