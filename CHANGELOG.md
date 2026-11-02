# Changelog

Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.
The version is set in `blendkit_ucupaint/blender_manifest.toml` (`python build.py --bump patch|minor|major`).

## 1.2.1
- Baking works on objects that are disabled for rendering (or sit in a collection disabled for rendering):
  they are enabled for the bake and restored afterwards. Fixes "Object … is not enabled for rendering".

## 1.2.0
- "From BlendKit" opens BlendKit's material bar right away (search in the bar itself), no dialog.
- Clicking a material in the bar, or dragging it onto an object or into the shader editor, adds it as an
  Ucupaint layer instead of replacing the Ucupaint material (BlendKit's material assignment is intercepted).
- Packaged as a Blender extension (Blender 4.2+), English UI with Russian translation.

## 1.1.0
- Menu items moved into Ucupaint's "Add Layer" menu.

## 1.0.0
- First version: bake a material onto the object's UVs and add it as an Ucupaint layer.
