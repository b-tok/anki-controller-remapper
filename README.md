# 8BitDo Zero 2 Controller Remapper for Anki

An Anki addon that allows you to use a 8BitDo Zero 2 controller to control Anki by mapping controller buttons to keyboard keys, including key combinations.

## Installation

1. Copy this entire folder to your Anki addons directory:
   - Windows: `%APPDATA%\Anki2\addons21\`
   - Mac: `~/Library/Application Support/Anki2/addons21/`
   - Linux: `~/.local/share/Anki2/addons21/` or `~/.var/app/net.ankiweb.Anki/data/Anki2/addons21`

2. Restart Anki

### Flatpak Users (Linux)

If you're using the Flatpak version of Anki, additional setup is required:

1. Grant device access to the Flatpak sandbox:
   ```bash
   flatpak override --user --device=all net.ankiweb.Anki
   ```

2. Add your user to the `input` group (requires sudo):
   ```bash
   sudo usermod -a -G input $USER
   ```

3. Apply the group membership (logout and login, or run):
   ```bash
   newgrp input
   ```

4. Restart Anki:
   ```bash
   flatpak run net.ankiweb.Anki
   ```

## Configuration

1. Go to **Tools** > **Controller Remapper Settings**
2. Select a controller button from the dropdown
3. Enter a keyboard key or combination (e.g., `z`, `Ctrl+z`, `Ctrl+Shift+z`)
4. Click "Add Mapping" or "Update Mapping"
5. Close the dialog to save settings

## Default Mappings

| Controller Button | Keyboard Key |
|------------------|--------------|
| A | Space |
| B | Enter/Return |
| X | z |
| Y | x |
| Up/Down/Left/Right | Arrow keys |
| Left Shoulder | Ctrl+Shift+z (Undo Redo) |
| Right Shoulder | Ctrl+z (Undo) |
| Start | Enter/Return |
| Select | Backspace |
| Left/Right Trigger | Ctrl+Shift+z / Ctrl+y |

## Supported Key Combinations

You can use any combination of:
- Letters and numbers (a-z, 0-9)
- Special keys (Space, Enter, Backspace, etc.)
- Modifiers: Ctrl, Shift, Alt

Examples:
- `z` - Press z
- `Ctrl+z` - Undo
- `Ctrl+Shift+z` - Redo
- `Ctrl+y` - Redo
- `Space` - Spacebar
- `Enter` - Enter key
- `Ctrl+Space` - Ctrl+Space

## Troubleshooting

- **Controller not detected**: Make sure your 8BitDo Zero 2 is connected via Bluetooth or USB before starting Anki
- **Flatpak: No joystick device found**: Run `flatpak override --user --device=all net.ankiweb.Anki` and add your user to the `input` group
- **Flatpak: Permission denied**: Ensure your user is in the `input` group: `groups` (should show `input`)
- **Keys not working**: Check the Controller Remapper Settings to verify your mappings and ensure key names are correct (e.g., "space" not "SPACE")
- **Addon not showing**: Restart Anki after installation

## Usage in Anki

Once configured:
- Start/Stop the remapper from the **Tools** menu
- Use your controller to navigate cards, type answers, trigger keyboard shortcuts
- Perfect for studying hands-free with a compact controller
