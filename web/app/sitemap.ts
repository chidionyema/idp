import { MetadataRoute } from "next";
import { site } from "@/content/site";
import { posts } from "@/content/posts";
export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://meridian.ai";
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: base, lastModified: new Date(), changeFrequency: "weekly", priority: 1 },
    { url: `${base}/research`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.9 },
    { url: `${base}/case-studies`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.9 },
    { url: `${base}/tooling`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.7 },
    { url: `${base}/consulting`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/writing`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.8 },
    { url: `${base}/contact`, lastModified: new Date(), changeFrequency: "yearly", priority: 0.5 },
    { url: `${base}/demo`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.7 },
    { url: `${base}/tools/cost-calculator`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/tools/trace-explorer`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.6 },
  ];
  const postRoutes: MetadataRoute.Sitemap = posts.map((p) => ({ url: `${base}/writing/${p.slug}`, lastModified: new Date(p.date), changeFrequency: "monthly" as const, priority: 0.8 }));
  return [...staticRoutes, ...postRoutes];
}
