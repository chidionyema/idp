// forensic-cline-oracle.ts -- run the REAL upstream Cline executors over a case file.
//
// This file is the harness only. The executors it drives are the upstream Cline
// sources, fetched at test time by forensic-selftest.py into
// ~/.estate/cache/forensic-oracle/cline/ from a PINNED commit:
//
//   cline/cline@a6507a62a147db4a35e27f4294589742ccac5060
//   sdk/packages/core/src/extensions/tools/executors/{editor,apply-patch,apply-patch-parser,line-endings}.ts
//
// Upstream code is never vendored into this repository: it is fetched, pinned and
// hashed at test time, so the oracle is the upstream implementation and its
// provenance is checkable.
//
// This harness MUST sit in the same directory as those four upstream files,
// because it imports them by relative path.
//
// Usage: node --experimental-transform-types forensic-cline-oracle.ts cases.json
// Exit:  0 = ran, stdout is a JSON array of {ok, message, content} or {ok:false, error}
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createEditorExecutor } from "./editor.ts";
import { createApplyPatchExecutor } from "./apply-patch.ts";

const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const results: any[] = [];

for (const c of cases) {
	const dir = fs.mkdtempSync(path.join(os.tmpdir(), "clinecase-"));
	const cwd = c.cwd === "abs" ? dir : (c.cwd ?? dir);
	const target = c.path ?? "f.txt";
	const abs = c.abs ? String(c.input.path) : path.resolve(cwd, target);
	if (c.base !== null && c.base !== undefined) {
		fs.mkdirSync(path.dirname(abs), { recursive: true });
		fs.writeFileSync(abs, c.base);
	}
	try {
		if (c.tool === "editor") {
			const executor = createEditorExecutor({});
			const message = await executor(c.input, cwd, {} as any);
			const after = fs.existsSync(abs) ? fs.readFileSync(abs, "utf8") : null;
			results.push({ ok: true, message, content: after });
		} else {
			const executor = createApplyPatchExecutor({});
			const message = await executor(c.input, cwd, {} as any);
			const paths = message
				.split("\n")
				.slice(1)
				.map((l: string) => l.split(": [deleted]")[0].split(" -> ")[0].trim())
				.filter((l: string) => l.length > 0);
			const after: Record<string, string | null> = {};
			for (const rp of paths) {
				const p = path.resolve(cwd, rp);
				after[rp] = fs.existsSync(p) ? fs.readFileSync(p, "utf8") : null;
			}
			results.push({ ok: true, message, content: after });
		}
	} catch (e) {
		results.push({ ok: false, error: e instanceof Error ? e.message : String(e) });
	}
	fs.rmSync(dir, { recursive: true, force: true });
}

process.stdout.write(JSON.stringify(results));
