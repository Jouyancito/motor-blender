// gltf_validate.js -- Khronos glTF-Validator runner for recetas/gltf_check.py.
//   node tools/gltf_validate.js <file.glb>   -> JSON summary on stdout
// Exit 0 = ran (read numErrors), 2 = validator module not found, 3 = bad usage.
// The module is resolved from $MOTOR_GLTF_VALIDATOR_DIR (a directory holding
// node_modules/gltf-validator), default ~/.cache/motor-gltf-validator.
const fs = require('fs');
const os = require('os');
const path = require('path');

const base = process.env.MOTOR_GLTF_VALIDATOR_DIR ||
  path.join(os.homedir(), '.cache', 'motor-gltf-validator');
let validator;
try {
  validator = require(path.join(base, 'node_modules', 'gltf-validator'));
} catch (e) {
  console.log(JSON.stringify({ error: 'validator not installed', base }));
  process.exit(2);
}
const file = process.argv[2];
if (!file) { console.log(JSON.stringify({ error: 'usage: gltf_validate.js <file>' })); process.exit(3); }
const bytes = new Uint8Array(fs.readFileSync(file));
validator.validateBytes(bytes, { uri: path.basename(file), maxIssues: 200 }).then((r) => {
  const i = r.issues;
  console.log(JSON.stringify({
    version: validator.version(), file: path.basename(file),
    numErrors: i.numErrors, numWarnings: i.numWarnings, numInfos: i.numInfos,
    numHints: i.numHints,
    errors: i.messages.filter((m) => m.severity === 0).slice(0, 10)
      .map((m) => m.code + ' @ ' + m.pointer + ': ' + m.message),
    warnings: i.messages.filter((m) => m.severity === 1).slice(0, 10)
      .map((m) => m.code + ' @ ' + m.pointer),
  }));
}).catch((e) => { console.log(JSON.stringify({ error: String(e) })); process.exit(1); });
