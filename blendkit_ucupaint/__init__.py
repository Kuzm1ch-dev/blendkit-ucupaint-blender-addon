# SPDX-License-Identifier: GPL-3.0-or-later
"""BlendKit → Ucupaint: put a BlendKit material into Ucupaint as a layer instead of replacing the material.

Ucupaint's "Add Layer" menu ("+" under the layer list) gets two items:
  * "From BlendKit"   — opens BlendKit's material asset bar in the 3D Viewport. The material you click
                        (or drag onto the object) is downloaded, baked to the object's UVs and added as a layer.
  * "File Material…"  — the same for any material already in the .blend file.

The add-on wraps BlendKit's material assignment: when BlendKit is about to put a material into a slot that holds
an Ucupaint material, the slot is left alone and the material becomes a layer instead (can be switched off in the
add-on preferences).

Bake mode bakes Base Color, Roughness, Metallic, Normal (and Height, if the material has displacement) exactly as the
material looks on the object (mixing, noise, mapping). "Images as is" takes the material's image files without
baking (tiles, but procedural parts and mixing are lost).
"""

import os
import sys
import time

import bpy
from bpy.app.translations import pgettext_iface as iface_

try:
    from bpy.app.translations import pgettext_rpt as rpt_
except ImportError:  # Blender < 4.0
    from bpy.app.translations import pgettext_tip as rpt_

from . import translations

LOG = "[BlendKit → Ucupaint]"
_enum_cache = []  # EnumProperty item strings must be kept alive, or Blender shows garbage


# ---------------------------------------------------------------------------------
#  Ucupaint helpers
# ---------------------------------------------------------------------------------

def yp_node(mat):
    """The Ucupaint group node of a material, or None."""
    if mat is None or not mat.use_nodes or mat.node_tree is None:
        return None
    for n in mat.node_tree.nodes:
        t = getattr(n, "node_tree", None) if n.type == 'GROUP' else None
        if t is not None and getattr(t, "yp", None) is not None and t.yp.is_ypaint_node:
            return n
    return None


def is_blendkit(mat):
    return mat is not None and "blenderkit" in mat.keys()


def find_target(ob):
    """(slot index, Ucupaint material) of an object: the active slot if it has Ucupaint, otherwise the first such slot."""
    if ob is None or ob.type != 'MESH':
        return None, None
    order = [ob.active_material_index] + [i for i in range(len(ob.material_slots)) if i != ob.active_material_index]
    for i in order:
        if i < len(ob.material_slots) and yp_node(ob.material_slots[i].material):
            return i, ob.material_slots[i].material
    return None, None


# ---------------------------------------------------------------------------------
#  Preferences
# ---------------------------------------------------------------------------------

def material_items(self, ctx):
    global _enum_cache
    mats = [m for m in bpy.data.materials if not m.name.startswith("__") and yp_node(m) is None and m.use_nodes]
    mats.sort(key=lambda m: (not is_blendkit(m), m.name.lower()))
    _enum_cache = [(m.name, ("★ " if is_blendkit(m) else "") + m.name,
                    iface_("From BlendKit") if is_blendkit(m) else iface_("Material in this file")) for m in mats]
    return _enum_cache or [("", iface_("— no materials —"), "")]


MODE_ITEMS = [
    ('BAKE', "Bake to object",
     "Bake the material to the object's UVs: looks exactly like the material on the object (mixing, noise, mapping), no tiling"),
    ('DIRECT', "Images as is",
     "Use the material's image files without baking: tiles, but procedural parts and mixing are lost"),
]
PROJ_ITEMS = [
    ('BOX', "Seamless (box projection)",
     "Project the material's textures onto the object from 6 sides, like BlendKit's automap: no seams between UV "
     "islands and the same texture scale everywhere. Baked into the object's own UV map"),
    ('UV', "Object's UV map",
     "Use the material's own mapping on the object's UV map: textures can break at UV seams and island edges"),
]
SIZE_ITEMS = [('512', "512", ""), ('1024', "1024", ""), ('2048', "2048", ""), ('4096', "4096", "")]


class BK2UCP_Prefs(bpy.types.AddonPreferences):
    bl_idname = __package__

    mode: bpy.props.EnumProperty(name="Method", default='BAKE', items=MODE_ITEMS)
    size: bpy.props.EnumProperty(name="Size", default='1024', items=SIZE_ITEMS)
    projection: bpy.props.EnumProperty(name="Textures", default='BOX', items=PROJ_ITEMS)
    folder: bpy.props.StringProperty(name="Folder", subtype='DIR_PATH', default="//textures/blendkit/",
                                     options={'PATH_SUPPORTS_BLEND_RELATIVE'},
                                     description="Where baked textures are saved (// means next to the .blend file)")
    auto: bpy.props.BoolProperty(name="BlendKit material on an Ucupaint object becomes a layer", default=True,
                                 description="Clicking or dragging a BlendKit material onto a slot with Ucupaint "
                                             "adds a layer instead of replacing the material")

    def draw(self, ctx):
        l = self.layout
        l.prop(self, "mode")
        l.prop(self, "size")
        l.prop(self, "projection")
        l.prop(self, "folder")
        l.prop(self, "auto")
        if _ucupaint_menu() is None:
            l.label(text="Ucupaint is not enabled", icon='ERROR')
        if _bk_module() is None:
            l.label(text="BlendKit is not enabled", icon='ERROR')


def prefs():
    return bpy.context.preferences.addons[__package__].preferences


# ---------------------------------------------------------------------------------
#  Baking a material to maps on the object's UVs
# ---------------------------------------------------------------------------------

def texture_size_meters(mat):
    """How many meters one texture repeat covers, as BlendKit stores it for the material (default 1)."""
    try:
        v = float(mat.blenderkit.texture_size_meters)
    except Exception:  # noqa: BLE001
        v = float((mat.get("blenderkit") or {}).get("texture_size_meters", 1.0) or 1.0)
    return v if v > 0 else 1.0


def project_box(nt, ob, src):
    """In a (temporary) material: feed every UV-driven texture with object coordinates and box projection, the way
    BlendKit's automap maps a material (UV = size in meters / texture_size_meters). No seams between UV islands."""
    k = sum(ob.scale) / 3.0 / texture_size_meters(src)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mul = nt.nodes.new('ShaderNodeVectorMath')
    mul.operation = 'SCALE'
    mul.inputs['Scale'].default_value = k
    nt.links.new(tc.outputs['Object'], mul.inputs[0])
    proj = mul.outputs['Vector']
    for n in list(nt.nodes):
        if n is tc:
            continue
        if n.type == 'TEX_COORD':
            for l in list(n.outputs['UV'].links):
                nt.links.new(proj, l.to_socket)
        elif n.type == 'UVMAP':
            for l in list(n.outputs['UV'].links):
                nt.links.new(proj, l.to_socket)
        elif n.type == 'TEX_IMAGE':
            n.projection = 'BOX'
            n.projection_blend = 0.25
            if not n.inputs['Vector'].is_linked:  # an unlinked image vector means "the active UV map"
                nt.links.new(proj, n.inputs['Vector'])


def bake_material(ctx, ob, src, size, folder, uv=None, projection='UV'):
    """Bake src on the UVs of ob (uv: UV map name, default active): color, roughness, metallic, normal (+ height). Returns file names."""
    scene = ctx.scene
    prev = (scene.render.engine, scene.cycles.samples, scene.cycles.device)
    slots = [(s, s.link, s.material) for s in ob.material_slots]
    hidden, sel = ob.hide_get(), [o for o in ctx.view_layer.objects if o.select_get()]
    # baking needs an object enabled for rendering: temporarily enable it and the hidden collections it is in
    vis = [(ob, ob.hide_render, ob.hide_viewport)] + [(c, c.hide_render, c.hide_viewport) for c in bpy.data.collections
                                                      if (c.hide_render or c.hide_viewport) and ob.name in c.all_objects]
    active = ctx.view_layer.objects.active
    uvs = ob.data.uv_layers
    prev_uv = uvs.active.name if uvs.active else None
    tmp = src.copy()
    tmp.name = "__bk2ucp_bake"
    imgs, files = [], []
    base = bpy.path.clean_name(src.name)
    try:
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 1
        scene.cycles.device = 'CPU'
        for d, _r, _v in vis:
            d.hide_render = False
            d.hide_viewport = False
        ob.hide_set(False)
        if uv and uv in uvs:
            uvs.active = uvs[uv]  # Cycles bakes into the active UV map
        for s in ob.material_slots:  # every face gets the temp material (other slots would have no image to bake into)
            s.link = 'OBJECT'
            s.material = tmp
        for o in ctx.view_layer.objects:
            o.select_set(False)
        ob.select_set(True)
        ctx.view_layer.objects.active = ob
        nt = tmp.node_tree
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None) \
            or next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if out is None or bsdf is None:
            raise RuntimeError(rpt_("the material has no Principled BSDF, nothing to bake"))
        if projection == 'BOX':
            project_box(nt, ob, src)
        disp = next((l.from_node for l in out.inputs['Displacement'].links), None)
        height = disp.inputs.get('Height') if disp is not None and disp.type == 'DISPLACEMENT' else None
        emis = nt.nodes.new('ShaderNodeEmission')
        tex = nt.nodes.new('ShaderNodeTexImage')
        chans = [("Base Color", 'sRGB', "color"), ("Roughness", 'Non-Color', "roughness"),
                 ("Metallic", 'Non-Color', "metallic"), ("Normal", 'Non-Color', "normal")]
        if height is not None and height.is_linked:
            chans.append(("Height", 'Non-Color', "height"))
        for ch, cs, suffix in chans:
            img = bpy.data.images.new(f"__bk2ucp_{suffix}", size, size)
            img.colorspace_settings.name = cs
            imgs.append(img)
            tex.image = img
            for n in nt.nodes:
                n.select = False
            tex.select = True
            nt.nodes.active = tex
            for l in list(out.inputs['Surface'].links):
                nt.links.remove(l)
            if ch == "Normal":
                nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
                bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_clear=True, margin=8)
            else:
                sock = height if ch == "Height" else bsdf.inputs[ch]
                for l in list(emis.inputs['Color'].links):
                    nt.links.remove(l)
                if sock.is_linked:
                    nt.links.new(sock.links[0].from_socket, emis.inputs['Color'])
                else:
                    v = sock.default_value
                    emis.inputs['Color'].default_value = tuple(v) if ch == "Base Color" else (v, v, v, 1.0)
                nt.links.new(emis.outputs['Emission'], out.inputs['Surface'])
                bpy.ops.object.bake(type='EMIT', use_clear=True, margin=8)
            fn = f"{base}_{ob.name}_{suffix}.png".replace(" ", "_")
            img.filepath_raw = os.path.join(folder, fn)
            img.file_format = 'PNG'
            img.save()
            files.append(fn)
        return files
    finally:
        for s, link, m in slots:
            s.link = link
            s.material = m
        for img in imgs:
            bpy.data.images.remove(img)
        bpy.data.materials.remove(tmp)
        scene.render.engine, scene.cycles.samples, scene.cycles.device = prev
        for d, r, v in vis:
            d.hide_render, d.hide_viewport = r, v
        if prev_uv and prev_uv in uvs:
            uvs.active = uvs[prev_uv]
        ob.hide_set(hidden)
        for o in ctx.view_layer.objects:
            o.select_set(o in sel)
        ctx.view_layer.objects.active = active


AUTOMAP_UV = "automap"  # the cube-projection UV map BlendKit creates when "automap" is on in its preferences


def pick_uv(ob):
    """The object's own UV map: the active one, but never BlendKit's "automap" if the object has another."""
    uvs = ob.data.uv_layers
    if not len(uvs):
        return ""
    names = [u.name for u in uvs]
    own = [n for n in names if n != AUTOMAP_UV]
    act = uvs.active.name if uvs.active else names[0]
    if act != AUTOMAP_UV:
        return act
    render = next((u.name for u in uvs if u.active_render and u.name != AUTOMAP_UV), None)
    return render or (own[0] if own else act)


def add_as_layer(ctx, ob, slot_index, ucp_mat, src, st=None):
    """Add src as a layer to the Ucupaint of ucp_mat (slot slot_index of ob). Returns the layer name."""
    st = st or prefs()
    node = yp_node(ucp_mat)
    yp = node.node_tree.yp
    ob.active_material_index = slot_index
    ucp_mat.node_tree.nodes.active = node
    uv = pick_uv(ob)
    if not uv:
        raise RuntimeError(rpt_("the object has no UV map"))
    n_before = len(yp.layers)
    with ctx.temp_override(object=ob, active_object=ob):
        if st.mode == 'BAKE':
            folder = bpy.path.abspath(st.folder)
            os.makedirs(folder, exist_ok=True)
            files = bake_material(ctx, ob, src, int(st.size), folder, uv, st.projection)
            ob.active_material_index = slot_index
            ucp_mat.node_tree.nodes.active = node
            bpy.ops.wm.y_open_images_as_single_layer(directory=folder if folder.endswith(("/", "\\")) else folder + os.sep,
                                                      files=[{"name": f} for f in files], texcoord_type='UV', uv_map=uv,
                                                      relative=True, normal_height_priority='BOTH')
        else:
            bpy.ops.wm.y_open_images_from_material_as_single_layer(mat_name=src.name, read_method='READ_NODE',
                                                                    texcoord_type='UV', uv_map=uv, normal_height_priority='BOTH')
    if len(yp.layers) <= n_before:
        raise RuntimeError(rpt_("Ucupaint did not create a layer"))
    lay = yp.layers[yp.active_layer_index]
    try:
        lay.name = src.name
    except Exception:  # noqa: BLE001
        pass
    return lay.name


# ---------------------------------------------------------------------------------
#  Operators (items of Ucupaint's "Add Layer" menu)
# ---------------------------------------------------------------------------------

def _settings_ui(layout, p):
    layout.prop(p, "mode", text="")
    if p.mode == 'BAKE':
        layout.prop(p, "size")
        layout.prop(p, "projection", text="")
        layout.prop(p, "folder", text="")


class BK2UCP_OT_from_file(bpy.types.Operator):
    bl_idname = "bk2ucp.add_layer"
    bl_label = "Material as Layer"
    bl_description = "A material from this file (downloaded from BlendKit or any other) as a layer in the active object's Ucupaint"
    bl_options = {'REGISTER', 'UNDO'}

    source: bpy.props.EnumProperty(name="Material", items=material_items)

    @classmethod
    def poll(cls, ctx):
        return ctx.mode == 'OBJECT' and find_target(ctx.active_object)[0] is not None

    def invoke(self, ctx, event):
        return ctx.window_manager.invoke_props_dialog(self, width=320)

    def draw(self, ctx):
        l = self.layout
        l.prop(self, "source", text="")
        _settings_ui(l, prefs())

    def execute(self, ctx):
        src = bpy.data.materials.get(self.source)
        if src is None:
            self.report({'ERROR'}, rpt_("No material selected"))
            return {'CANCELLED'}
        ob = ctx.active_object
        i, ucp = find_target(ob)
        try:
            name = add_as_layer(ctx, ob, i, ucp, src)
        except Exception as e:  # noqa: BLE001
            self.report({'ERROR'}, rpt_("Failed: {}").format(e))
            return {'CANCELLED'}
        self.report({'INFO'}, rpt_("Layer “{}” added to {}").format(name, ucp.name))
        return {'FINISHED'}


# ---------------------------------------------------------------------------------
#  BlendKit hook: when BlendKit assigns a downloaded material to a slot with Ucupaint (clicking a material in the
#  asset bar, dragging it onto an object or into the node editor), the material is not assigned but baked and
#  added as a layer.
# ---------------------------------------------------------------------------------

_orig_assign = None
_orig_automap = None
_wait = {}  # "From BlendKit" was used: object and Ucupaint slot to target even if another slot is active
WAIT_SECONDS = 15 * 60
_queue = []


def _bk_module():
    """BlendKit's download module (whatever repository BlendKit is installed from)."""
    return next((m for k, m in list(sys.modules.items())
                 if k.endswith("blenderkit.download") and hasattr(m, "assign_material")), None)


def _slot_index(ob, target_slot):
    mp = ob.get("material_mapping")
    if mp:
        info = mp.get(str(target_slot))
        if info and info.get("type") == "SLOT":
            return info.get("index", target_slot)
        if info:
            return None  # a Set Material node in geometry nodes, not our case
    return target_slot


def _ucupaint_target(ob, target_slot):
    """(slot, Ucupaint material) where the material BlendKit assigns to ob should go as a layer, or (None, None)."""
    if ob is None or ob.type != 'MESH':
        return None, None
    i = _slot_index(ob, target_slot)
    if i is not None and 0 <= i < len(ob.material_slots) and yp_node(ob.material_slots[i].material):
        return i, ob.material_slots[i].material
    if _wait and _wait.get("ob") == ob.name and time.time() - _wait["t"] < WAIT_SECONDS:
        ucp = bpy.data.materials.get(_wait["ucp"])
        j = _wait["slot"]
        if ucp is not None and j < len(ob.material_slots) and ob.material_slots[j].material is ucp:
            return j, ucp
    return None, None


def _assign_hook(object, material, target_slot, *args, **kwargs):  # noqa: A002 (same signature as BlendKit)
    try:
        on = prefs().auto or bool(_wait)
        i, ucp = _ucupaint_target(object, target_slot) if on else (None, None)
    except Exception as e:  # noqa: BLE001
        print(LOG, e)
        i = ucp = None
    if ucp is None:
        return _orig_assign(object, material, target_slot, *args, **kwargs)
    _wait.clear()
    _queue.append((object.name, i, ucp.name, material.name))
    if not bpy.app.timers.is_registered(_process):
        bpy.app.timers.register(_process, first_interval=0.1)  # bake outside of BlendKit's downloader
    return None


_assign_hook._bk2ucp = True


def _automap_hook(target_object=None, target_slot=None, *args, **kwargs):
    """BlendKit adds an "automap" UV (cube projection) before downloading a material. Not for Ucupaint slots:
    the layer is baked onto the object's own UVs, and a new active UV map would break the other layers."""
    try:
        ob = bpy.data.objects.get(target_object) if target_object else None
        on = prefs().auto or bool(_wait)
        if on and ob is not None and _ucupaint_target(ob, target_slot if target_slot is not None else ob.active_material_index)[1]:
            return None
    except Exception as e:  # noqa: BLE001
        print(LOG, e)
    return _orig_automap(target_object, target_slot, *args, **kwargs)


_automap_hook._bk2ucp = True


def _process():
    while _queue:
        obn, i, ucpn, srcn = _queue.pop(0)
        ob, ucp, src = bpy.data.objects.get(obn), bpy.data.materials.get(ucpn), bpy.data.materials.get(srcn)
        if ob is None or ucp is None or src is None:
            continue
        try:
            name = add_as_layer(bpy.context, ob, i, ucp, src)
            msg = rpt_("“{}” added as a layer to {}").format(name, ucp.name)
        except Exception as e:  # noqa: BLE001
            msg = rpt_("Failed: {}").format(e)
        print(LOG, f"{ob.name}: {msg}")
        _report(msg)
    return None


def _report(msg):
    """Show a message at the bottom of the 3D Viewport, the way BlendKit does."""
    m = _bk_module()
    pkg = m.__name__.rsplit(".", 1)[0] if m else None
    reports = sys.modules.get(f"{pkg}.reports") if pkg else None
    if reports is not None and hasattr(reports, "add_report"):
        try:
            reports.add_report(f"Ucupaint: {msg}")
        except Exception:  # noqa: BLE001
            pass


def _keep_alive():
    """Install the hook and the menu item; retried, because BlendKit/Ucupaint may be enabled (or reloaded) later."""
    global _orig_assign, _orig_automap
    m = _bk_module()
    if m is not None and not getattr(m.assign_material, "_bk2ucp", False):
        _orig_assign = m.assign_material
        m.assign_material = _assign_hook
    u = _bk_utils()
    if u is not None and not getattr(u.automap, "_bk2ucp", False):
        _orig_automap = u.automap
        u.automap = _automap_hook
    menu = _ucupaint_menu()
    if menu is not None and menu_draw not in getattr(menu.draw, "_draw_funcs", []):
        menu.append(menu_draw)
    return 2.0


def _bk_utils():
    m = _bk_module()
    pkg = m.__name__.rsplit(".", 1)[0] if m else None
    u = sys.modules.get(f"{pkg}.utils") if pkg else None
    return u if u is not None and hasattr(u, "automap") else None


def _hook_remove():
    m = _bk_module()
    if m is not None and getattr(m.assign_material, "_bk2ucp", False) and _orig_assign is not None:
        m.assign_material = _orig_assign
    u = _bk_utils()
    if u is not None and getattr(u.automap, "_bk2ucp", False) and _orig_automap is not None:
        u.automap = _orig_automap


class BK2UCP_OT_search(bpy.types.Operator):
    bl_idname = "bk2ucp.search_blendkit"
    bl_label = "From BlendKit"
    bl_description = "Open BlendKit's material bar: the material you click becomes a layer"

    @classmethod
    def poll(cls, ctx):
        return (ctx.mode == 'OBJECT' and find_target(ctx.active_object)[0] is not None
                and hasattr(ctx.window_manager, "blenderkitUI"))

    def execute(self, ctx):
        ob = ctx.active_object
        i, ucp = find_target(ob)
        win = ctx.window
        area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), None)
        if area is None:
            self.report({'ERROR'}, rpt_("A 3D Viewport is needed: BlendKit shows its material bar there"))
            return {'CANCELLED'}
        _wait.clear()
        _wait.update(ob=ob.name, slot=i, ucp=ucp.name, t=time.time())
        region = next(r for r in area.regions if r.type == 'WINDOW')
        ui = ctx.window_manager.blenderkitUI
        with ctx.temp_override(window=win, area=area, region=region):
            if ui.asset_type != 'MATERIAL':
                ui.asset_type = 'MATERIAL'
            if not ui.assetbar_on:
                bpy.ops.view3d.blenderkit_asset_bar_widget('INVOKE_DEFAULT', do_search=True, keep_running=True)
        self.report({'INFO'}, rpt_("Click a material in the BlendKit bar: it becomes a layer"))
        return {'FINISHED'}


def menu_draw(self, ctx):
    l = self.layout
    l.separator()
    l.operator_context = 'EXEC_DEFAULT'
    l.operator("bk2ucp.search_blendkit", text=iface_("From BlendKit"), icon='URL')
    l.operator_context = 'INVOKE_DEFAULT'
    l.operator("bk2ucp.add_layer", text=iface_("File Material…"), icon='MATERIAL')


def _ucupaint_menu():
    return getattr(bpy.types, "NODE_MT_y_new_layer_menu", None)


classes = (BK2UCP_Prefs, BK2UCP_OT_from_file, BK2UCP_OT_search)


def register():
    bpy.app.translations.register(__package__, translations.DATA)
    for c in classes:
        bpy.utils.register_class(c)
    _keep_alive()
    bpy.app.timers.register(_keep_alive, first_interval=2.0, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(_keep_alive):
        bpy.app.timers.unregister(_keep_alive)
    _hook_remove()
    menu = _ucupaint_menu()
    if menu is not None:
        try:
            menu.remove(menu_draw)
        except Exception:  # noqa: BLE001
            pass
    _wait.clear()
    _queue.clear()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.app.translations.unregister(__package__)
