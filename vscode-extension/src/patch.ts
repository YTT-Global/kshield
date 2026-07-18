interface DiffOp {
  type: ' ' | '-' | '+';
  text: string;
}

interface Hunk {
  oldStart: number;
  ops: DiffOp[];
}

const HUNK_HEADER = /^@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@/;

function parseHunks(diffText: string): Hunk[] {
  const hunks: Hunk[] = [];
  let current: Hunk | null = null;

  for (const line of diffText.split(/\r?\n/)) {
    if (line.startsWith('---') || line.startsWith('+++')) {
      continue;
    }
    const header = HUNK_HEADER.exec(line);
    if (header) {
      if (current) {
        hunks.push(current);
      }
      current = { oldStart: parseInt(header[1], 10), ops: [] };
      continue;
    }
    if (!current) {
      continue;
    }
    if (line.startsWith('+')) {
      current.ops.push({ type: '+', text: line.slice(1) });
    } else if (line.startsWith('-')) {
      current.ops.push({ type: '-', text: line.slice(1) });
    } else if (line.startsWith(' ')) {
      current.ops.push({ type: ' ', text: line.slice(1) });
    }
  }
  if (current) {
    hunks.push(current);
  }
  return hunks;
}

/**
 * Applies a unified diff (as produced by backend/app/engine/remediation.py via
 * Python's difflib.unified_diff) to the given text. Returns null if a hunk's
 * context/removed lines no longer match — the file changed since the finding
 * was generated, so it's safer to bail out than to corrupt the file.
 */
export function applyUnifiedDiff(original: string, diffText: string): string | null {
  if (!diffText.trim()) {
    return null;
  }

  const hunks = parseHunks(diffText);
  if (hunks.length === 0) {
    return null;
  }

  const newline = original.includes('\r\n') ? '\r\n' : '\n';
  const lines = original.split(/\r?\n/);

  // Apply bottom-to-top so earlier hunks' line numbers stay valid.
  for (const hunk of [...hunks].sort((a, b) => b.oldStart - a.oldStart)) {
    let cursor = hunk.oldStart - 1;
    if (cursor < 0 || cursor > lines.length) {
      return null;
    }

    const replacement: string[] = [];
    for (const op of hunk.ops) {
      if (op.type === ' ') {
        if (lines[cursor] !== op.text) {
          return null;
        }
        replacement.push(op.text);
        cursor++;
      } else if (op.type === '-') {
        if (lines[cursor] !== op.text) {
          return null;
        }
        cursor++;
      } else {
        replacement.push(op.text);
      }
    }

    lines.splice(hunk.oldStart - 1, cursor - (hunk.oldStart - 1), ...replacement);
  }

  return lines.join(newline);
}
