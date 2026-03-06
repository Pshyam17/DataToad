# Deploy Spock (Pshyam17/Spock) to Vercel

Spock is an **Express + React (Vite)** app with PostgreSQL (Drizzle), sessions, and Passport. The repo already avoids starting the HTTP server when `VERCEL` is set. To run it on Vercel you need a serverless API handler and correct config.

---

## 1. Clone Spock and add the API handler

```bash
git clone https://github.com/Pshyam17/Spock.git
cd Spock
```

Create **`api/index.ts`** in the repo root with:

```ts
// api/index.ts – Vercel serverless entrypoint
import app from "../index";

export default app;
```

This exposes your Express app as Vercel’s serverless function handler.

---

## 2. Fix static file path for Vercel

On Vercel the server runs from the built function, so `__dirname` is not next to `dist/public`.  
In **`server/static.ts`**, resolve the public directory like this:

**Replace:**

```ts
const distPath = path.resolve(__dirname, "public");
```

**With:**

```ts
const distPath =
  process.env.VERCEL === "1"
    ? path.join(process.cwd(), "dist", "public")
    : path.resolve(__dirname, "public");
```

So in production on Vercel it uses `dist/public` from the project root (created by `npm run build`).

---

## 3. Update `vercel.json`

You want **all** traffic (API + SPA) to go through the Express app so it can serve the React app and API routes. In the repo root, set **`vercel.json`** to:

```json
{
  "version": 2,
  "buildCommand": "npm run build",
  "outputDirectory": "dist/public",
  "rewrites": [
    { "source": "/(.*)", "destination": "/api" }
  ],
  "functions": {
    "api/index.ts": {
      "memory": 1024,
      "maxDuration": 30
    }
  }
}
```

- **buildCommand** – builds both client (→ `dist/public`) and server bundle.
- **outputDirectory** – Vercel serves static assets from `dist/public` when they match.
- **rewrites** – send everything else (HTML, API, SPA fallback) to the Express app at `/api`.
- **functions** – optional; increases memory and timeout for the API.

---

## 4. Deploy from the Vercel dashboard

1. Go to [vercel.com](https://vercel.com) and sign in (e.g. with GitHub).
2. **Add New** → **Project** → Import **Pshyam17/Spock** (or your fork).
3. **Configure:**
   - **Framework preset:** Other
   - **Root directory:** `./` (leave default)
   - **Build command:** `npm run build`
   - **Output directory:** `dist/public`
   - **Install command:** `npm install`
4. **Environment variables** (Settings → Environment Variables):

   | Variable         | Value              | Notes                    |
   |------------------|--------------------|--------------------------|
   | `DATABASE_URL`   | `postgresql://...` | PostgreSQL connection URL (required for DB + sessions) |
   | `SESSION_SECRET` | (random string)    | For express-session      |

   Add any other env vars your app or Drizzle use (same names as in local `.env`).

5. Click **Deploy**.

---

## 5. After deploy

- Your app will be at `https://<project>.vercel.app`.
- API routes stay under `/api/...` if that’s how the app is set up; the rewrite sends all non-asset requests to the same Express app, so your existing routes (e.g. `/api/...`) still work.
- If you use a **custom domain**, add it in the Vercel project **Settings → Domains**.

---

## Limitations

- **WebSockets** – The repo depends on `ws`. Vercel serverless does **not** support long-lived WebSocket servers. Any real-time features using `ws` on the same process will not work; you’d need a separate WebSocket service (e.g. another host or a dedicated WS provider).
- **Cold starts** – First request after idle can be slower; the function config above helps a bit.
- **PostgreSQL** – Use a cloud Postgres that allows connections from the internet (e.g. Neon, Supabase, Railway, Vercel Postgres). Set `DATABASE_URL` (and run migrations if you use them, e.g. via a post-build script or manually).

---

## Optional: Run migrations on deploy

If you use Drizzle migrations, you can run them in the build step. In **`package.json`**, change the build script to:

```json
"build": "tsx script/build.ts && drizzle-kit push"
```

Or add a separate **Build** step in Vercel that runs `npm run db:push` (and ensure `DATABASE_URL` is set for the build environment). Use `drizzle-kit push` only if that matches your workflow; otherwise use your migration command.

---

## Summary checklist

- [ ] Clone Spock (or use your fork).
- [ ] Add `api/index.ts` that exports the Express app from `../index`.
- [ ] In `server/static.ts`, use `process.cwd() + '/dist/public'` when `VERCEL === '1'`.
- [ ] Set `vercel.json` with build, output, rewrites, and optional function config.
- [ ] In Vercel: import repo, set build command and output directory, add `DATABASE_URL` and `SESSION_SECRET`.
- [ ] Deploy and test; add a custom domain if needed.
