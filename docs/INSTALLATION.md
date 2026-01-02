# Installation Guide

## Prerequisites

Before installing WLED Effects, ensure you have:

- ✅ **Home Assistant** 2024.1.0 or newer
- ✅ **HACS** (Home Assistant Community Store) installed
- ✅ **WLED Integration** installed and configured
- ✅ **WLED Device** with firmware 0.14.0 or newer
- ✅ **Python** 3.11 or newer (usually comes with Home Assistant)

## Installation Methods

### Method 1: HACS Installation (Recommended)

#### Step 1: Add Custom Repository

1. Open Home Assistant
2. Go to **HACS** → **Integrations**
3. Click the **⋮** (three dots menu) in the top right
4. Select **Custom repositories**
5. Add the repository:
   - **Repository URL**: `https://github.com/tamaygz/hacs-wledext-effects`
   - **Category**: `Integration`
6. Click **Add**

#### Step 2: Install the Integration

1. In HACS, click **+ Explore & Download Repositories**
2. Search for **"WLED Effects"**
3. Click on **WLED Effects**
4. Click **Download**
5. Select the latest version
6. Click **Download** again to confirm

#### Step 3: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Click **Restart** and wait for Home Assistant to come back online

#### Step 4: Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"WLED Effects"**
4. Click on **WLED Effects**

#### Step 5: Configure Your First Effect

1. Select your **WLED device** from the dropdown
2. Choose an **effect type** (start with "Rainbow Wave" for testing)
3. Configure effect parameters (or use defaults)
4. Click **Submit**

✅ Your first effect is now configured! Continue to [Quick Start Guide](QUICK_START.md) to learn how to use it.

---

### Method 2: Manual Installation

#### Step 1: Download the Integration

Download the latest release from GitHub:
```
https://github.com/tamaygz/hacs-wledext-effects/releases/latest
```

#### Step 2: Extract Files

1. Extract the downloaded ZIP file
2. Copy the `custom_components/wled_effects` folder

#### Step 3: Install to Home Assistant

1. Navigate to your Home Assistant configuration directory (where `configuration.yaml` is located)
2. If a `custom_components` folder doesn't exist, create it
3. Paste the `wled_effects` folder inside `custom_components`:

```
<config_directory>/
├── configuration.yaml
└── custom_components/
    └── wled_effects/
        ├── __init__.py
        ├── manifest.json
        ├── ...
```

#### Step 4: Restart Home Assistant

Restart Home Assistant to load the new integration.

#### Step 5: Add the Integration

Follow **Step 4** from the HACS installation method above.

---

## Verifying Installation

After installation, verify everything is working:

### 1. Check Integration Status

1. Go to **Settings** → **Devices & Services**
2. Look for **WLED Effects** in the integrations list
3. Status should show as "Configured" or "OK"

### 2. Check Entity Creation

Each effect creates multiple entities:

- `switch.wled_effects_<effect_name>` - Effect on/off
- `number.wled_effects_<effect_name>_brightness` - Brightness control
- `number.wled_effects_<effect_name>_speed` - Speed control
- `select.wled_effects_<effect_name>_mode` - Effect mode
- `sensor.wled_effects_<effect_name>_status` - Effect status
- `sensor.wled_effects_<effect_name>_stats` - Performance metrics
- `button.wled_effects_<effect_name>_restart` - Restart effect

### 3. Test Your Effect

1. Go to **Developer Tools** → **Services**
2. Call the `wled_effects.start_effect` service:

```yaml
service: wled_effects.start_effect
target:
  entity_id: switch.wled_effects_rainbow_wave
```

3. Your WLED strip should show the effect!

---

## Troubleshooting Installation

### Integration Not Appearing

**Problem**: WLED Effects doesn't appear in the "Add Integration" list

**Solutions**:
- Ensure you've restarted Home Assistant after installation
- Check that files are in the correct directory: `<config>/custom_components/wled_effects/`
- Check Home Assistant logs for errors: **Settings** → **System** → **Logs**
- Verify `manifest.json` exists and is valid JSON

### WLED Device Not Found

**Problem**: Can't select WLED device during setup

**Solutions**:
- Ensure the WLED integration is installed and configured first
- Verify your WLED device is online and accessible
- Check that your WLED device firmware is 0.14.0 or newer
- Try adding the WLED device manually via its IP address

### Configuration Entry Fails

**Problem**: Integration setup fails with error message

**Solutions**:
- Check Home Assistant logs for detailed error messages
- Verify network connectivity to WLED device
- Ensure WLED device is not in use by another service
- Try restarting both Home Assistant and the WLED device

### Entities Not Created

**Problem**: Effect is configured but entities don't appear

**Solutions**:
- Restart Home Assistant completely (not just reload)
- Check **Settings** → **Devices & Services** → **Entities** for hidden entities
- Review Home Assistant logs for entity registration errors
- Verify the effect type is valid and supported

---

## Updating

### Via HACS

1. Go to **HACS** → **Integrations**
2. Find **WLED Effects**
3. If an update is available, click **Update**
4. Restart Home Assistant

### Manual Update

1. Download the latest release
2. Replace the contents of `custom_components/wled_effects/` with the new files
3. Restart Home Assistant

**Note**: Configuration entries and entity states are preserved during updates.

---

## Uninstalling

### Step 1: Remove Configuration Entries

1. Go to **Settings** → **Devices & Services**
2. Find **WLED Effects**
3. Click **⋮** (three dots) → **Delete**
4. Confirm deletion for each effect configuration

### Step 2: Remove Integration Files

**Via HACS**:
1. Go to **HACS** → **Integrations**
2. Find **WLED Effects**
3. Click **⋮** → **Remove**
4. Restart Home Assistant

**Manual**:
1. Delete the `custom_components/wled_effects/` folder
2. Restart Home Assistant

---

## Next Steps

✅ Installation complete! Now you're ready to:

- **[Quick Start Guide](QUICK_START.md)** - Create your first effect in 5 minutes
- **[Effects Reference](EFFECTS_REFERENCE.md)** - Explore all available effects
- **[Context-Aware Features](CONTEXT_AWARE_FEATURES.md)** - Advanced capabilities

## Support

Need help? Check out:

- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- **[GitHub Issues](https://github.com/tamaygz/hacs-wledext-effects/issues)** - Report bugs
- **[GitHub Discussions](https://github.com/tamaygz/hacs-wledext-effects/discussions)** - Ask questions

---

**Last Updated**: January 2026  
**Version**: 1.0.0
