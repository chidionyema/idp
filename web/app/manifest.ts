import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Meridian Intelligence",
    short_name: "Meridian",
    description:
      "AI research laboratory building and validating products for enterprises and individuals.",
    start_url: "/",
    display: "standalone",
    background_color: "#0B1421",
    theme_color: "#0B1421",
    icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
