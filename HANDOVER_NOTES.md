# Handover Notes: ETF Mover Watch Project

This project tracks the top 5 gainers and losers from the top ~200 US ETFs and generates a daily report using AI analysis.

## Your Tasks:

1.  **Create a New GitHub Repository:**
    *   Go to [github.com/new](https://github.com/new).
    *   Name your repository (e.g., `etf-mover-watch`).
    *   **Public** visibility is required for free GitHub Pages.
    *   **Do NOT initialize** with README/gitignore/license.

2.  **Add Your Gemini API Key:**
    *   Go to **Settings** > **Secrets and variables** > **Actions** > **New repository secret**.
    *   Name: `GEMINI_API_KEY`
    *   Value: (Paste your key: `AIza...`)

3.  **Push the Code:**
    *   Open terminal:
        ```bash
        cd etf-mover-watch
        git add .
        git commit -m "Initial commit: ETF Mover Watch"
        git branch -M main
        git remote add origin https://github.com/YOUR_USERNAME/etf-mover-watch.git
        git push -u origin main
        ```

4.  **Enable GitHub Pages:**
    *   Go to **Settings** > **Pages**.
    *   Source: `Deploy from a branch`.
    *   Branch: `main` / `/(root)`.
    *   Click **Save**.

## Testing
Once pushed, go to the **Actions** tab in GitHub and manually run the "Daily ETF Watch" workflow to see the first report generated immediately.

## Note on Schedule
This bot is scheduled to run at **21:30 UTC** (market close) on **Weekdays (Mon-Fri)** only.
