import bpy
import bmesh
import math


def setup_units():
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = 'MILLIMETERS'


def clear_scene():
    for obj in bpy.data.objects:
        obj.hide_viewport = False
        obj.hide_set(False)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def add_material(obj, name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    obj.data.materials.append(mat)


def profile_to_object(name, profile, y_start, thickness, color):
    """profile: [(x, z), ...] を y=y_start の面として作り、y方向に thickness 押し出す"""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    verts = [bm.verts.new((x, y_start, z)) for (x, z) in profile]
    face = bm.faces.new(verts)
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    ext_verts = [e for e in res['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=ext_verts, vec=(0.0, thickness, 0.0))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()

    add_material(obj, name + "_mat", color)
    return obj


def create_board():
    W, H, R = 32.0, 40.0, 4.0
    THICK = 2.4
    x = W / 2.0
    steps = 16
    pts = []
    pts.append((-x, 0.0))
    pts.append((x, 0.0))
    pts.append((x, H - R))
    # 右上コーナー R (中心 x-R, H-R)
    cx, cz = x - R, H - R
    for i in range(1, steps + 1):
        a = math.radians(90.0 * i / steps)
        pts.append((cx + R * math.cos(a), cz + R * math.sin(a)))
    # 左上コーナー R (中心 -(x-R), H-R)
    cx2, cz2 = -(x - R), H - R
    for i in range(0, steps + 1):
        a = math.radians(90.0 + 90.0 * i / steps)
        pts.append((cx2 + R * math.cos(a), cz2 + R * math.sin(a)))
    return profile_to_object("board", pts, 0.0, -THICK, (0.0, 0.35, 0.85, 1.0))


def create_receipt():
    W, H, R = 32.0, 40.0, 4.0
    GAP = 0.2
    RW = 3.2                       # 幅(x)
    BOARD_THICK = 2.4
    THICK = BOARD_THICK + GAP      # 2.6
    y_start = GAP / 2.0            # boardを±0.1で挟む
    steps = 16
    color = (0.85, 0.25, 0.1, 1.0)

    x_in = W / 2.0 + GAP           # 内側直線 x = 16.2
    x_out = x_in + RW              # 外側直線 x = 19.4
    z_straight = H - R             # 直線部の上端 = 36
    r_in = R + GAP                 # 内側円弧半径 = 4.2
    r_out = R + GAP + RW           # 外側円弧半径 = 7.4

    def build(sign):
        # boardの隅Rと同心 (中心 sign*(W/2 - R), H - R)
        cx = sign * (W / 2.0 - R)
        cz = H - R
        pts = []
        # 内側直線 下→上
        pts.append((sign * x_in, 0.0))
        pts.append((sign * x_in, z_straight))
        # 内側円弧 (angle 0→90) 半径 r_in
        for i in range(1, steps + 1):
            a = math.radians(90.0 * i / steps)
            pts.append((cx + sign * r_in * math.cos(a), cz + r_in * math.sin(a)))
        # 天面キャップ: 内側円弧終点 → 外側円弧終点 (どちらも x=cx)
        pts.append((cx, cz + r_out))
        # 外側円弧 (angle 90→0) 半径 r_out
        for i in range(steps - 1, -1, -1):
            a = math.radians(90.0 * i / steps)
            pts.append((cx + sign * r_out * math.cos(a), cz + r_out * math.sin(a)))
        # 外側直線 上→下
        pts.append((sign * x_out, 0.0))
        if sign < 0:
            pts.reverse()
        return pts

    obj_r = profile_to_object("receipt_R", build(+1), y_start, -THICK, color)
    obj_l = profile_to_object("receipt_L", build(-1), y_start, -THICK, color)
    return obj_r, obj_l


def create_back():
    W, H, THICK = 40.0, 50.0, 5.0
    x = W / 2.0
    pts = [(-x, 0.0), (x, 0.0), (x, H), (-x, H)]
    return profile_to_object("back", pts, 0.0, THICK, (0.1, 0.7, 0.2, 1.0))


def main():
    setup_units()
    clear_scene()
    create_board()
    create_receipt()
    create_back()


main()