# Development

## Source layout

- `DropletForge/DropletForge.pyp`: Cinema 4D command registration and panel entry point.
- `DropletForge/Droplet_Forge_C4D.py`: controls, material creation, and dialog actions.
- `DropletForge/droplet_forge_nodes.py`: native Scene Nodes construction and object hierarchy.
- `DropletForge/forge_preferences.py`: per-user preferences, localization, and Config dialog.
- `DropletForge/res/`: SVG and transparent PNG icons.

## Command identifier

The command currently uses development ID `1000001`, defined as `PLUGIN_ID` in `DropletForge.pyp`. A different plugin using that ID will prevent registration. Obtain a unique identifier through Maxon's Plugin Cafe and update it before distributing a conflict-free production build. This repository does not claim that the development identifier is exclusive to DropletForge.

## Build a distribution

Create a ZIP containing exactly the `DropletForge` directory and its contents. Preserve the folder name and include the license, notice, preferences module, and `res` directory. Exclude Python caches and local user preferences. Install the extracted folder in Cinema 4D's plugin path and restart the application.

## Validation

Native integration checks were executed inside Cinema 4D 2026.4.0 on Windows. They covered four-layer polygon output, per-layer enable/disable, global limits, selection masks and persistent links, material assignment, Standard/Octane material creation, undo/redo, preference persistence, language changes, and updates of older three-layer hierarchies.

The Octane Object tag policy and direct group material assignment were checked with both engine preferences. Compatibility with other Cinema 4D releases, macOS, or different Octane builds remains unverified.

## Release checklist

1. Confirm version strings, documentation, and the plugin command ID.
2. Parse all Python source files and inspect the ZIP structure.
3. Verify the ZIP contains the same source and icons as the plugin directory.
4. Exercise both language options and engine modes in Cinema 4D.
5. Publish matching source and downloadable ZIP with English release notes.

## Contributing

Open an issue with the Cinema 4D version, operating system, selected material engine, reproduction steps, and any relevant console traceback. Use minimal scenes and omit private assets. Keep documentation and commit descriptions in English. UI translations may include English and Brazilian Portuguese.
