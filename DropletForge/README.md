# DropletForge 1.0

<p align="center"><img src="res/icon_128.png" width="96" alt="DropletForge icon"></p>

**Procedural surface droplets for Cinema 4D 2026, built with native Scene Nodes.**

Create water droplets on an object, restrict their placement with a polygon Selection Tag, and customize four independent layers. DropletForge generates editable Scene Nodes and polygon mesh output inside an Object Manager group, with material support for Cinema 4D Standard and Octane.

## Requirements

- Cinema 4D 2026. Validated on Windows with Cinema 4D 2026.4.0.
- Octane for Cinema 4D is optional and required only for Octane materials and Object tags. Octane Live Viewer compatibility was checked with Octane 2025.4, build 1.7.2.
- Standard mode works without Octane.

**Plugin ID:** this version uses the development command ID `1000001`. Another plugin using that ID will prevent registration. A unique Maxon Plugin Cafe ID is required for conflict-free public deployment. See the developer notes in the repository.

## Installation

1. Extract the download ZIP.
2. Copy the entire `DropletForge` folder into your Cinema 4D plugins directory. Keep its Python files and `res` folder together.
3. Restart Cinema 4D.
4. Open **Extensions > DropletForge**.
5. On first launch, choose **EN** or **PT/BR**. Your choice is saved for subsequent launches.

Install only one copy of the plugin to avoid duplicate command registration. The ZIP includes source code and the GPL license.

## Quick start

1. Select the target object, or drag it into **Object**.
2. Optionally link a polygon **Selection Tag** belonging to that object.
3. Adjust the Large, Medium, Small, and Micro layers.
4. Click **Create / Update**. The first application creates the nodes; later applications update the object's existing droplet group.
5. Choose your material engine in **Config**. Use **+ Drop Oct Tx** or **+ Drop Std Tx** to create **Water Drop** and assign it to the existing group immediately.

If you create a material before generating droplets, it stays linked in the panel and is assigned when you click Create / Update. **Use selected object** loads the selected object or its existing droplet generator. **Demo Scene** creates a separate example scene.

## Four independent layers

| Layer | Default count | Default size | Default detail |
| --- | ---: | ---: | ---: |
| Large | 70 | 3.0 cm | 20 |
| Medium | 400 | 1.35 cm | 12 |
| Small | 1,600 | 0.5 cm | 8 |
| Micro | 3,200 | 0.25 cm | 6 |

Micro starts with twice Small's count and half its size. Each layer has its own **Enabled**, Count, Size, Size variation, Flattening, Offset, and Detail controls. Sizes remain independently editable; changing Small does not automatically change Micro.

Turning Enabled off removes that layer's droplets from the generated output, disables its customization controls, and preserves its values. On an existing generator, toggling Enabled updates the geometry immediately. A new object's nodes are created only after Create / Update.

The general settings provide Seed, Global scale, Count multiplier, and Total limit. The limit is shared by enabled layers. Higher counts and detail increase mesh memory usage. The Size value controls the maximum droplet radius before variation and global scale.

## Restrict droplets with a Selection Tag

Link a polygon Selection Tag from the chosen object and click Create / Update. Droplets are distributed only on the selected polygons, across all enabled layers.

- An empty polygon selection generates no droplets.
- Clearing the field restores the entire surface.
- After changing selected polygons, click Create / Update again.
- Renaming a tag and using tags with identical names are supported.
- Point selections and tags from another object are rejected.

The selection link and generated geometry are saved with the scene and support undo.

## Materials and render engines

Open **Config** to choose the engine used when creating Water Drop. This preference does not convert existing materials or change the scene's render settings.

| Preference | Material shortcut | Water Drop material |
| --- | --- | --- |
| Octane | + Drop Oct Tx | Octane Specular, clear transmission, IOR 1.333 |
| Standard | + Drop Std Tx | Native Cinema 4D material, transparency and refraction, IOR 1.333 |

The shortcut inserts the material into the scene, links it in the panel, and assigns it directly to the droplet group for the linked object. Material creation and assignment support undo/redo together.

DropletForge creates its **Octane Object** tag only when the saved preference is Octane and the Octane plugin is available. Saving Standard in Config removes DropletForge-managed Octane Object tags from groups in the current document. Manually added Octane tags are preserved. Switching back to Octane creates a managed tag where needed, without replacing an existing manual Octane tag.

## Object Manager and Scene Nodes

Each object gets an independent `DropletForge | Object name` group containing four native Nodes Mesh objects, one per layer. Their Scene Nodes output polygon geometry for rendering. Delete the group to remove all of its droplets; undo restores the group.

Double-click a layer's icon to inspect its graph in the Node Editor. The original surface remains a separate object. The graph is saved in the scene and evaluates without the Python backend module.

Older three-layer scenes can be updated. Micro starts at half the saved Small size with a count of zero to preserve the scene's appearance. Increase its count to introduce the additional layer. Updating the hierarchy supports undo. After converting an older graph, Octane Live Viewer may require **Send your scene and Restart new render**.

## Language and preferences

The first-launch language choice and the Config settings are stored per user at:

`<Cinema 4D preferences>/DropletForge/preferences.json`

Config can switch between **EN** and **PT/BR** at any time. Saving changes updates the interface immediately while retaining its values and object, selection, and material links. The language and material-engine choices are restored on later launches.

## Scope and limitations

DropletForge distributes static droplets on a surface. Running-liquid simulation, trails, advanced masks, and UV-based adhesion are not implemented. Compatibility outside the validated Cinema 4D/Octane versions and Windows environment has not been verified. Polygon output uses memory in proportion to the generated droplet count and detail.

## License

DropletForge is licensed under **GNU GPL version 2 or later** (`GPL-2.0-or-later`). See [LICENSE.txt](LICENSE.txt) and [NOTICE.txt](NOTICE.txt). Distributed without warranty.
