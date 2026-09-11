// Guest code runs only inside QuickJS WebAssembly. No host APIs are exposed.
const fs = require('node:fs');
const path = require('node:path');
const { getQuickJS } = require(path.join(__dirname, 'state/coding-sandbox/node_modules/quickjs-emscripten'));

async function main() {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  if (typeof input.code !== 'string' || input.code.length > 131072 || !Array.isArray(input.tests) || input.tests.length > 100) throw Error('Invalid sandbox input');
  const QuickJS = await getQuickJS();
  const rows = [];
  for (const test of input.tests) {
    const runtime = QuickJS.newRuntime();
    runtime.setMemoryLimit(64 * 1024 * 1024);
    runtime.setMaxStackSize(512 * 1024);
    const until = Date.now() + Math.min(input.testMs || 300, 1000);
    runtime.setInterruptHandler(() => Date.now() >= until);
    const vm = runtime.newContext();
    const handles = [];
    const own = result => {
      if (result.error) {
        let message;
        try { message = JSON.stringify(vm.dump(result.error)); } finally { result.error.dispose(); }
        throw Error(String(message).slice(0, 1500));
      }
      handles.push(result.value); return result.value;
    };
    try {
      // Decode input before guest code can modify globals. JSON.parse preserves __proto__ as data.
      const arg = own(vm.evalCode(`JSON.parse(${JSON.stringify(JSON.stringify(test.input))})`));
      own(vm.evalCode(input.code, 'candidate.js'));
      const fn = own(vm.evalCode('solve'));
      if (vm.typeof(fn) !== 'function') throw Error('solve is not a function');
      const result = own(vm.callFunction(fn, vm.undefined, arg));
      const kind = vm.typeof(result);
      const actual = vm.dump(result);
      const after = vm.dump(arg);
      rows.push({id: test.id, outputKind: actual === null ? 'null' : kind, actual,
        mutated: JSON.stringify(after) !== JSON.stringify(test.input)});
    } catch (error) { rows.push({id: test.id, error: String(error).slice(0, 1500)}); }
    finally {
      for (const h of handles.reverse()) h.dispose();
      vm.dispose(); runtime.dispose();
    }
  }
  process.stdout.write(JSON.stringify({engine: 'quickjs-emscripten', version: '0.32.0', node: process.version,
    isolation: 'WebAssembly guest with no exposed host functions or module loader', memoryLimitBytes: 64*1024*1024, testMs: input.testMs || 300, rows}));
}
main().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
