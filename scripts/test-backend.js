#!/usr/bin/env node
/**
 * Cross-platform backend test runner script
 * Runs pytest using the correct virtual environment path for Windows/Mac/Linux
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const isWindows = os.platform() === 'win32';
const rootDir = path.join(__dirname, '..');
const backendDir = path.join(rootDir, 'apps', 'backend');
const testsDir = path.join(rootDir, 'tests');
const venvDir = path.join(backendDir, '.venv');

// Get pytest path based on platform
const pytestPath = isWindows
  ? path.join(venvDir, 'Scripts', 'pytest.exe')
  : path.join(venvDir, 'bin', 'pytest');

// Check if venv exists
if (!fs.existsSync(venvDir)) {
  console.error('Error: Virtual environment not found.');
  console.error('Run "npm run install:backend" first.');
  process.exit(1);
}

// Check if pytest is installed
if (!fs.existsSync(pytestPath)) {
  console.error('Error: pytest not found in virtual environment.');
  console.error('Install test dependencies:');
  const pipPath = isWindows
    ? path.join(venvDir, 'Scripts', 'pip.exe')
    : path.join(venvDir, 'bin', 'pip');
  // Escape path for safe display in shell command (handle backslashes on Windows)
  const escapedPipPath = pipPath.replace(/\\/g, '\\\\');
  console.error(`  "${escapedPipPath}" install -r tests/requirements-test.txt`);
  process.exit(1);
}

// Get any additional args passed to the script (validated to only contain safe characters)
const args = process.argv.slice(2);
const defaultArgs = ['-v'];
const argsToUse = args.length > 0 ? args : defaultArgs;

// Validate arguments to only contain safe characters (alphanumeric, dash, underscore, dot, slash, equals)
// Reject: shell metacharacters, path traversal sequences, and command separators
// This whitelist prevents command injection through malicious arguments
const unsafePatterns = [
  /[;&|`$()]/,  // Shell metacharacters
  /\.\./,       // Path traversal
  /\x00/,       // Null bytes
];
for (const arg of argsToUse) {
  // Check for unsafe patterns first
  for (const pattern of unsafePatterns) {
    if (pattern.test(arg)) {
      console.error(`Error: Invalid argument '${arg}'. Argument contains unsafe characters.`);
      process.exit(1);
    }
  }
  // Then whitelist safe characters (alphanumeric, dash, underscore, dot, slash, colon, equals, at sign)
  // Note: backslash is intentionally excluded for Windows safety
  if (!/^[a-zA-Z0-9._/=:@+-]+$/.test(arg)) {
    console.error(`Error: Invalid argument '${arg}'. Only alphanumeric, dash, underscore, dot, slash, equals, colon, and at sign are allowed.`);
    process.exit(1);
  }
}

console.log(`> ${pytestPath} ${testsDir} ${argsToUse.join(' ')}\n`);

// Use spawn with direct array of arguments to avoid shell injection
// This is safer than building a shell command string
const proc = spawn(pytestPath, [testsDir, ...argsToUse], {
  cwd: rootDir,
  stdio: 'inherit'
});

proc.on('exit', (code) => {
  process.exit(code ?? 1);
});

proc.on('error', (err) => {
  console.error('Failed to start pytest:', err);
  process.exit(1);
});
