"use strict";
const repository = "rionhadergjonaj-web/Repaintko";
const releasesPage = `https://github.com/${repository}/releases`;
function trustedAsset(url) {
  try { const u = new URL(url); return u.protocol === "https:" && u.hostname === "github.com" && u.pathname.startsWith(`/${repository}/releases/download/`); } catch { return false; }
}
async function loadReleases() {
  const status = document.getElementById("release-status");
  try {
    const response = await fetch(`https://api.github.com/repos/${repository}/releases?per_page=10`, {headers:{Accept:"application/vnd.github+json"}, signal:AbortSignal.timeout(8000)});
    if (!response.ok) throw new Error("release unavailable");
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error("invalid response");
    const releases = data.filter(r => !r.draft && !r.prerelease);
    if (!releases.length) { status.textContent = "Das erste öffentliche Setup wird vorbereitet."; return; }
    // The /latest endpoint respects GitHub's explicitly selected latest release.
    const latestResponse = await fetch(`https://api.github.com/repos/${repository}/releases/latest`, {signal:AbortSignal.timeout(8000)});
    if (!latestResponse.ok) throw new Error("latest unavailable");
    const latest = await latestResponse.json();
    const asset = (latest.assets || []).find(a => /^Repaintko-Setup-[\d.]+\.exe$/i.test(a.name) && trustedAsset(a.browser_download_url));
    status.textContent = `Aktuelle Veröffentlichung: ${latest.tag_name}`;
    if (asset) { const button = document.getElementById("download-button"); button.href = asset.browser_download_url; button.textContent = `Für Windows herunterladen · ${Math.round(asset.size / 1048576)} MB ↓`; }
    const list = document.getElementById("release-list"); list.replaceChildren();
    for (const release of releases.slice(0, 5)) {
      const article = document.createElement("article"); article.className = "release";
      const heading = document.createElement("h3"); heading.textContent = release.name || release.tag_name;
      const date = document.createElement("time"); date.dateTime = release.published_at; date.textContent = new Date(release.published_at).toLocaleDateString("de-CH");
      const body = document.createElement("p"); body.textContent = (release.body || "Details auf GitHub.").slice(0, 4000);
      article.append(heading, date, body); list.append(article);
    }
  } catch { status.textContent = "Die Versionsabfrage ist gerade nicht verfügbar. Alle Setups findest du bei den Veröffentlichungen."; document.getElementById("download-button").href = releasesPage; }
}
loadReleases();
