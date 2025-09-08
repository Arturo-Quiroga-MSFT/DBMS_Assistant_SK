#!/usr/bin/env node
/**
 * Simple release helper: bumps version, updates CHANGELOG heading date if unreleased, and commits tag hints.
 */
const fs = require('fs');
const path = require('path');

const semverType = process.argv[2];
if(!['patch','minor','major'].includes(semverType)) {
  console.error('Usage: npm run release:<patch|minor|major>');
  process.exit(1);
}

const pkgPath = path.join(__dirname, '..', 'package.json');
const changelogPath = path.join(__dirname, '..', 'CHANGELOG.md');

function bump(version, type){
  const [maj, min, pat] = version.split('.').map(Number);
  if(type==='patch') return `${maj}.${min}.${pat+1}`;
  if(type==='minor') return `${maj}.${min+1}.0`;
  if(type==='major') return `${maj+1}.0.0`;
}

const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
const oldVersion = pkg.version;
const newVersion = bump(oldVersion, semverType);

pkg.version = newVersion;
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2)+"\n");

// Prepend new section to CHANGELOG
let changelog = fs.readFileSync(changelogPath, 'utf8');
const today = new Date().toISOString().substring(0,10);
const header = `## [${newVersion}] - ${today}`;
if(changelog.includes(header)) {
  console.warn('Changelog already has entry for version, append details manually.');
} else {
  const insertion = `${header}\n### Changed\n- Version bump to ${newVersion}.\n\n`;
  const lines = changelog.split(/\r?\n/);
  // Insert after first two lines (title + blank or description lines)
  const idx = lines.findIndex(l=>l.startsWith('## ['));
  if(idx !== -1) {
    lines.splice(idx,0,insertion.trim());
    changelog = lines.join('\n');
  } else {
    changelog += '\n' + insertion;
  }
  fs.writeFileSync(changelogPath, changelog);
}

console.log(`Bumped version ${oldVersion} -> ${newVersion}`);
console.log('Next steps:');
console.log('  git add package.json CHANGELOG.md');
console.log(`  git commit -m \"chore(release): v${newVersion}\"`);
console.log(`  git tag v${newVersion}`);
console.log('  npm run package');
