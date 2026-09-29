#!/usr/bin/env node
/**
 * bloomin8_optimize.js
 *
 * 1. Lit la config depuis les variables d'environnement (exportées par
 *    run.sh à partir des options de l'add-on — plus de config.json
 *    modifiable à chaud : un changement de config redémarre l'add-on,
 *    donc on peut se permettre une reconstruction complète simple sans
 *    workflow de confirmation "garder/vider" séparé).
 * 2. Récupère les assets de l'album Immich source, filtre STRICTEMENT selon
 *    l'orientation configurée (portrait/landscape, via width/height).
 * 3. Télécharge, optimise (resize/crop + correction colorimétrique) et
 *    dépose dans destination_path/<portrait|landscape>/ — c'est le
 *    sous-dossier que bloomin8_pull 0.2.x attend sous image_dir.
 *
 * IMPORTANT — pipeline de couleur :
 * BLOOMIN8 fait SON PROPRE dithering en interne à partir d'un JPEG en tons
 * continus. Pré-ditherer côté script est CONTRE-PRODUCTIF (double
 * dithering + artefacts de recompression). On applique donc : resize/crop
 * -> gamma -> saturation -> lift des ombres -> export JPEG qualité
 * élevée, SANS quantification de palette.
 */
const fs = require("fs");
const path = require("path");
const fetch = require("node-fetch");
const { createCanvas, loadImage } = require("canvas");

const DATA_DIR = process.env.DATA_DIR || "/data";
const STATE_PATH = path.join(DATA_DIR, "state", "bloomin8_optimize.json");
const LOCK_PATH = path.join(DATA_DIR, "state", "bloomin8_optimize.lock");

function getConfig() {
  return {
    immich: {
      server: (process.env.IMMICH_SERVER || "").replace(/\/$/, ""),
      apiKey: process.env.IMMICH_API_KEY || "",
    },
    bloomin8: {
      enabled: (process.env.BLOOMIN8_ENABLED || "true").toLowerCase() !== "false",
      albumId: process.env.BLOOMIN8_ALBUM_ID || "",
      orientation: process.env.BLOOMIN8_ORIENTATION || "landscape",
      baseDir: process.env.BLOOMIN8_DEST_PATH || "/media/bloomin8",
      resolution: {
        width: parseInt(process.env.BLOOMIN8_RES_WIDTH || "1600", 10),
        height: parseInt(process.env.BLOOMIN8_RES_HEIGHT || "1200", 10),
      },
      color: {
        gamma: parseFloat(process.env.BLOOMIN8_COLOR_GAMMA || "0.85"),
        saturation: parseFloat(process.env.BLOOMIN8_COLOR_SATURATION || "1.15"),
        lift: parseInt(process.env.BLOOMIN8_COLOR_LIFT || "13", 10),
        liftThreshold: parseInt(process.env.BLOOMIN8_COLOR_LIFT_THRESHOLD || "90", 10),
      },
    },
  };
}

function acquireLock() {
  fs.mkdirSync(path.dirname(LOCK_PATH), { recursive: true });
  if (fs.existsSync(LOCK_PATH)) {
    const oldPid = parseInt(fs.readFileSync(LOCK_PATH, "utf-8").trim(), 10);
    try {
      process.kill(oldPid, 0);
      return false;
    } catch (e) {
      // verrou périmé, on continue
    }
  }
  fs.writeFileSync(LOCK_PATH, String(process.pid));
  return true;
}

function releaseLock() {
  try {
    fs.unlinkSync(LOCK_PATH);
  } catch (e) {
    // déjà absent
  }
}

let stopRequested = false;
process.on("SIGTERM", () => {
  stopRequested = true;
  log("Arrêt demandé — sauvegarde de la progression en cours avant de quitter...", "WARN");
});

function log(message, level = "INFO") {
  const ts = new Date().toISOString();
  const line = `${ts} [${level}] ${message}\n`;
  fs.mkdirSync(path.join(DATA_DIR, "logs"), { recursive: true });
  fs.appendFileSync(path.join(DATA_DIR, "logs", "bloomin8_optimize.log"), line);
  process.stdout.write(line);
}

function loadState() {
  if (!fs.existsSync(STATE_PATH)) return { processed_asset_ids: [], last_run: { album_id: null, orientation: null } };
  return JSON.parse(fs.readFileSync(STATE_PATH, "utf-8"));
}

function saveState(state) {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2), "utf-8");
}

function clearDestination(destDir) {
  if (fs.existsSync(destDir)) {
    for (const f of fs.readdirSync(destDir)) {
      fs.rmSync(path.join(destDir, f), { force: true });
    }
  }
  log(`Dossier de destination vidé : ${destDir}`);
}

async function fetchAlbumAssets(server, apiKey, albumId) {
  const url = `${server}/api/search/metadata`;
  const body = { albumIds: [albumId], page: 1, size: 1000, type: "IMAGE" };

  const resp = await fetch(url, {
    method: "POST",
    headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    throw new Error(`Erreur lecture album ${albumId} : HTTP ${resp.status}`);
  }

  const data = await resp.json();
  const assets = data.assets?.items || [];
  log(`Album ${albumId} lu : ${assets.length} asset(s)`);
  return assets;
}

function matchesOrientation(asset, wantedOrientation) {
  const w = asset?.width;
  const h = asset?.height;
  if (!w || !h) return false; // pas de métadonnées fiables -> exclu
  const isPortrait = h > w;
  return wantedOrientation === "portrait" ? isPortrait : !isPortrait;
}

async function downloadOriginal(server, apiKey, assetId) {
  const resp = await fetch(`${server}/api/assets/${assetId}/original`, {
    headers: { "x-api-key": apiKey },
  });
  if (!resp.ok) {
    throw new Error(`Téléchargement asset ${assetId} : HTTP ${resp.status}`);
  }
  return Buffer.from(await resp.arrayBuffer());
}

function applyColorGrading(imageData, { gamma, saturation, lift, liftThreshold }) {
  const data = imageData.data;

  const gammaLUT = new Uint8ClampedArray(256);
  for (let i = 0; i < 256; i++) {
    gammaLUT[i] = Math.round(255 * Math.pow(i / 255, gamma));
  }

  for (let i = 0; i < data.length; i += 4) {
    let r = gammaLUT[data[i]];
    let g = gammaLUT[data[i + 1]];
    let b = gammaLUT[data[i + 2]];

    if (saturation !== 1) {
      const luma = 0.299 * r + 0.587 * g + 0.114 * b;
      r = luma + (r - luma) * saturation;
      g = luma + (g - luma) * saturation;
      b = luma + (b - luma) * saturation;
    }

    if (lift > 0) {
      r = liftChannel(r, lift, liftThreshold);
      g = liftChannel(g, lift, liftThreshold);
      b = liftChannel(b, lift, liftThreshold);
    }

    data[i] = clamp255(r);
    data[i + 1] = clamp255(g);
    data[i + 2] = clamp255(b);
  }

  return imageData;
}

function liftChannel(value, lift, threshold) {
  if (value >= threshold) return value;
  const depth = 1 - value / threshold;
  return value + lift * depth;
}

function clamp255(v) {
  return v < 0 ? 0 : v > 255 ? 255 : Math.round(v);
}

async function optimizeForBloomin8(buffer, targetWidth, targetHeight, colorOptions, orientation) {
  const img = await loadImage(buffer);

  const srcRatio = img.width / img.height;
  const dstRatio = targetWidth / targetHeight;
  let sx = 0, sy = 0, sw = img.width, sh = img.height;
  if (srcRatio > dstRatio) {
    sw = img.height * dstRatio;
    sx = (img.width - sw) / 2;
  } else {
    sh = img.width / dstRatio;
    sy = (img.height - sh) / 2;
  }

  const canvas = createCanvas(targetWidth, targetHeight);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, sx, sy, sw, sh, 0, 0, targetWidth, targetHeight);

  const imageData = ctx.getImageData(0, 0, targetWidth, targetHeight);
  applyColorGrading(imageData, colorOptions);
  ctx.putImageData(imageData, 0, 0);

  let finalCanvas = canvas;

  // Rotation de compensation : le firmware BLOOMIN8 attend son buffer natif
  // dans un sens fixe côté API /eink_pull. Confirmé par test manuel : sans
  // cette rotation, l'image ressort pivotée en montage paysage.
  if (orientation === "landscape") {
    const rotated = createCanvas(targetHeight, targetWidth);
    const rctx = rotated.getContext("2d");
    rctx.translate(targetHeight, 0);
    rctx.rotate(Math.PI / 2);
    rctx.drawImage(canvas, 0, 0);
    finalCanvas = rotated;
  }

  return finalCanvas.toBuffer("image/jpeg", { quality: 0.95 });
}

async function mainBody() {
  const cfg = getConfig();
  const bloomin8 = cfg.bloomin8;

  if (!bloomin8.enabled) {
    log("Script désactivé dans la config, arrêt.");
    return;
  }
  if (!bloomin8.albumId) {
    log("Aucun album_id configuré, arrêt.", "WARN");
    return;
  }

  // bloomin8_pull 0.2.x attend une arborescence portrait/ et landscape/
  // SOUS destination_path (il pioche lui-même le bon sous-dossier selon
  // l'orientation configurée côté HA pour chaque device).
  const destDir = path.join(bloomin8.baseDir, bloomin8.orientation === "portrait" ? "portrait" : "landscape");
  fs.mkdirSync(destDir, { recursive: true });

  let state = loadState();
  const lastRun = state.last_run || { album_id: null, orientation: null };
  const configChanged =
    (lastRun.album_id !== null && lastRun.album_id !== bloomin8.albumId) ||
    (lastRun.orientation !== null && lastRun.orientation !== bloomin8.orientation);

  let fullRebuild = false;
  if (configChanged) {
    // La config ne change plus qu'au redémarrage de l'add-on (action
    // volontaire de l'utilisateur) : plus besoin d'un workflow de
    // confirmation garder/vider, on reconstruit simplement à neuf.
    log(`Config changée (album/orientation) : reconstruction complète de ${destDir}.`);
    clearDestination(destDir);
    state = { processed_asset_ids: [], last_run: lastRun };
    fullRebuild = true;
  }

  const assets = await fetchAlbumAssets(cfg.immich.server, cfg.immich.apiKey, bloomin8.albumId);
  const filtered = assets.filter((a) => matchesOrientation(a, bloomin8.orientation));

  log(`${assets.length} asset(s) dans l'album, ${filtered.length} correspondent à l'orientation "${bloomin8.orientation}".`);

  const processedSet = new Set(state.processed_asset_ids || []);
  let done = 0;

  for (const asset of filtered) {
    if (stopRequested) {
      saveState({ processed_asset_ids: Array.from(processedSet), last_run: { album_id: bloomin8.albumId, orientation: bloomin8.orientation } });
      log(`Arrêt propre après ${done} image(s) optimisée(s) — état sauvegardé.`);
      return;
    }

    if (!fullRebuild && processedSet.has(asset.id)) continue;

    try {
      const original = await downloadOriginal(cfg.immich.server, cfg.immich.apiKey, asset.id);
      const optimized = await optimizeForBloomin8(
        original,
        bloomin8.resolution.width,
        bloomin8.resolution.height,
        bloomin8.color,
        bloomin8.orientation
      );
      const outPath = path.join(destDir, `${asset.id}.jpg`);
      fs.writeFileSync(outPath, optimized);
      processedSet.add(asset.id);
      done += 1;
    } catch (e) {
      log(`Erreur sur asset ${asset.id} : ${e.message}`, "ERROR");
    }
  }

  saveState({
    processed_asset_ids: Array.from(processedSet),
    last_run: { album_id: bloomin8.albumId, orientation: bloomin8.orientation },
  });

  log(`Run terminé. ${done} image(s) optimisée(s) et déposée(s) dans ${destDir}.`);
}

async function main() {
  if (!acquireLock()) {
    log("Une autre instance tourne déjà, run ignoré.", "WARN");
    return;
  }
  try {
    await mainBody();
  } finally {
    releaseLock();
  }
}

main().catch((e) => {
  log(`Erreur fatale : ${e.stack || e.message}`, "ERROR");
  process.exit(1);
});
