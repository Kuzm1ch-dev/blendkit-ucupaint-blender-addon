# BlendKit → Ucupaint

[Русская версия](README.ru.md)

A Blender add-on that puts [BlendKit](https://www.blenderkit.com/) materials into
[Ucupaint](https://github.com/ucupumar/ucupaint) **as layers** instead of replacing your Ucupaint material.

Normally, clicking or dragging a BlendKit material onto an object replaces the object's material, so your
Ucupaint setup is gone from that slot. With this add-on the material is downloaded, baked onto the object's UVs
and added as a new Ucupaint layer, and you keep painting on top of it.

## Requirements

- Blender **4.2** or newer
- [Ucupaint](https://extensions.blender.org/add-ons/ucupaint/) (tested with 3.0)
- [BlendKit](https://extensions.blender.org/add-ons/blenderkit/) (tested with 3.21) for the "From BlendKit" item;
  "File Material…" works without it
- The object needs a UV map and an Ucupaint material in one of its slots

Tested on Blender 5.1.

## Installation

1. Download `blendkit_ucupaint-X.Y.Z.zip` from the [Releases](../../releases/latest) page (Assets) (or build it, see below).
2. In Blender: **Edit → Preferences → Get Extensions**, then the **⌄** menu at the top right → **Install from Disk…**,
   and pick the zip. Dragging the zip into the Blender window also works.
3. Make sure Ucupaint and BlendKit are enabled.

To update, install the newer zip the same way.

## Usage

Select an object with an Ucupaint material and open Ucupaint's layer **+** (Add Layer) menu:

- **From BlendKit** opens BlendKit's material bar in the 3D Viewport. Search in the bar as usual and **click** a
  material: once downloaded it is baked and appears as a layer. Dragging a material onto the object (or into the
  shader editor) does the same.
- **File Material…** adds any material already in the .blend file (downloaded BlendKit materials are marked ★).

A message appears at the bottom of the 3D Viewport when the layer is ready.

### Options

**Edit → Preferences → Add-ons → BlendKit to Ucupaint**:

| Option | What it does |
|---|---|
| Method | **Bake to object**: bakes Base Color, Roughness, Metallic, Normal (and Height, if the material has displacement) exactly as the material looks on the object, including procedural parts and mixing. **Images as is**: uses the material's image files directly; they tile, but procedural parts and mixing are lost. |
| Size | Resolution of baked maps (512–4096). |
| Folder | Where baked PNGs go. `//` means next to the .blend file (default `//textures/blendkit/`). Save the .blend first if you use a relative path. |
| BlendKit material on an Ucupaint object becomes a layer | Switch off to let BlendKit replace materials as usual. |

The UI is in English; with **Preferences → Interface → Translation** set to Russian it is shown in Russian.

## Notes

- Baking uses Cycles on the CPU at 1 sample for a moment; render settings are restored afterwards. Objects
  disabled for rendering are temporarily enabled for the bake.
- Only slots that already hold an Ucupaint material are intercepted. Other objects and slots behave as BlendKit
  normally does.
- The downloaded BlendKit material stays in the file (unassigned) and can be removed with
  **File → Clean Up → Purge Unused Data**.

## Building from source

```
python build.py                 # -> dist/blendkit_ucupaint-<version>.zip
python build.py --bump patch    # 1.2.1 -> 1.2.2 and build (minor / major also work)
python build.py --set 2.0.0     # set an exact version and build
```

Requires Python 3.9+. The version is kept in one place, `blendkit_ucupaint/blender_manifest.toml`. Describe each
release in [CHANGELOG.md](CHANGELOG.md). Blender's own tool builds the same package:
`blender --command extension build --source-dir blendkit_ucupaint --output-dir dist`.

Project layout:

```
blendkit_ucupaint/          the extension (what goes into the zip)
  __init__.py               add-on code
  translations.py           UI translations
  blender_manifest.toml     id, version, Blender version, license
build.py                    zip builder / version bump
CHANGELOG.md
LICENSE                     GPL-3.0-or-later
.github/workflows/release.yml  builds and publishes the zip on tag push
```

## Releasing

Releases are built by GitHub Actions (`.github/workflows/release.yml`):

1. Raise the version: `python build.py --bump patch` (or `minor` / `major`) and describe it in `CHANGELOG.md`
   under `## X.Y.Z`.
2. Commit, then tag and push:
   ```
   git commit -am "Release 1.2.2"
   git tag v1.2.2
   git push && git push --tags
   ```
3. GitHub builds `blendkit_ucupaint-1.2.2.zip` and publishes it on the **Releases** page with the changelog as
   notes. The tag must match the version in `blender_manifest.toml`, otherwise the build fails.

Users download the zip from **Releases → Assets**. The latest one is always at
`https://github.com/<you>/blendkit-ucupaint/releases/latest`.

## License

GPL-3.0-or-later, like Blender, Ucupaint and BlendKit. See [LICENSE](LICENSE).
