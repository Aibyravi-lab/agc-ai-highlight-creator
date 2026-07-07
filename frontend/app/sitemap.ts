import type { MetadataRoute } from "next";
import { SITE_URL } from "../utils/seo";

const ROUTES = [
  "/",
  "/login",
  "/register",
  "/about",
  "/contact",
  "/privacy",
  "/terms",
  "/refund",
  "/pricing",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return ROUTES.map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified,
  }));
}
