# SPDX-License-Identifier: GPL-3.0-or-later
"""UI translations. Blender uses them when Preferences → Interface → Translation is on.

To add a language, add a dict like RU below and register it in DATA under Blender's locale code
(see bpy.app.translations.locales).
"""

RU = {
    # menu / operators
    "From BlendKit": "Из BlendKit",
    "File Material…": "Материал файла…",
    "Material as Layer": "Материал слоем",
    "Open BlendKit's material bar: the material you click becomes a layer":
        "Открыть полосу материалов BlendKit: материал, по которому щёлкнешь, станет слоем",
    "A material from this file (downloaded from BlendKit or any other) as a layer in the active object's Ucupaint":
        "Материал из файла (скачанный из BlendKit или любой) — слоем в Ucupaint активного объекта",
    "Material": "Материал",
    "Material in this file": "Материал файла",
    "— no materials —": "— нет материалов —",
    # preferences
    "Method": "Способ",
    "Size": "Размер",
    "Folder": "Папка",
    "Bake to object": "Запечь на объект",
    "Images as is": "Картинки как есть",
    "Bake the material to the object's UVs: looks exactly like the material on the object (mixing, noise, mapping), no tiling":
        "Запечь материал на UV объекта: точно как выглядит (смешивания, шум, масштаб), без повторения",
    "Use the material's image files without baking: tiles, but procedural parts and mixing are lost":
        "Взять картинки материала без запекания: тайлятся, но процедурные части и смешивания теряются",
    "Where baked textures are saved (// means next to the .blend file)":
        "Куда сохранять запечённые текстуры (// — рядом с .blend)",
    "BlendKit material on an Ucupaint object becomes a layer": "Материал BlendKit на объект с Ucupaint — слоем",
    "Clicking or dragging a BlendKit material onto a slot with Ucupaint adds a layer instead of replacing the material":
        "Щелчок или перетаскивание материала BlendKit на слот с Ucupaint добавляет слой, а не заменяет материал",
    "Ucupaint is not enabled": "Ucupaint не включён",
    "BlendKit is not enabled": "BlendKit не включён",
    # reports
    "No material selected": "Не выбран материал",
    "Failed: {}": "Не получилось: {}",
    "Layer “{}” added to {}": "Слой «{}» добавлен в {}",
    "“{}” added as a layer to {}": "«{}» — слой в {}",
    "A 3D Viewport is needed: BlendKit shows its material bar there":
        "Нужен открытый 3D-вид: там BlendKit показывает полосу материалов",
    "Click a material in the BlendKit bar: it becomes a layer": "Щёлкни материал в полосе BlendKit — он станет слоем",
    "the material has no Principled BSDF, nothing to bake": "в материале нет Principled BSDF — запекать нечего",
    "the object has no UV map": "у объекта нет UV-развёртки",
    "Ucupaint did not create a layer": "Ucupaint не создал слой",
}

# Blender looks strings up by (context, text); labels use "*", operator names use "Operator".
_CONTEXTS = ("*", "Operator")

DATA = {
    locale: {(ctx, en): tr for en, tr in table.items() for ctx in _CONTEXTS}
    for locale, table in {"ru_RU": RU}.items()
}
