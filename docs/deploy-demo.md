# Free demo deployment (Render + Netlify)

This puts the dashboard on the internet for **free**, so you can send a link to people you're pitching to. It takes
about 30 to 40 minutes the first time and needs three free accounts: GitHub, Render and Netlify.

> **This is a demo setup, not a place for real student data.** The free API host loses its files whenever it restarts
> or sleeps, so the database is rebuilt with made-up students each time. For a permanent installation with real
> data, use the single-server setup in the main [README](../README.md#option-a-one-server-with-docker-recommended).

## How the pieces fit

```
Visitor's browser ──> Netlify (the website)  ──calls──>  Render (the API + demo data)
```

Netlify serves the screens, Render runs the backend. The two have different addresses, so each needs to know the
other's: the website needs the API address, and the API needs the website address (for browser security, called CORS).
That is why the steps below go API first, then website, then back to the API.

## What to expect from the free plans

| | |
|--|--|
| **Sleeping** | Render's free API sleeps after 15 minutes without visitors; the next visit takes up to about a minute to wake it, during which the site shows "Cannot reach the server" or a loading page |
| **Data resets** | Whenever the API restarts, redeploys or wakes from sleep, it starts with fresh demo data. Anything added or changed during a demo disappears later |
| **Accounts survive** | The admin and viewer logins come from settings, so they exist after every reset |
| **Monthly hours** | Render gives 750 free instance hours a month, enough for one service to stay awake all month |
| **Cost** | Free. Limits and prices change; check render.com/pricing and netlify.com/pricing before relying on them. Render's paid Starter plan (about $7 a month at the time of writing) stops the sleeping |

## Step 0: keep work and demo separate

You'll keep building after the pitch. Both hosts redeploy automatically whenever the `main` branch changes, so do your
day-to-day work on another branch and merge into `main` only when you want the demo updated:

```bash
cd ~/Documents/projects/student-analytics
git checkout -b dev            # work here from now on
```

## Step 1: put the code on GitHub

1. Create a free account at github.com, then **New repository**. Name it `student-analytics`, choose **Private**, and do
   **not** add a README or .gitignore (the project has them). Copy the repository address it shows.
2. In the project folder:

```bash
cd ~/Documents/projects/student-analytics
git status                     # check that no .env file or .db file is listed (they are ignored on purpose)
git add -A
git commit -m "Student Analytics Dashboard v1.0.0"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/student-analytics.git     # the address you copied
git push -u origin main
```

If git asks for a password, GitHub needs a **personal access token** rather than your account password
(GitHub: Settings, Developer settings, Personal access tokens), or you can sign in with the GitHub extension in VS Code.

## Step 2: the API on Render

1. Sign up at render.com with your GitHub account and allow it to see the `student-analytics` repository.
2. **New +**, then **Blueprint**, select the repository, and continue. Render reads `render.yaml` and shows one service,
   `student-analytics-api`, on the **Free** plan.
3. It asks for three values:
   - `ADMIN_PASSWORD`: your administrator password, **at least 10 characters**. Write it down. (If it is shorter, the API refuses to start.)
   - `DEMO_VIEWER_PASSWORD`: a password for the read-only `viewer` account that you'll share with people you're pitching to (at least 10 characters).
   - `CORS_ORIGINS`: type `http://localhost:5173` for now; you'll replace it in Step 4.
4. Press **Apply** / **Deploy**. The first build takes a few minutes. Wait until the service shows **Live**.
5. Copy the service address shown near the top, like `https://student-analytics-api-abcd.onrender.com`.
6. Check it: open `https://…onrender.com/api/health` in a browser. You should see `{"status":"ok"}`.

## Step 3: the website on Netlify

1. Sign up at netlify.com with your GitHub account.
2. **Add new site**, then **Import an existing project**, choose GitHub and the `student-analytics` repository.
3. Leave **Base directory** empty. The build command and publish folder are read from `netlify.toml`.
4. Before deploying, open **Environment variables** (on the same page, or later under Site configuration) and add:
   - Key: `VITE_API_BASE_URL`
   - Value: the Render address from Step 2, for example `https://student-analytics-api-abcd.onrender.com`
     (starts with `https://`, **no slash at the end**).
5. Deploy. When it finishes, copy the site address, like `https://random-name-123.netlify.app`. You can choose a nicer
   name under Site configuration, Domain management, **Edit site name**.

> The API address is baked into the website when it is built. If you set or change `VITE_API_BASE_URL` after a
> build, run **Deploys, Trigger deploy, Clear cache and deploy site**.

## Step 4: tell the API about the website

1. Back in Render, open the service, then **Environment**.
2. Change `CORS_ORIGINS` to the Netlify address from Step 3, exactly: `https://random-name-123.netlify.app`
   (no slash at the end, `https` not `http`). Save. Render redeploys automatically.
3. Wait for **Live** again.

## Step 5: try it

1. Open your Netlify address. If the API was asleep, wait up to a minute and reload.
2. Sign in as `admin` with your admin password. You should see the Overview with insights, charts and lists filled with demo data.
3. Open a private window and sign in as `viewer`: no Add, Edit, Delete or Import buttons, and no Users or Audit log in the menu.
4. Go through the checklist in the main README's "Release checklist" section.

## Before a pitch

- **Wake the API** a couple of minutes beforehand by opening the site, or keep it awake: a free monitoring service such as
  UptimeRobot can request `https://…onrender.com/api/health` every 5 minutes. Staying awake all month uses about 744 of the
  750 free hours, so this works for one service only.
- **Give people the `viewer` login**, not the admin one. Keep the admin login for yourself.
- **Test on a phone** over mobile data, and keep a local copy running (`python app.py` and `npm run dev`) as a fallback.
- **Remember the data is made up and resets.** Say so; it avoids awkward questions.

## Updating the demo later

```bash
git checkout main
git merge dev
git push
```

Render and Netlify both rebuild on their own within a few minutes. Then `git checkout dev` and carry on.

## Optional: your own domain

Netlify lets you attach a domain you own (Site configuration, Domain management). Afterwards change `CORS_ORIGINS` on
Render to the new address, and trigger a Netlify deploy if you changed `VITE_API_BASE_URL`.

## Troubleshooting

| Symptom | Likely cause and fix |
|---------|----------------------|
| Render build fails | Open the build log. Check `render.yaml` is at the repository root and `backend/Dockerfile` exists. If Render rejects the Blueprint, create a **Web Service** by hand instead: runtime **Docker**, Dockerfile path `./backend/Dockerfile`, Docker build context `./backend`, health check path `/api/health`, plan **Free**, and add the environment variables listed in `render.yaml` |
| Render says the service failed to start | Look at the logs. "ADMIN_PASSWORD is not acceptable" means the password is shorter than 10 characters |
| Netlify build fails with "Cannot find module react-router-dom" | `frontend/package.json` must list it. Run `cd frontend && npm install react-router-dom`, commit and push |
| Netlify build fails because it can't find `package.json` or `dist` | "Base directory" must be empty, and `netlify.toml` must be at the repository root |
| Site opens but sign-in says "Cannot reach the server" | (1) API asleep: wait a minute and retry. (2) `CORS_ORIGINS` doesn't exactly match the site address (check `https`, spelling, trailing slash). (3) `VITE_API_BASE_URL` wasn't set before the build: set it and clear cache and redeploy |
| Everything works, then data is gone | Expected on the free plan: the API restarted or slept, and the demo data was rebuilt |
| Page reload gives a 404 | `netlify.toml` redirect missing from the repository root |
