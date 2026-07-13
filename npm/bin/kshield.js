#!/usr/bin/env node
"use strict";

const path = require("path");
const { spawnSync } = require("child_process");

const binary = path.join(__dirname, "kshield-bin");

const result = spawnSync(binary, process.argv.slice(2), { stdio: "inherit" });

if (result.error) {
  if (result.error.code === "ENOENT") {
    console.error("[kshield] Binary not found. Re-run: npm install -g kshield");
  } else {
    console.error("[kshield] Error:", result.error.message);
  }
  process.exit(1);
}

process.exit(result.status ?? 0);
