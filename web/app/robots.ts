import { MetadataRoute } from "next";
export default function robots(): MetadataRoute.Robots {
  const base = process.env.MERIAN_SITE_URL ?? process.env.MERIDIAN_SITE_URL ?? "http://localhost:3000";
  return { rules: { userAgent: "*", allow: "/" }, sitemap: `${base}/sitemap.xml` };
}
