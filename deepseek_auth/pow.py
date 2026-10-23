"""DeepSeek Proof-of-Work (PoW) Solver via Node.js WASM bridge.
Pure zero-python-dependency solution: runs via Node.js runtime built into the host.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WASM_FILE = Path(__file__).parent / "wasm" / "sha3_wasm_bg.wasm"

NODE_SCRIPT = """
const fs = require('fs');

const wasmPath = process.argv[1];
const challengeHex = process.argv[2];
const salt = process.argv[3];
const expireAt = parseInt(process.argv[4], 10);
const difficulty = parseFloat(process.argv[5]);

const wasmBuffer = fs.readFileSync(wasmPath);

function writeStr(str, exp) {
  const enc = new TextEncoder().encode(str);
  const ptr = exp.__wbindgen_export_0(enc.length, 1);
  const mem = new Uint8Array(exp.memory.buffer);
  mem.set(enc, ptr);
  return [ptr, enc.length];
}

async function solve() {
  const mod = await WebAssembly.instantiate(wasmBuffer, {});
  const exp = mod.instance.exports;
  const prefix = `${salt}_${expireAt}_`;
  const retptr = exp.__wbindgen_add_to_stack_pointer(-16);
  try {
    const [p1, l1] = writeStr(challengeHex, exp);
    const [p2, l2] = writeStr(prefix, exp);
    exp.wasm_solve(retptr, p1, l1, p2, l2, difficulty);
    const view = new DataView(exp.memory.buffer);
    const flag = view.getInt32(retptr + 0, true);
    const answer = view.getFloat64(retptr + 8, true);
    if (flag === 0) {
      process.stderr.write("NO_SOLUTION");
      process.exit(1);
    }
    process.stdout.write(String(Math.trunc(answer)));
  } finally {
    exp.__wbindgen_add_to_stack_pointer(16);
  }
}

solve().catch(err => {
  process.stderr.write(String(err));
  process.exit(1);
});
"""

def solve_pow_challenge(challenge_data: dict[str, Any]) -> str:
    """Solve the PoW challenge from DeepSeek and return the base64-encoded x-ds-pow-response header value."""
    algorithm = challenge_data.get("algorithm", "DeepSeekHashV1")
    challenge_hex = challenge_data.get("challenge", "")
    salt = challenge_data.get("salt", "")
    expire_at = int(challenge_data.get("expire_at", 0))
    difficulty = float(challenge_data.get("difficulty", 144000))
    signature = challenge_data.get("signature", "")
    target_path = challenge_data.get("target_path", "/api/v0/chat/completion")

    if algorithm != "DeepSeekHashV1":
        raise ValueError(f"Unsupported PoW algorithm: {algorithm}")

    cmd = [
        "node",
        "-e",
        NODE_SCRIPT,
        str(WASM_FILE),
        challenge_hex,
        salt,
        str(expire_at),
        str(difficulty),
    ]

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if res.returncode != 0:
            raise RuntimeError(f"node exit {res.returncode}: stdout='{res.stdout}', stderr='{res.stderr}'")
        answer_val = int(res.stdout.strip())
    except Exception as exc:
        logger.error("Failed to solve DeepSeek PoW challenge via Node WASM: %s", exc)
        raise RuntimeError(f"DeepSeek PoW solver failure: {exc}") from exc

    pow_dict = {
        "algorithm": algorithm,
        "challenge": challenge_hex,
        "salt": salt,
        "answer": answer_val,
        "signature": signature,
        "target_path": target_path,
    }
    encoded = base64.b64encode(json.dumps(pow_dict, separators=(",", ":")).encode("utf-8")).decode("utf-8").strip()
    return encoded
