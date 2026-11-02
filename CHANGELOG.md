# Changelog

Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.
The version is set in `blendkit_ucupaint/blender_manifest.toml` (`python build.py --bump patch|minor|major`).

## 1.3.0
- New option "Textures" (default "Seamless (box projection)"): while baking, the material's textures are projected
  onto the object from 6 sides in object space, like BlendKit's automap (scale from the material's
  `texture_size_meters`), then baked into the object's own UV map. No more texture breaks into squares at UV island
  edges. "Object's UV map" keeps the previous behaviour.

## 1.2.2
- BlendKit no longer adds its "automap" UV map (cube projection) to objects whose slot holds Ucupaint: the layer
  is baked onto the object's own UVs, and the extra active UV map no longer redirects the Ucupaint layers.
- If an object already has an "automap" UV map, baking uses the object's own UV map instead.

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
