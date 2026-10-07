#!/usr/bin/env node
/**
 * Postinstall script — downloads the correct platform binary from GitHub Releases
 * and places it alongside the package so bin/kshield.js can find it.
 */
"use strict";

const https = require("https");
const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const REPO = "YTT-Global/kshield";
const VERSION = process.env.KSHIELD_VERSION || require("../package.json").version;
const BINARY_DIR = path.join(__dirname, "..", "bin");

function platform() {
  const arch = os.arch() === "arm64" ? "aarch64" : "x86_64";
  switch (os.platform()) {
    case "darwin":  return `${arch}-apple-darwin`;
    case "linux":   return `${arch}-unknown-linux-gnu`;
    case "win32":   return arch === "x86_64" ? "x86_64-pc-windows-msvc" : null;
    default: return null;
  }
}

function isWindows() {
  return os.platform() === "win32";
}

function download(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    function get(u) {
      https.get(u, (res) => {
        if (res.statusCode === 301 || res.statusCode === 302) {
          return get(res.headers.location);
        }
        if (res.statusCode !== 200) {
          return reject(new Error(`HTTP ${res.statusCode} for ${u}`));
        }
        res.pipe(file);
        file.on("finish", () => file.close(resolve));
      }).on("error", reject);
    }
    get(url);
  });
}

async function main() {
  const plat = platform();
  if (!plat) {
    console.warn(`[kshield] Unsupported platform: ${os.platform()}/${os.arch()}`);
    console.warn("[kshield] Build from source: https://github.com/" + REPO);
    return;
  }

  const archiveExt = isWindows() ? "zip" : "tar.gz";
  const archive = `kshield-${plat}.${archiveExt}`;
  const url = `https://github.com/${REPO}/releases/download/v${VERSION}/${archive}`;
  const tmp = path.join(os.tmpdir(), archive);
  const binaryDest = path.join(BINARY_DIR, isWindows() ? "kshield-bin.exe" : "kshield-bin");

  console.log(`[kshield] Downloading binary for ${plat}...`);

  try {
    await download(url, tmp);
    if (isWindows()) {
      // Windows ships tar.exe too (since Win10 1803+), which also unzips .zip archives.
      execSync(`tar -xf "${tmp}" -C "${BINARY_DIR}"`, { stdio: "ignore" });
    } else {
      execSync(`tar -xzf "${tmp}" -C "${BINARY_DIR}"`, { stdio: "ignore" });
    }
    const extracted = path.join(BINARY_DIR, isWindows() ? "kshield.exe" : "kshield");
    if (fs.existsSync(extracted)) {
      fs.renameSync(extracted, binaryDest);
      if (!isWindows()) fs.chmodSync(binaryDest, 0o755);
    }
    fs.unlinkSync(tmp);
    console.log("[kshield] Installed successfully.");
  } catch (err) {
    console.warn("[kshield] Could not download binary:", err.message);
    console.warn("[kshield] Run: npx @ytt-global/kshield --help  (will try again)");
  }
}

main();
