import bpy
import bmesh
import math
import colorsys


# =========================
# 定数
# =========================

MM_SCALE = 1000

CYLINDER_VERTICES_PIPE = 96
CYLINDER_VERTICES_HOLE = 32
CYLINDER_VERTICES_NUT = 6
FLANGE_ROUND_SEGMENTS = 16
CONNECTOR_SECTIONS = 18
FILLET_SEGMENTS = 8

# monitor
MONITOR_X_MIN = -85
MONITOR_X_MAX = 85
MONITOR_Y_MIN = 0
MONITOR_Y_MAX = 20
MONITOR_Z_MIN = 0
MONITOR_Z_MAX = 110
MONITOR_Y_OFFSET = 50

# monitor bracket lower
MONITOR_BKT_LOWER_WIDTH = 12
MONITOR_BKT_LOWER_DEPTH = 9
MONITOR_BKT_LOWER_THICKNESS = 2
MONITOR_BKT_LOWER_HOLE_D = 3
MONITOR_BKT_LOWER_HOLE_X_PITCH = 49
MONITOR_BKT_LOWER_HOLE_Y = -4.5
MONITOR_BKT_LOWER_Z_MIN = 0
MONITOR_BKT_LOWER_Z_MAX = 2

# monitor bracket upper
MONITOR_BKT_UPPER_WIDTH = 10
MONITOR_BKT_UPPER_DEPTH = 25
MONITOR_BKT_UPPER_THICKNESS = 2
MONITOR_BKT_UPPER_HOLE_D = 3
MONITOR_BKT_UPPER_HOLE_X_PITCH = 30
MONITOR_BKT_UPPER_HOLE_Y_1 = -64.5
MONITOR_BKT_UPPER_HOLE_Y_2 = -79.5
MONITOR_BKT_UPPER_HOLE_CENTER_Y = (MONITOR_BKT_UPPER_HOLE_Y_1 + MONITOR_BKT_UPPER_HOLE_Y_2) / 2
MONITOR_BKT_UPPER_Y_MIN = MONITOR_BKT_UPPER_HOLE_CENTER_Y - MONITOR_BKT_UPPER_DEPTH / 2
MONITOR_BKT_UPPER_Y_MAX = MONITOR_BKT_UPPER_HOLE_CENTER_Y + MONITOR_BKT_UPPER_DEPTH / 2
MONITOR_BKT_UPPER_Z_MIN = 65
MONITOR_BKT_UPPER_Z_MAX = 67

## bkt_plate
BKT_PLATE_X_SIZE = 40
BKT_PLATE_Y_SIZE = 25
BKT_PLATE_THICKNESS = 2
BKT_PLATE_HOLE_D = MONITOR_BKT_UPPER_HOLE_D
BKT_PLATE_HOLE_X_PITCH = MONITOR_BKT_UPPER_HOLE_X_PITCH
BKT_PLATE_HOLE_Y_1 = MONITOR_BKT_UPPER_HOLE_Y_1
BKT_PLATE_HOLE_Y_2 = MONITOR_BKT_UPPER_HOLE_Y_2
BKT_PLATE_X_MIN = -BKT_PLATE_X_SIZE / 2
BKT_PLATE_X_MAX = 60
BKT_PLATE_Y_MIN = MONITOR_BKT_UPPER_HOLE_CENTER_Y - BKT_PLATE_Y_SIZE / 2
BKT_PLATE_Y_MAX = MONITOR_BKT_UPPER_HOLE_CENTER_Y + BKT_PLATE_Y_SIZE / 2
BKT_PLATE_Z_MIN = MONITOR_BKT_UPPER_Z_MAX
BKT_PLATE_Z_MAX = MONITOR_BKT_UPPER_Z_MAX + BKT_PLATE_THICKNESS

# bracketA bracket
BRACKET_A_BKT_UPPER_WIDTH = MONITOR_BKT_UPPER_WIDTH
BRACKET_A_BKT_UPPER_DEPTH = 100
BRACKET_A_BKT_UPPER_THICKNESS = MONITOR_BKT_UPPER_THICKNESS
BRACKET_A_BKT_UPPER_HOLE_D = MONITOR_BKT_UPPER_HOLE_D
BRACKET_A_BKT_UPPER_HOLE_X_PITCH = MONITOR_BKT_UPPER_HOLE_X_PITCH
BRACKET_A_BKT_UPPER_HOLE_Y_1 = MONITOR_BKT_UPPER_HOLE_Y_1
BRACKET_A_BKT_UPPER_HOLE_Y_2 = MONITOR_BKT_UPPER_HOLE_Y_2
BRACKET_A_BKT_UPPER_HOLE_CENTER_Y = MONITOR_BKT_UPPER_HOLE_CENTER_Y
BRACKET_A_BKT_UPPER_Y_MAX = MONITOR_BKT_UPPER_Y_MAX
BRACKET_A_BKT_UPPER_Y_MIN = BRACKET_A_BKT_UPPER_Y_MAX - BRACKET_A_BKT_UPPER_DEPTH
BRACKET_A_BKT_UPPER_Z_MIN = MONITOR_BKT_UPPER_Z_MIN - MONITOR_BKT_UPPER_THICKNESS
BRACKET_A_BKT_UPPER_Z_MAX = MONITOR_BKT_UPPER_Z_MIN

BRACKET_A_BKT_LOWER_WIDTH = MONITOR_BKT_LOWER_WIDTH
BRACKET_A_BKT_LOWER_DEPTH = 100
BRACKET_A_BKT_LOWER_THICKNESS = MONITOR_BKT_LOWER_THICKNESS
BRACKET_A_BKT_LOWER_HOLE_D = MONITOR_BKT_LOWER_HOLE_D
BRACKET_A_BKT_LOWER_HOLE_X_PITCH = MONITOR_BKT_LOWER_HOLE_X_PITCH
BRACKET_A_BKT_LOWER_HOLE_Y = MONITOR_BKT_LOWER_HOLE_Y
# 起点はモニターBKT lower の端（y_max）。そこから -y方向に 100mm 伸ばす
BRACKET_A_BKT_LOWER_Y_MAX = MONITOR_BKT_LOWER_HOLE_Y + MONITOR_BKT_LOWER_DEPTH / 2
BRACKET_A_BKT_LOWER_Y_MIN = BRACKET_A_BKT_LOWER_Y_MAX - BRACKET_A_BKT_LOWER_DEPTH
BRACKET_A_BKT_LOWER_Z_MIN = MONITOR_BKT_LOWER_Z_MIN - MONITOR_BKT_LOWER_THICKNESS
BRACKET_A_BKT_LOWER_Z_MAX = MONITOR_BKT_LOWER_Z_MIN

# base
BASE_Z_MIN = 0
BASE_Z_MAX = 40

BASE_PLATE_12_X_MIN = -6
BASE_PLATE_12_X_MAX = 6
BASE_PLATE_12_Y_MIN = 1
BASE_PLATE_12_Y_MAX = 3.8
BASE_PLATE_12_CHAMFER = 0.2

BASE_PLATE_7_X_MIN = -3.5
BASE_PLATE_7_X_MAX = 3.5
BASE_PLATE_7_Y_MIN = -1
BASE_PLATE_7_Y_MAX = 1

# pipe
PIPE_CENTER_X = 0
PIPE_CENTER_Y = -24
PIPE_Z_MIN = 0
PIPE_Z_MAX = 100
PIPE_HEIGHT = PIPE_Z_MAX - PIPE_Z_MIN
PIPE_CENTER_Z = (PIPE_Z_MIN + PIPE_Z_MAX) / 2

PIPE_OUTER_D = 34
PIPE_INNER_D = 28
PIPE_OUTER_R = PIPE_OUTER_D / 2
PIPE_INNER_R = PIPE_INNER_D / 2

PIPE_A_Y_MIN = PIPE_CENTER_Y
PIPE_A_Y_MAX = 30
PIPE_B_Y_MIN = -80
PIPE_B_Y_MAX = PIPE_CENTER_Y

PIPE_HALF_CUTTER_X_SIZE = 100
PIPE_HALF_CUTTER_Z_SIZE = PIPE_HEIGHT + 10
PIPE_INNER_CUTTER_DEPTH = 60

# flange
FLANGE_Z_MIN = 0
FLANGE_Z_MAX = 20
FLANGE_Z_CENTER = 10

FLANGE_INNER_X = 13.5
FLANGE_ROUND_CENTER_X = 21
FLANGE_ROUND_R = 10

BRACKET_A_FLANGE_Y_MIN = -24
BRACKET_A_FLANGE_Y_MAX = -22

BRACKET_B_FLANGE_Y_MIN = -28
BRACKET_B_FLANGE_Y_MAX = -24

# fillet
FLANGE_PIPE_FILLET_R = 2.0

# screw / nut
FLANGE_HOLE_X = 23
FLANGE_HOLE_D = 5
SCREW_HOLE_EXTRA_DEPTH = 4

M4_NUT_FLAT_TO_FLAT = 7.4
M4_NUT_DEPTH = 3
NUT_POCKET_OVER_CUT = 0.3


# =========================
# 初期化
# =========================

for obj in bpy.data.objects:
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.hide_render = False
    obj.select_set(True)

bpy.ops.object.delete()

for mesh in list(bpy.data.meshes):
    bpy.data.meshes.remove(mesh)

for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)


# =========================
# 基本関数
# =========================

def mm(v):
    return v / MM_SCALE


def make_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = color
    return mat


_distinct_color_index = 0


def next_distinct_color():
    """呼び出すたびに異なる色を返す（個々の立体に別々の色を設定するため）"""
    global _distinct_color_index
    hue = (_distinct_color_index * 0.61803398875) % 1.0
    _distinct_color_index += 1
    r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 0.95)
    return (r, g, b, 1.0)


def boolean_op(target, cutter, op):
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active = target

    mod_name = f"bool_{id(cutter)}"
    mod = target.modifiers.new(name=mod_name, type='BOOLEAN')
    mod.operation = op
    mod.object = cutter
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=mod_name)

    bpy.data.objects.remove(cutter, do_unlink=True)


def add_box(name, parent, material, x_min, x_max, y_min, y_max, z_min, z_max):
    sx = mm(x_max - x_min)
    sy = mm(y_max - y_min)
    sz = mm(z_max - z_min)

    cx = mm((x_min + x_max) / 2)
    cy = mm((y_min + y_max) / 2)
    cz = mm((z_min + z_max) / 2)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    return obj


def add_prism_xz(name, parent, material, verts_xz, y_min, y_max):
    y0 = mm(y_min)
    y1 = mm(y_max)
    n = len(verts_xz)

    verts = [(mm(x), y0, mm(z)) for x, z in verts_xz]
    verts += [(mm(x), y1, mm(z)) for x, z in verts_xz]

    faces = [
        tuple(range(n - 1, -1, -1)),
        tuple(range(n, 2 * n)),
    ]

    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    return obj


def add_prism_xy(name, parent, material, verts_xy, z_min, z_max):
    z0 = mm(z_min)
    z1 = mm(z_max)
    n = len(verts_xy)

    verts = [(mm(x), mm(y), z0) for x, y in verts_xy]
    verts += [(mm(x), mm(y), z1) for x, y in verts_xy]

    faces = [
        tuple(range(n - 1, -1, -1)),
        tuple(range(n, 2 * n)),
    ]

    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    return obj


def hide_all_recursively(obj):
    obj.hide_set(True)
    for child in obj.children:
        hide_all_recursively(child)


def add_prism_yz(name, parent, material, verts_yz, x_min, x_max):
    x0 = mm(x_min)
    x1 = mm(x_max)
    n = len(verts_yz)

    verts = [(x0, mm(y), mm(z)) for y, z in verts_yz]
    verts += [(x1, mm(y), mm(z)) for y, z in verts_yz]

    faces = [
        tuple(range(n - 1, -1, -1)),
        tuple(range(n, 2 * n)),
    ]

    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)
    mesh.update()

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    return obj


def add_through_hole_z(target, x, y, z_min, z_max, diameter):
    """Z軸方向に貫通穴を開ける"""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(diameter / 2),
        depth=mm(z_max - z_min + 10),
        location=(mm(x), mm(y), mm((z_min + z_max) / 2)),
        vertices=CYLINDER_VERTICES_HOLE
    )
    hole = bpy.context.active_object
    boolean_op(target, hole, 'DIFFERENCE')


# =========================
# monitor / base
# =========================

def make_monitor():
    mat = make_material("mat_monitor", (0.8, 0.8, 0.8, 1.0))
    
    monitor = add_box(
        "monitor",
        None,
        mat,
        MONITOR_X_MIN,
        MONITOR_X_MAX,
        MONITOR_Y_MIN,
        MONITOR_Y_MAX,
        MONITOR_Z_MIN,
        MONITOR_Z_MAX
    )
    
    # y方向に+50mm移動
    monitor.location.y += mm(MONITOR_Y_OFFSET)
    
    return monitor


def make_monitor_bkt_lower():
    mat = make_material("mat_monitor_bkt_lower", (0.6, 0.6, 0.6, 1.0))
    
    parent = bpy.data.objects.new("monitor_bkt_lower", None)
    bpy.context.collection.objects.link(parent)
    
    # 2インスタンスを生成
    for x_offset in [-MONITOR_BKT_LOWER_HOLE_X_PITCH / 2, MONITOR_BKT_LOWER_HOLE_X_PITCH / 2]:
        plate = add_box(
            f"monitor_bkt_lower_plate_{x_offset}",
            parent,
            mat,
            x_offset - MONITOR_BKT_LOWER_WIDTH / 2,
            x_offset + MONITOR_BKT_LOWER_WIDTH / 2,
            MONITOR_BKT_LOWER_HOLE_Y - MONITOR_BKT_LOWER_DEPTH / 2,
            MONITOR_BKT_LOWER_HOLE_Y + MONITOR_BKT_LOWER_DEPTH / 2,
            MONITOR_BKT_LOWER_Z_MIN,
            MONITOR_BKT_LOWER_Z_MAX
        )
        
        # 穴を開ける（z方向全貫通）
        add_through_hole_z(plate, x_offset, MONITOR_BKT_LOWER_HOLE_Y, 
                          MONITOR_BKT_LOWER_Z_MIN, MONITOR_BKT_LOWER_Z_MAX, 
                          MONITOR_BKT_LOWER_HOLE_D)
    
    return parent


def make_monitor_bkt_upper():
    mat = make_material("mat_monitor_bkt_upper", (0.5, 0.5, 0.5, 1.0))
    
    parent = bpy.data.objects.new("monitor_bkt_upper", None)
    bpy.context.collection.objects.link(parent)
    
    # 2インスタンスを生成
    for x_offset in [-MONITOR_BKT_UPPER_HOLE_X_PITCH / 2, MONITOR_BKT_UPPER_HOLE_X_PITCH / 2]:
        plate = add_box(
            f"monitor_bkt_upper_plate_{x_offset}",
            parent,
            mat,
            x_offset - MONITOR_BKT_UPPER_WIDTH / 2,
            x_offset + MONITOR_BKT_UPPER_WIDTH / 2,
            MONITOR_BKT_UPPER_Y_MIN,
            MONITOR_BKT_UPPER_Y_MAX,
            MONITOR_BKT_UPPER_Z_MIN,
            MONITOR_BKT_UPPER_Z_MAX
        )
        
        # 2つの穴を開ける
        add_through_hole_z(plate, x_offset, MONITOR_BKT_UPPER_HOLE_Y_1,
                          MONITOR_BKT_UPPER_Z_MIN, MONITOR_BKT_UPPER_Z_MAX,
                          MONITOR_BKT_UPPER_HOLE_D)
        add_through_hole_z(plate, x_offset, MONITOR_BKT_UPPER_HOLE_Y_2,
                          MONITOR_BKT_UPPER_Z_MIN, MONITOR_BKT_UPPER_Z_MAX,
                          MONITOR_BKT_UPPER_HOLE_D)
    
    return parent


def make_monitor_bkt_group():
    """monitor_bkt_lower と monitor_bkt_upper をグループ化し、回転・移動を適用"""
    # グループ親を作成
    group_parent = bpy.data.objects.new("monitor_bkt_group", None)
    bpy.context.collection.objects.link(group_parent)
    
    # 各ブラケットを生成し、グループ親の子にする
    lower = make_monitor_bkt_lower()
    upper = make_monitor_bkt_upper()
    
    lower.parent = group_parent
    upper.parent = group_parent
    
    make_bkt_plate(group_parent)
    
    # グループ親を回転中心 (0, MONITOR_Y_OFFSET, 0) に配置
    group_parent.location = (0, mm(MONITOR_Y_OFFSET), 0)
    
    # x軸に沿って -30度回転
    group_parent.rotation_euler = (-math.radians(30), 0, 0)
    
    # y方向に +5mm、z方向に -10mm移動
    group_parent.location.y += mm(5)
    group_parent.location.z -= mm(10)
    
    return group_parent


def make_bracketA_bkt_upper():
    parent = bpy.data.objects.new("bracketA_bkt_upper", None)
    bpy.context.collection.objects.link(parent)
    
    for i, x_offset in enumerate([-BRACKET_A_BKT_UPPER_HOLE_X_PITCH / 2, BRACKET_A_BKT_UPPER_HOLE_X_PITCH / 2]):
        mat = make_material(f"mat_bracketA_bkt_upper_{i}", next_distinct_color())
        plate = add_box(
            f"bracketA_bkt_upper_plate_{x_offset}",
            parent,
            mat,
            x_offset - BRACKET_A_BKT_UPPER_WIDTH / 2,
            x_offset + BRACKET_A_BKT_UPPER_WIDTH / 2,
            BRACKET_A_BKT_UPPER_Y_MIN,
            BRACKET_A_BKT_UPPER_Y_MAX,
            BRACKET_A_BKT_UPPER_Z_MIN,
            BRACKET_A_BKT_UPPER_Z_MAX
        )
        
        add_through_hole_z(plate, x_offset, BRACKET_A_BKT_UPPER_HOLE_Y_1,
                          BRACKET_A_BKT_UPPER_Z_MIN, BRACKET_A_BKT_UPPER_Z_MAX,
                          BRACKET_A_BKT_UPPER_HOLE_D)
        add_through_hole_z(plate, x_offset, BRACKET_A_BKT_UPPER_HOLE_Y_2,
                          BRACKET_A_BKT_UPPER_Z_MIN, BRACKET_A_BKT_UPPER_Z_MAX,
                          BRACKET_A_BKT_UPPER_HOLE_D)
    
    return parent


def make_bracketA_bkt_lower():
    parent = bpy.data.objects.new("bracketA_bkt_lower", None)
    bpy.context.collection.objects.link(parent)
    
    for i, x_offset in enumerate([-BRACKET_A_BKT_LOWER_HOLE_X_PITCH / 2, BRACKET_A_BKT_LOWER_HOLE_X_PITCH / 2]):
        mat = make_material(f"mat_bracketA_bkt_lower_{i}", next_distinct_color())
        plate = add_box(
            f"bracketA_bkt_lower_plate_{x_offset}",
            parent,
            mat,
            x_offset - BRACKET_A_BKT_LOWER_WIDTH / 2,
            x_offset + BRACKET_A_BKT_LOWER_WIDTH / 2,
            BRACKET_A_BKT_LOWER_Y_MIN,
            BRACKET_A_BKT_LOWER_Y_MAX,
            BRACKET_A_BKT_LOWER_Z_MIN,
            BRACKET_A_BKT_LOWER_Z_MAX
        )
        
        add_through_hole_z(plate, x_offset, BRACKET_A_BKT_LOWER_HOLE_Y,
                          BRACKET_A_BKT_LOWER_Z_MIN, BRACKET_A_BKT_LOWER_Z_MAX,
                          BRACKET_A_BKT_LOWER_HOLE_D)
    
    return parent

def make_bracketA_bkt_group():
    """bracketA_bkt_upper と bracketA_bkt_lower をグループ化し、回転・移動を適用"""
    group_parent = bpy.data.objects.new("bracketA_bkt_group", None)
    bpy.context.collection.objects.link(group_parent)
    
    # upper = make_bracketA_bkt_upper()
    # lower = make_bracketA_bkt_lower()
    
    # upper.parent = group_parent
    # lower.parent = group_parent
    
    group_parent.location = (0, mm(MONITOR_Y_OFFSET), 0)
    group_parent.rotation_euler = (-math.radians(30), 0, 0)
    group_parent.location.y += mm(5)
    group_parent.location.z -= mm(10)

    # monitor_assembly と同じ変換（+30度回転・y方向+30mm移動）を上位に被せて、
    # モニターBKTの新しい位置・角度に追従させる。
    # カットはワールド空間で行うため、この親変換をカットより前に適用する。
    assembly_parent = bpy.data.objects.new("bracketA_bkt_assembly", None)
    bpy.context.collection.objects.link(assembly_parent)
    group_parent.parent = assembly_parent
    assembly_parent.rotation_euler = (math.radians(30), 0, 0)
    assembly_parent.location.y = mm(30)

    # 回転・移動をワールド行列に反映させてからカットする
    # （これをしないと boolean modifier が回転前の位置で評価してしまう）
    bpy.context.view_layer.update()

    # 各プレート（子メッシュ）にカッターを適用
    # ※カッターはワールド空間の軸に沿った十分大きな形状で生成し、
    #   boolean modifier がプレートのワールド変換（回転・移動）を考慮して
    #   「回転・移動後のブラケット」をワールド空間でカットする。
    #   回転で傾いたブラケットを取りこぼさないよう、カッターは全方向に十分大きくする。
    # for empty in [upper, lower]:
    #     for plate in list(empty.children):
    #         # カッター1: ワールドの xz平面 y=PIPE_CENTER_Y で分割する半空間ボックス。
    #         #            y < PIPE_CENTER_Y 側を削除し、y > PIPE_CENTER_Y のみ残す
    #         #            （ブラケットBの領域に干渉しない）
    #         cutter_plane = add_box(
    #             "cutter_plane",
    #             None,
    #             make_material("mat_cutter", (1.0, 0.0, 0.0, 0.5)),
    #             -500,
    #             500,
    #             PIPE_CENTER_Y - 1000,
    #             PIPE_CENTER_Y,
    #             -500,
    #             500
    #         )
    #         boolean_op(plate, cutter_plane, 'DIFFERENCE')
    #
    #         # カッター2: ワールドz軸に沿ったパイプ内径シリンダー（パイプ内部に干渉しない）
    #         #            回転で傾いたブラケットを貫通できるよう十分な高さにする
    #         bpy.ops.mesh.primitive_cylinder_add(
    #             radius=mm(PIPE_INNER_D / 2),
    #             depth=mm(1000),
    #             location=(mm(PIPE_CENTER_X), mm(PIPE_CENTER_Y), 0),
    #             vertices=CYLINDER_VERTICES_HOLE
    #         )
    #         cutter_cylinder = bpy.context.active_object
    #         boolean_op(plate, cutter_cylinder, 'DIFFERENCE')
    
    return group_parent

# =========================
# pipe
# =========================

def make_pipe_half(name, parent, material, side):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(PIPE_OUTER_R),
        depth=mm(PIPE_HEIGHT),
        location=(mm(PIPE_CENTER_X), mm(PIPE_CENTER_Y), mm(PIPE_CENTER_Z)),
        vertices=CYLINDER_VERTICES_PIPE
    )
    pipe = bpy.context.active_object
    pipe.name = name

    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(PIPE_INNER_R),
        depth=mm(PIPE_HEIGHT + 10),
        location=(mm(PIPE_CENTER_X), mm(PIPE_CENTER_Y), mm(PIPE_CENTER_Z)),
        vertices=CYLINDER_VERTICES_PIPE
    )
    inner = bpy.context.active_object
    boolean_op(pipe, inner, 'DIFFERENCE')

    if side == 'A':
        y_min = PIPE_A_Y_MIN
        y_max = PIPE_A_Y_MAX
    else:
        y_min = PIPE_B_Y_MIN
        y_max = PIPE_B_Y_MAX

    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(
            mm(PIPE_CENTER_X),
            mm((y_min + y_max) / 2),
            mm(PIPE_CENTER_Z)
        )
    )
    cutter = bpy.context.active_object
    cutter.scale = (
        mm(PIPE_HALF_CUTTER_X_SIZE),
        mm(y_max - y_min),
        mm(PIPE_HALF_CUTTER_Z_SIZE)
    )
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boolean_op(pipe, cutter, 'INTERSECT')

    pipe.data.materials.append(material)

    if parent:
        pipe.parent = parent

    return pipe


# =========================
# bracketA connector
# =========================

def tangent_point_from_base_to_pipe(x0, y0, cx, cy, r):
    vx = x0 - cx
    vy = y0 - cy
    d2 = vx * vx + vy * vy

    a = r * r / d2
    b = r * math.sqrt(d2 - r * r) / d2

    tx1 = cx + a * vx - b * vy
    ty1 = cy + a * vy + b * vx

    tx2 = cx + a * vx + b * vy
    ty2 = cy + a * vy - b * vx

    if x0 > 0:
        return (tx1, ty1) if tx1 > 0 else (tx2, ty2)

    return (tx1, ty1) if tx1 < 0 else (tx2, ty2)



# =========================
# flange / holes / fillet
# =========================

def add_screw_hole_y(target, x, y_min, y_max, z, diameter):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(diameter / 2),
        depth=mm((y_max - y_min) + SCREW_HOLE_EXTRA_DEPTH),
        location=(mm(x), mm((y_min + y_max) / 2), mm(z)),
        rotation=(math.pi / 2, 0, 0),
        vertices=CYLINDER_VERTICES_HOLE
    )
    hole = bpy.context.active_object
    boolean_op(target, hole, 'DIFFERENCE')


def add_m4_nut_pocket_y(target, x, y_outer, direction, z, material):
    r = M4_NUT_FLAT_TO_FLAT / math.sqrt(3)

    if direction == "plus_y":
        y0 = y_outer - NUT_POCKET_OVER_CUT
        y1 = y_outer + M4_NUT_DEPTH
    else:
        y0 = y_outer - M4_NUT_DEPTH
        y1 = y_outer + NUT_POCKET_OVER_CUT

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=CYLINDER_VERTICES_NUT,
        radius=mm(r),
        depth=mm(y1 - y0),
        location=(mm(x), mm((y0 + y1) / 2), mm(z)),
        rotation=(math.pi / 2, 0, 0)
    )

    pocket = bpy.context.active_object
    pocket.name = "m4_nut_pocket_cutter"
    pocket.data.materials.append(material)

    boolean_op(target, pocket, 'DIFFERENCE')


def cut_pipe_inner_void_z(target):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(PIPE_INNER_R),
        depth=mm(PIPE_INNER_CUTTER_DEPTH),
        location=(mm(PIPE_CENTER_X), mm(PIPE_CENTER_Y), mm(PIPE_CENTER_Z)),
        vertices=CYLINDER_VERTICES_PIPE
    )
    cutter = bpy.context.active_object
    boolean_op(target, cutter, 'DIFFERENCE')


def make_flange_verts(side):
    verts = []

    if side == 'R':
        verts.append((FLANGE_INNER_X, FLANGE_Z_MIN))
        verts.append((FLANGE_ROUND_CENTER_X, FLANGE_Z_MIN))

        for i in range(1, FLANGE_ROUND_SEGMENTS):
            a = -math.pi / 2 + math.pi * i / FLANGE_ROUND_SEGMENTS
            verts.append((
                FLANGE_ROUND_CENTER_X + FLANGE_ROUND_R * math.cos(a),
                FLANGE_Z_CENTER + FLANGE_ROUND_R * math.sin(a)
            ))

        verts.append((FLANGE_ROUND_CENTER_X, FLANGE_Z_MAX))
        verts.append((FLANGE_INNER_X, FLANGE_Z_MAX))

    else:
        verts.append((-FLANGE_INNER_X, FLANGE_Z_MAX))
        verts.append((-FLANGE_ROUND_CENTER_X, FLANGE_Z_MAX))

        for i in range(1, FLANGE_ROUND_SEGMENTS):
            a = math.pi / 2 + math.pi * i / FLANGE_ROUND_SEGMENTS
            verts.append((
                -FLANGE_ROUND_CENTER_X + FLANGE_ROUND_R * math.cos(a),
                FLANGE_Z_CENTER + FLANGE_ROUND_R * math.sin(a)
            ))

        verts.append((-FLANGE_ROUND_CENTER_X, FLANGE_Z_MIN))
        verts.append((-FLANGE_INNER_X, FLANGE_Z_MIN))

    return verts


def make_flange_half(name, parent, material, y_min, y_max, side, nut_pocket=False, pocket_outer_side=None):
    verts = make_flange_verts(side)

    hole_x = FLANGE_HOLE_X if side == 'R' else -FLANGE_HOLE_X

    flange = add_prism_xz(name, None, material, verts, y_min, y_max)

    cut_pipe_inner_void_z(flange)

    if nut_pocket:
        if pocket_outer_side == "min":
            add_m4_nut_pocket_y(
                target=flange,
                x=hole_x,
                y_outer=y_min,
                direction="plus_y",
                z=FLANGE_Z_CENTER,
                material=material
            )
        else:
            add_m4_nut_pocket_y(
                target=flange,
                x=hole_x,
                y_outer=y_max,
                direction="minus_y",
                z=FLANGE_Z_CENTER,
                material=material
            )

    add_screw_hole_y(
        target=flange,
        x=hole_x,
        y_min=y_min,
        y_max=y_max,
        z=FLANGE_Z_CENTER,
        diameter=FLANGE_HOLE_D
    )

    if parent:
        flange.parent = parent

    return flange


def make_fillet_xy_verts(side, y_base, direction):
    r = FLANGE_PIPE_FILLET_R
    R = PIPE_OUTER_R
    cxp = PIPE_CENTER_X
    cyp = PIPE_CENTER_Y

    sx = 1 if side == 'R' else -1
    sy = 1 if direction == "plus_y" else -1

    y_face = y_base

    # フィレット円弧の中心 O を求める
    #   ・フランジ面(直線 y = y_face)に接する -> 面から距離 r
    #   ・パイプ外周(半径 R)に外接する      -> パイプ中心から距離 R + r
    oy = y_face + sy * r
    dy = oy - cyp
    ox = cxp + sx * math.sqrt((R + r) ** 2 - dy ** 2)

    # フランジ面との接点(O から面へ下ろした垂線の足)
    tf = (ox, y_face)

    # パイプ外周との接点(パイプ中心と O を結ぶ線上、半径 R の位置)
    vx = ox - cxp
    vy = oy - cyp
    vlen = math.hypot(vx, vy)
    tp = (cxp + R * vx / vlen, cyp + R * vy / vlen)

    # フランジ面とパイプ外周の交点(隅)
    cx_corner = cxp + sx * math.sqrt(R ** 2 - (y_face - cyp) ** 2)
    corner = (cx_corner, y_face)

    def shortest_delta(a_from, a_to):
        d = a_to - a_from
        while d <= -math.pi:
            d += 2 * math.pi
        while d > math.pi:
            d -= 2 * math.pi
        return d

    verts = [corner, tf]

    # フィレット円弧 tf -> tp (中心 O, 半径 r, 隅側を通る短い弧)
    a_tf = math.atan2(tf[1] - oy, tf[0] - ox)
    a_tp = math.atan2(tp[1] - oy, tp[0] - ox)
    da = shortest_delta(a_tf, a_tp)
    for i in range(1, FILLET_SEGMENTS):
        a = a_tf + da * i / FILLET_SEGMENTS
        verts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    verts.append(tp)

    # パイプ外周に沿って tp -> corner (中心 パイプ中心, 半径 R)
    a_tp = math.atan2(tp[1] - cyp, tp[0] - cxp)
    a_co = math.atan2(corner[1] - cyp, corner[0] - cxp)
    db = shortest_delta(a_tp, a_co)
    for i in range(1, FILLET_SEGMENTS):
        a = a_tp + db * i / FILLET_SEGMENTS
        verts.append((cxp + R * math.cos(a), cyp + R * math.sin(a)))

    return verts

def make_pipe_flange_fillet(name, parent, material, side, y_base, direction):
    verts_xy = make_fillet_xy_verts(side, y_base, direction)

    fillet = add_prism_xy(
        name,
        None,
        material,
        verts_xy,
        FLANGE_Z_MIN,
        FLANGE_Z_MAX
    )

    cut_pipe_inner_void_z(fillet)

    if parent:
        fillet.parent = parent

    return fillet


# =========================
# bracket
# =========================

def make_bracketA():
    mat = make_material("mat_bracketA", (0.4, 0.7, 0.9, 1.0))

    parent = bpy.data.objects.new("bracketA", None)
    bpy.context.collection.objects.link(parent)

    make_pipe_half("bracketA_pipe", parent, mat, 'A')

    make_flange_half(
        "bracketA_flange_R",
        parent,
        mat,
        BRACKET_A_FLANGE_Y_MIN,
        BRACKET_A_FLANGE_Y_MAX,
        'R',
        nut_pocket=False
    )

    make_flange_half(
        "bracketA_flange_L",
        parent,
        mat,
        BRACKET_A_FLANGE_Y_MIN,
        BRACKET_A_FLANGE_Y_MAX,
        'L',
        nut_pocket=False
    )

    make_pipe_flange_fillet(
        "bracketA_fillet_R",
        parent,
        mat,
        'R',
        BRACKET_A_FLANGE_Y_MAX,
        "plus_y"
    )

    make_pipe_flange_fillet(
        "bracketA_fillet_L",
        parent,
        mat,
        'L',
        BRACKET_A_FLANGE_Y_MAX,
        "plus_y"
    )

    return parent


def make_bracketB():
    mat = make_material("mat_bracketB", (0.9, 0.5, 0.4, 1.0))

    parent = bpy.data.objects.new("bracketB", None)
    bpy.context.collection.objects.link(parent)

    make_pipe_half("bracketB_pipe", parent, mat, 'B')

    make_flange_half(
        "bracketB_flange_R",
        parent,
        mat,
        BRACKET_B_FLANGE_Y_MIN,
        BRACKET_B_FLANGE_Y_MAX,
        'R',
        nut_pocket=True,
        pocket_outer_side="min"
    )

    make_flange_half(
        "bracketB_flange_L",
        parent,
        mat,
        BRACKET_B_FLANGE_Y_MIN,
        BRACKET_B_FLANGE_Y_MAX,
        'L',
        nut_pocket=True,
        pocket_outer_side="min"
    )

    make_pipe_flange_fillet(
        "bracketB_fillet_R",
        parent,
        mat,
        'R',
        BRACKET_B_FLANGE_Y_MIN,
        "minus_y"
    )

    make_pipe_flange_fillet(
        "bracketB_fillet_L",
        parent,
        mat,
        'L',
        BRACKET_B_FLANGE_Y_MIN,
        "minus_y"
    )

    return parent


def make_bkt_plate(parent_group):
    mat = make_material("mat_bkt_plate", next_distinct_color())
    parent = bpy.data.objects.new("bkt_plate", None)
    bpy.context.collection.objects.link(parent)
    parent.parent = parent_group

    plate = add_box(
        "bkt_plate_body", parent, mat,
        BKT_PLATE_X_MIN, BKT_PLATE_X_MAX,
        BKT_PLATE_Y_MIN, BKT_PLATE_Y_MAX,
        BKT_PLATE_Z_MIN, BKT_PLATE_Z_MAX
    )
    for sx in (-1, 1):
        for y in (BKT_PLATE_HOLE_Y_1, BKT_PLATE_HOLE_Y_2):
            add_through_hole_z(
                plate,
                sx * BKT_PLATE_HOLE_X_PITCH / 2, y,
                BKT_PLATE_Z_MIN, BKT_PLATE_Z_MAX,
                BKT_PLATE_HOLE_D
            )
    return parent


# =========================
# 生成
# =========================

monitor = make_monitor()
monitor_bkt_group = make_monitor_bkt_group()

# monitor と monitor_bkt_group の親オブジェクトを作成し、
# monitor_bkt_group の回転角のマイナス値（+30度）で回転
monitor_assembly_parent = bpy.data.objects.new("monitor_assembly", None)
bpy.context.collection.objects.link(monitor_assembly_parent)

monitor.parent = monitor_assembly_parent
monitor_bkt_group.parent = monitor_assembly_parent

# monitor_bkt_group の回転角（-30度）のマイナス値（+30度）で回転
monitor_assembly_parent.rotation_euler = (math.radians(30), 0, 0)

# y方向に+30mm移動
monitor_assembly_parent.location.x = -60 / MM_SCALE
monitor_assembly_parent.location.y = 10 / MM_SCALE

make_bracketA_bkt_group()
make_bracketA()
make_bracketB()