# Branding Assets

Vedzovi's favicon, Apple touch icon, and Open Graph image are not yet final.
The frontend code is already wired to pick them up automatically — no code
changes are required once the real files are dropped into place.

## Required assets

| Asset | Location | Recommended dimensions |
|---|---|---|
| Favicon | `frontend/public/favicon.ico` | 32x32 and 16x16 (multi-size `.ico`) |
| Apple touch icon | `frontend/public/apple-touch-icon.png` | 180x180 |
| Open Graph image | `frontend/public/og-image.png` | 1200x630 |

## How detection works

[frontend/utils/brandAssets.ts](../frontend/utils/brandAssets.ts) checks at
build/render time whether each file exists in `frontend/public/`. Metadata in
[frontend/app/layout.tsx](../frontend/app/layout.tsx),
[frontend/utils/seo.ts](../frontend/utils/seo.ts), and
[frontend/app/manifest.ts](../frontend/app/manifest.ts) only reference an
asset once its `has*` flag is `true`, so nothing ever points at a missing file.

- **Favicon** — until `public/favicon.ico` exists, the app keeps using
  Next.js's default favicon at `frontend/app/favicon.ico` (its built-in
  file-convention route). Once you add `public/favicon.ico`, it is referenced
  explicitly in metadata and takes priority. At that point you can also
  delete `frontend/app/favicon.ico` to avoid keeping two favicons around.
- **Apple touch icon** — added to `<head>` metadata and to the web manifest's
  `icons` array only once `public/apple-touch-icon.png` exists.
- **Open Graph image** — added to Open Graph and Twitter Card metadata only
  once `public/og-image.png` exists. Until then, the Twitter card type stays
  `summary` (no image); it switches to `summary_large_image` automatically
  the moment the image is present.

## Placing the assets

1. Drop the final files at the paths in the table above.
2. Run the frontend build (`npm run build`) or dev server — no source changes
   needed.
3. Optionally delete `frontend/app/favicon.ico` once `public/favicon.ico` is
   in place (see note above).
