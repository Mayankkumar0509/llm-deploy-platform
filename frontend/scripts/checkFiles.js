const fs = require('fs');
const path = require('path');

const root = process.cwd();
const checkDirs = ['pages', 'components', 'lib'];
let found = [];

for (const dir of checkDirs) {
  const full = path.join(root, dir);
  if (!fs.existsSync(full)) continue;

  const files = fs.readdirSync(full);
  for (const f of files) {
    if (f.endsWith('.ts') || f.endsWith('.tsx')) {
      found.push(path.join(dir, f));
    }
  }
}

if (found.length > 0) {
  console.error('TypeScript files detected (rename to .js/.jsx or enable TS):');
  console.error(found.join('\n'));
  process.exit(1);
} else {
  console.log('OK: No .ts/.tsx files found.');
  process.exit(0);
}

