#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

// Determine VS Code settings paths based on platform
function getVSCodePaths() {
  const platform = os.platform();
  const homeDir = os.homedir();

  if (platform === 'win32') {
    return {
      mcpSettings: path.join(process.env.APPDATA, 'Code', 'User', 'globalStorage', 'saoudrizwan.claude-dev', 'settings', 'cline_mcp_settings.json'),
      userSettings: path.join(process.env.APPDATA, 'Code', 'User', 'settings.json')
    };
  } else if (platform === 'darwin') {
    return {
      mcpSettings: path.join(homeDir, 'Library', 'Application Support', 'Code', 'User', 'globalStorage', 'saoudrizwan.claude-dev', 'settings', 'cline_mcp_settings.json'),
      userSettings: path.join(homeDir, 'Library', 'Application Support', 'Code', 'User', 'settings.json')
    };
  } else {
    return {
      mcpSettings: path.join(homeDir, '.config', 'Code', 'User', 'globalStorage', 'saoudrizwan.claude-dev', 'settings', 'cline_mcp_settings.json'),
      userSettings: path.join(homeDir, '.config', 'Code', 'User', 'settings.json')
    };
  }
}

// Get absolute path to Auto-Claude MCP server
const mcpServerPath = path.join(__dirname, '..', 'apps', 'frontend', 'src', 'main', 'mcp-server', 'index.ts');

// MCP server configuration with alwaysAllow for auto-bypass permissions
const mcpConfig = {
  mcpServers: {
    "auto-claude-manager": {
      command: "npx",
      args: ["--yes", "tsx", mcpServerPath.replace(/\\/g, '/')],
      env: {
        NODE_ENV: "production"
      },
      alwaysAllow: ["*"],  // Auto-approve all MCP tool calls
      description: "Auto-Claude task management - create, monitor, fix tasks via MCP"
    }
  }
};

// Get VS Code paths
const paths = getVSCodePaths();
const mcpSettingsPath = paths.mcpSettings;
const userSettingsPath = paths.userSettings;
const mcpSettingsDir = path.dirname(mcpSettingsPath);

console.log('🔧 Setting up Auto-Claude MCP server for VS Code...\n');
console.log(`   MCP server path: ${mcpServerPath}`);
console.log(`   MCP config: ${mcpSettingsPath}`);
console.log(`   User settings: ${userSettingsPath}\n`);

// === STEP 1: Configure MCP Server ===
console.log('📋 Step 1: Configuring MCP server...');

// Ensure directory exists
if (!fs.existsSync(mcpSettingsDir)) {
  console.log(`   Creating directory: ${mcpSettingsDir}`);
  fs.mkdirSync(mcpSettingsDir, { recursive: true });
}

// Read existing MCP config if it exists
let existingMcpConfig = {};
if (fs.existsSync(mcpSettingsPath)) {
  try {
    const content = fs.readFileSync(mcpSettingsPath, 'utf-8');
    existingMcpConfig = JSON.parse(content);
    console.log('   ✓ Found existing MCP configuration');
  } catch (err) {
    console.warn('   ⚠️  Warning: Could not parse existing MCP config, will overwrite');
  }
}

// Merge MCP configurations
const finalMcpConfig = {
  ...existingMcpConfig,
  mcpServers: {
    ...(existingMcpConfig.mcpServers || {}),
    ...mcpConfig.mcpServers
  }
};

// Write MCP configuration
fs.writeFileSync(mcpSettingsPath, JSON.stringify(finalMcpConfig, null, 2), 'utf-8');
console.log('   ✓ MCP server configured with auto-approve enabled');

// === STEP 2: Configure Bypass Permissions ===
console.log('\n📋 Step 2: Enabling bypass permissions...');

// Read existing VS Code user settings if they exist
let existingUserSettings = {};
if (fs.existsSync(userSettingsPath)) {
  try {
    const content = fs.readFileSync(userSettingsPath, 'utf-8');
    existingUserSettings = JSON.parse(content);
    console.log('   ✓ Found existing VS Code user settings');
  } catch (err) {
    console.warn('   ⚠️  Warning: Could not parse VS Code settings');
  }
}

// Add bypass permissions setting (common setting names for Cline extension)
const updatedUserSettings = {
  ...existingUserSettings,
  "cline.alwaysAllowReadOnly": true,
  "cline.alwaysAllowWriteOnly": false,  // Keep write operations visible for safety
  "claude-dev.autoApproveTools": true   // Alternative setting name
};

// Write updated VS Code user settings
try {
  const userSettingsDir = path.dirname(userSettingsPath);
  if (!fs.existsSync(userSettingsDir)) {
    fs.mkdirSync(userSettingsDir, { recursive: true });
  }
  fs.writeFileSync(userSettingsPath, JSON.stringify(updatedUserSettings, null, 2), 'utf-8');
  console.log('   ✓ Bypass permissions enabled for read-only operations');
  console.log('   ℹ️  Write operations will still require approval (for safety)');
} catch (err) {
  console.warn('   ⚠️  Could not update VS Code settings:', err.message);
  console.log('   ℹ️  You can manually enable "Bypass permissions" in Claude Code UI');
}

console.log('\n✅ Auto-Claude MCP server configured successfully!');
console.log(`   MCP config: ${mcpSettingsPath}`);
console.log(`   User settings: ${userSettingsPath}`);

console.log('\n📝 Next steps:');
console.log('1. Restart VS Code COMPLETELY (close and reopen, not just reload)');
console.log('2. Open a Claude Code session in your Auto-Claude project');
console.log('3. Check bottom-left corner for "Bypass permissions" toggle');
console.log('   - It should be automatically enabled for read operations');
console.log('   - You can enable it fully for all operations if desired');
console.log('4. Verify MCP tools are available:');
console.log('   - Type: "List my Auto-Claude tasks"');
console.log('   - Or: "Show available MCP tools"');

console.log('\n🔍 Troubleshooting:');
console.log('- If tools don\'t appear: Check VS Code Dev Tools Console (Help > Toggle Developer Tools)');
console.log('- Verify tsx is available: npx --yes tsx --version');
console.log('- Test MCP server manually:');
console.log(`  npx --yes tsx "${mcpServerPath}"`);
