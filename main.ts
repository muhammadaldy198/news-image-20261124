// main.ts — news-image-20261124 entry point.
//
// The broadsheet is drawn once, by hand, in draw.py (PIL) and committed
// here as entry.png. At grade time the sandbox has no Python, no PIL and
// no fonts, so this program does the one thing the rules ask for: it
// copies the finished image to /output/entry.png, byte for byte, with no
// network and no randomness. Two runs therefore write identical bytes.
//
// Guards: the source must exist, be non-empty, and start with the PNG
// magic bytes; the copy is verified by size after the write.

import { chmod, copyFile, mkdir, open, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "entry.png");
const outDir = process.env.OUTPUT_DIR ?? "/output";
const target = join(outDir, "entry.png");

async function main(): Promise<void> {
  const info = await stat(source).catch(() => {
    throw new Error(`entry image missing: ${source}`);
  });
  if (info.size === 0) {
    throw new Error("entry image is empty");
  }
  if (info.size > 1_048_576) {
    throw new Error(`entry image too large: ${info.size} bytes (limit 1 MiB)`);
  }
  // Magic check reads only the first 8 bytes, not the whole file.
  const fh = await open(source, "r");
  try {
    const head = Buffer.alloc(8);
    const { bytesRead } = await fh.read(head, 0, 8, 0);
    if (bytesRead < 8 || !head.equals(PNG_MAGIC)) {
      throw new Error("entry image is not a PNG (bad magic bytes)");
    }
  } finally {
    await fh.close();
  }
  await mkdir(outDir, { recursive: true });
  await copyFile(source, target);
  await chmod(target, 0o644);
  const copied = await stat(target);
  if (copied.size !== info.size) {
    throw new Error(
      `copy size mismatch: wrote ${copied.size}, expected ${info.size}`,
    );
  }
  console.log(`wrote ${target} (${copied.size} bytes)`);
}

await main();
