#!/bin/bash
set -xe

# Create config structure
mkdir -p /config/custom_components
mkdir -p /config/.storage
mkdir -p /config/test

# Symlink integration
ln -sf /workspaces/ha_lighting_phase/custom_components/lighting_phase /config/custom_components/lighting_phase

# Copy config files
cp /workspaces/ha_lighting_phase/.devcontainer/config/configuration.yaml /config/configuration.yaml

# Restore dashboard
cp /workspaces/ha_lighting_phase/.devcontainer/config/lovelace_dashboards /config/.storage/lovelace_dashboards
cp /workspaces/ha_lighting_phase/.devcontainer/config/lovelace.dashboard_lighting_phase /config/.storage/lovelace.dashboard_lighting_phase

pip install homeassistant

### Hass run command
alias hass='hass -c /config'

### Enable stopping startup until debugger is started
export HA_DEBUG=true

ln -sf /usr/share/zoneinfo/America/New_York /etc/localtime
echo "America/New_York" > /etc/timezone

# Install git hooks
#ln -sf /workspaces/ha_lighting_phase/.devcontainer/scripts/pre-commit \
#       /workspaces/ha_lighting_phase/.git/hooks/pre-commit
#chmod +x /workspaces/ha_lighting_phase/.devcontainer/scripts/pre-commit
#git config --global --add safe.directory /workspaces/ha_lighting_phase
#echo "✓ Git hooks installed"

