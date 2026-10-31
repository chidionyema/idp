// forensic-pi-oracle.mjs -- run the REAL Pi edit engine over a case file.
//
// The oracle is the installed runtime, not a copy of it: the whole point of this
// file is that the Python replay engine in forensic_replay.py is compared against
// what Pi actually does to a file. A mirror of the runtime would only prove that
// two copies of the same idea agree.
//
// Usage: node forensic-pi-oracle.mjs cases.json
// Exit:  0 = ran, stdout is a JSON array of {ok, content|error}
//        3 = the Pi runtime was not found (pending, never a false pass)
//
// The runtime is discovered in this order:
//   1. $PI_RUNTIME_DIR  (the dist/ directory of @earendil-works/pi-coding-agent)
//   2. every installed nvm node version, newest first
//   3. the usual global npm prefixes
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { existsSync, readdirSync } from "node:fs";
import { pathToFileURL } from "node:url";

function findRuntime() {
	const candidates = [];
	if (process.env.PI_RUNTIME_DIR) {
		candidates.push(process.env.PI_RUNTIME_DIR);
	}
	const nvmRoot = path.join(os.homedir(), ".nvm", "versions", "node");
	if (existsSync(nvmRoot)) {
		const versions = readdirSync(nvmRoot).sort().reverse();
		for (const version of versions) {
			candidates.push(
				path.join(
					nvmRoot,
					version,
					"lib",
					"node_modules",
					"@earendil-works",
					"pi-coding-agent",
					"dist",
				),
			);
		}
	}
	candidates.push(
		"/usr/local/lib/node_modules/@earendil-works/pi-coding-agent/dist",
		"/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent/dist",
	);
	for (const dir of candidates) {
		if (existsSync(path.join(dir, "core", "tools", "edit-diff.js"))) {
			return dir;
		}
	}
	return null;
}

const runtime = findRuntime();
if (!runtime) {
	process.stderr.write(
		"pi runtime not found: set PI_RUNTIME_DIR to the dist/ directory of @earendil-works/pi-coding-agent\n",
	);
	process.exit(3);
}

const editDiff = await import(
	pathToFileURL(path.join(runtime, "core", "tools", "edit-diff.js")).href
);
const textUtils = await import(
	pathToFileURL(path.join(runtime, "utils", "text.js")).href
);
const {
	applyEditsToNormalizedContent,
	normalizeToLF,
	detectLineEnding,
	restoreLineEndings,
} = editDiff;
const { splitBom } = textUtils;

const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = cases.map((c) => {
	try {
		const { bom, text } = splitBom(c.base);
		const normalizedContent = normalizeToLF(text);
		const { newContent } = applyEditsToNormalizedContent(
			normalizedContent,
			c.edits,
			c.path ?? "f.txt",
		);
		const ending = detectLineEnding(text);
		return { ok: true, content: bom + restoreLineEndings(newContent, ending) };
	} catch (err) {
		return { ok: false, error: err instanceof Error ? err.message : String(err) };
	}
});
process.stdout.write(JSON.stringify(out));
