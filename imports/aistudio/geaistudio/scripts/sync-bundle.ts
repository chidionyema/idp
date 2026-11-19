import process from 'node:process';
import {
  materializeStaticDistExports,
  pushBundleToIngest,
} from '../src/engine/debugPackBuilder';

async function main() {
  const strict = process.argv.includes('--strict');
  const staticDist = materializeStaticDistExports(process.cwd());
  const result = await pushBundleToIngest(process.cwd(), { trigger: 'postbuild' });
  console.log(
    JSON.stringify(
      {
        ...result,
        staticDistMaterialized: staticDist.materialized,
        staticDistFilesCount: staticDist.filesWritten.length,
      },
      null,
      2
    )
  );
  if (strict && !result.pushed) {
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
