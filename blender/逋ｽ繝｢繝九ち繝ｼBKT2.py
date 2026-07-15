import bpy
import bmesh
import math

def mm(v):
    return v / 1000.0

OBJ_NAME = "monitor_plate"

plate_width_x = mm(164.0)
plate_height_z = mm(106.0)
plate_thickness_y = mm(2.0)

cut_width_x = mm(100.0)
cut_height_z = mm(70.0)

hole_diameter = mm(5.0)
hole_radius = hole_diameter / 2.0
hole_offset_from_edge = mm(7.0)
hole_segments = 64

def clear_scene():
    for obj in bpy.context.scene.objects:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)

    bpy.ops.object.delete()

def make_monitor_plate():
    x_min = -plate_width_x / 2.0
    x_max = plate_width_x / 2.0

    y_min = 0.0
    y_max = plate_thickness_y

    z_min = 0.0
    z_max = plate_height_z

    cut_x_min = -cut_width_x / 2.0
    cut_x_max = cut_width_x / 2.0
    cut_z_min = z_max - cut_height_z

    countersink_diameter_y0 = mm(6.0)
    countersink_diameter_ymax = mm(3.0)
    countersink_extra_depth = mm(0.2)

    countersink_radius_y0 = countersink_diameter_y0 / 2.0
    countersink_radius_ymax = countersink_diameter_ymax / 2.0
    countersink_depth = plate_thickness_y + countersink_extra_depth
    countersink_center_y = plate_thickness_y / 2.0
    countersink_rotation = (math.radians(90.0), 0.0, 0.0)

    verts_2d = [
        (x_min, z_min),
        (x_max, z_min),
        (x_max, z_max),
        (cut_x_max, z_max),
        (cut_x_max, cut_z_min),
        (cut_x_min, cut_z_min),
        (cut_x_min, z_max),
        (x_min, z_max),
    ]

    verts = []

    for x, z in verts_2d:
        verts.append((x, y_min, z))

    for x, z in verts_2d:
        verts.append((x, y_max, z))

    faces = []

    faces.append(tuple(range(len(verts_2d) - 1, -1, -1)))
    faces.append(tuple(range(len(verts_2d), len(verts_2d) * 2)))

    n = len(verts_2d)

    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))

    mesh = bpy.data.meshes.new(f"{OBJ_NAME}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(OBJ_NAME, mesh)
    bpy.context.collection.objects.link(obj)

    hole_x_left = x_min + hole_offset_from_edge
    hole_x_right = x_max - hole_offset_from_edge
    hole_z_bottom = z_min + hole_offset_from_edge
    hole_z_top = z_max - hole_offset_from_edge

    hole_positions = [
        (hole_x_left, hole_z_bottom),
        (hole_x_right, hole_z_bottom),
        (hole_x_left, hole_z_top),
        (hole_x_right, hole_z_top),
    ]

    cutters = []

    for i, (x, z) in enumerate(hole_positions, start=1):
        bpy.ops.mesh.primitive_cone_add(
            vertices=hole_segments,
            radius1=countersink_radius_ymax,
            radius2=countersink_radius_y0,
            depth=countersink_depth,
            location=(x, countersink_center_y, z),
            rotation=countersink_rotation,
        )

        cutter = bpy.context.object
        cutter.name = f"{OBJ_NAME}_countersink_cutter_{i}"
        cutters.append(cutter)

        mod = obj.modifiers.new(
            name=f"countersink_hole_{i}",
            type="BOOLEAN"
        )
        mod.operation = "DIFFERENCE"
        mod.object = cutter

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)

    for cutter in cutters:
        bpy.data.objects.remove(cutter, do_unlink=True)

    return obj

# =========================
# bracketA / bracketB 用 定数
# =========================

CYLINDER_VERTICES_PIPE = 96
CYLINDER_VERTICES_HOLE = 32
CYLINDER_VERTICES_NUT = 6
FLANGE_ROUND_SEGMENTS = 16
FILLET_SEGMENTS = 8

# pipe
PIPE_CENTER_X = 0
PIPE_CENTER_Y = -24
PIPE_Z_MIN = 0
PIPE_Z_MAX = 56  # コネクターと同じ高さ（PLATE_Z_OFFSET + PLATE_SOLID_HEIGHT = 20 + 36）
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

# connector (plate <-> bracketA)
PLATE_Z_OFFSET = 20
PLATE_SOLID_HEIGHT = 36
CONNECTOR_X_MIN = -PIPE_OUTER_D / 2
CONNECTOR_X_MAX = PIPE_OUTER_D / 2
CONNECTOR_Y_MIN = PIPE_CENTER_Y
CONNECTOR_Y_MAX = 0
CONNECTOR_Z_MIN = PLATE_Z_OFFSET
CONNECTOR_Z_MAX = PLATE_Z_OFFSET + PLATE_SOLID_HEIGHT

# connector のロフト(断面補間)パラメータ
CONNECTOR_Z_BOTTOM = PIPE_Z_MIN            # z=0: パイプ外径の半円に一致
CONNECTOR_Z_MORPH_END = PLATE_Z_OFFSET     # z=20: 四角形(3辺)になる
CONNECTOR_Z_TOP = CONNECTOR_Z_MAX          # z=56: プレート結合部の上端
CONNECTOR_MORPH_SEGMENTS = 24              # 断面輪郭の分割数
CONNECTOR_Z_SEGMENTS = 16                  # モーフ区間の z 分割数


# =========================
# bracketA / bracketB 用 基本関数
# =========================

def make_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = color
    return mat


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

    # フランジの z 範囲(FLANGE_Z_MIN〜FLANGE_Z_MAX)全体をカバーしてパイプ内径でカット
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(PIPE_INNER_D / 2),
        depth=mm((FLANGE_Z_MAX - FLANGE_Z_MIN) + 10),
        location=(
            mm(PIPE_CENTER_X),
            mm(PIPE_CENTER_Y),
            mm(FLANGE_Z_CENTER),
        ),
        vertices=CYLINDER_VERTICES_PIPE,
    )
    inner_cutter = bpy.context.active_object
    boolean_op(flange, inner_cutter, 'DIFFERENCE')

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

    oy = y_face + sy * r
    dy = oy - cyp
    ox = cxp + sx * math.sqrt((R + r) ** 2 - dy ** 2)

    tf = (ox, y_face)

    vx = ox - cxp
    vy = oy - cyp
    vlen = math.hypot(vx, vy)
    tp = (cxp + R * vx / vlen, cyp + R * vy / vlen)

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

    a_tf = math.atan2(tf[1] - oy, tf[0] - ox)
    a_tp = math.atan2(tp[1] - oy, tp[0] - ox)
    da = shortest_delta(a_tf, a_tp)
    for i in range(1, FILLET_SEGMENTS):
        a = a_tf + da * i / FILLET_SEGMENTS
        verts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    verts.append(tp)

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


def make_plate_connector_fillet(name, parent, material, side):
    """プレート(y=0)とコネクター側壁(x=±PIPE_OUTER_R)が接する
    z方向の稜線に沿って凹フィレットを追加する。

      - コネクター側壁: 平面 x = ±PIPE_OUTER_R（材料は内側）
      - プレート面     : 平面 y = 0（材料は +y 側）
      - 稜線           : (x=±PIPE_OUTER_R, y=0) を z 方向に伸びる線

    断面(xy平面)は、側壁への接点 A=(x_wall, -r) と
    プレートへの接点 B=(x_wall±r, 0) を結ぶ半径 r の円弧で
    構成される凹フィレット。
    """
    r = FLANGE_PIPE_FILLET_R  # 2mm

    sx = 1 if side == 'R' else -1
    x_wall = sx * PIPE_OUTER_R

    cx = x_wall + sx * r   # 円弧の中心 x
    cy = -r                # 円弧の中心 y

    corner = (x_wall, 0.0)          # 稜線位置(側壁とプレートの交線)
    a_b = math.pi / 2               # プレート接点 B の角度
    a_a = math.pi if side == 'R' else 0.0  # 側壁接点 A の角度

    verts_xy = [corner]
    for i in range(FILLET_SEGMENTS + 1):
        a = a_b + (a_a - a_b) * i / FILLET_SEGMENTS
        verts_xy.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    fillet = add_prism_xy(
        name,
        None,
        material,
        verts_xy,
        PLATE_Z_OFFSET,
        CONNECTOR_Z_TOP
    )

    if parent:
        fillet.parent = parent

    return fillet


# =========================
# bracket
# =========================

def _connector_semicircle_point(u):
    # u in [0,1]: (-R,-24) -> (0,-24+R) -> (R,-24) のパイプ外径半円上の点
    theta = math.pi * (1.0 - u)
    x = PIPE_OUTER_R * math.cos(theta)
    y = PIPE_CENTER_Y + PIPE_OUTER_R * math.sin(theta)
    return (x, y)


def _connector_rect_point(u):
    # u in [0,1]: 四角形の3辺（左辺 -> 上辺 -> 右辺）上の点
    x_left = CONNECTOR_X_MIN
    x_right = CONNECTOR_X_MAX
    y_bot = CONNECTOR_Y_MIN
    y_top = CONNECTOR_Y_MAX

    left_len = y_top - y_bot
    top_len = x_right - x_left
    right_len = y_top - y_bot
    total = left_len + top_len + right_len

    d = u * total
    if d <= left_len:
        return (x_left, y_bot + d)
    d -= left_len
    if d <= top_len:
        return (x_left + d, y_top)
    d -= top_len
    return (x_right, y_top - d)


def make_bracketA_connector(name, parent, material):
    # プレートとブラケットAを結合するブロック。
    # 底面とパイプが垂直に接するのを避けるため、z方向に断面を補間して
    # なだらかに遷移させる。
    #   z=CONNECTOR_Z_BOTTOM(=0)      : 断面輪郭 = パイプ外径の半円
    #   z=CONNECTOR_Z_MORPH_END(=20)  : 断面輪郭 = 四角形の3辺(左・上・右)
    #   z>=CONNECTOR_Z_MORPH_END       : 四角形のまま
    # どちらの輪郭も (-R,-24)〜(R,-24) を端点とし、底辺(y=PIPE_CENTER_Y)で閉じる。
    P = CONNECTOR_MORPH_SEGMENTS + 1

    z_levels = []
    for i in range(CONNECTOR_Z_SEGMENTS + 1):
        z_levels.append(
            CONNECTOR_Z_BOTTOM
            + (CONNECTOR_Z_MORPH_END - CONNECTOR_Z_BOTTOM) * i / CONNECTOR_Z_SEGMENTS
        )
    z_levels.append(CONNECTOR_Z_TOP)

    # 断面サンプルの u 値。四角形の上辺の角(±R, 0)にちょうど頂点が乗らないと
    # プレート側の面が両端で斜めに削れて隙間になるため、角に対応する u を
    # 明示的にサンプル点へ含める。
    left_len = CONNECTOR_Y_MAX - CONNECTOR_Y_MIN
    top_len = CONNECTOR_X_MAX - CONNECTOR_X_MIN
    right_len = CONNECTOR_Y_MAX - CONNECTOR_Y_MIN
    total_len = left_len + top_len + right_len
    u_corner_lo = left_len / total_len
    u_corner_hi = (left_len + top_len) / total_len

    u_list = [i / CONNECTOR_MORPH_SEGMENTS for i in range(CONNECTOR_MORPH_SEGMENTS + 1)]
    u_list += [u_corner_lo, u_corner_hi]
    u_list = sorted(set(u_list))
    P = len(u_list)

    verts = []
    for z in z_levels:
        s = (z - CONNECTOR_Z_BOTTOM) / (CONNECTOR_Z_MORPH_END - CONNECTOR_Z_BOTTOM)
        s = max(0.0, min(1.0, s))
        for u in u_list:
            cx, cy = _connector_semicircle_point(u)
            rx, ry = _connector_rect_point(u)
            x = cx + (rx - cx) * s
            y = cy + (ry - cy) * s
            verts.append((mm(x), mm(y), mm(z)))

    faces = []
    n_rings = len(z_levels)
    for k in range(n_rings - 1):
        base0 = k * P
        base1 = (k + 1) * P
        for j in range(P):
            j2 = (j + 1) % P
            faces.append((base0 + j, base0 + j2, base1 + j2, base1 + j))

    # 底面(z=CONNECTOR_Z_BOTTOM)と上面(z=CONNECTOR_Z_TOP)のキャップ
    bottom_ring = tuple(range(P))
    top_ring = tuple((n_rings - 1) * P + j for j in range(P))
    faces.append(tuple(reversed(bottom_ring)))
    faces.append(top_ring)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    # PIPE_INNER_D のシリンダーでカットしてパイプ内側と干渉しないようにする
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(PIPE_INNER_D / 2),
        depth=mm((CONNECTOR_Z_TOP - CONNECTOR_Z_BOTTOM) + 20),
        location=(
            mm(PIPE_CENTER_X),
            mm(PIPE_CENTER_Y),
            mm((CONNECTOR_Z_BOTTOM + CONNECTOR_Z_TOP) / 2),
        ),
        vertices=CYLINDER_VERTICES_PIPE,
    )
    cutter = bpy.context.active_object
    boolean_op(obj, cutter, 'DIFFERENCE')

    return obj


def make_bracketA():
    mat = make_material("mat_bracketA", (0.4, 0.7, 0.9, 1.0))

    parent = bpy.data.objects.new("bracketA", None)
    bpy.context.collection.objects.link(parent)

    make_pipe_half("bracketA_pipe", parent, mat, 'A')

    make_bracketA_connector("bracketA_connector", parent, mat)

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

    make_plate_connector_fillet(
        "bracketA_plate_connector_fillet_R",
        parent,
        mat,
        'R'
    )

    make_plate_connector_fillet(
        "bracketA_plate_connector_fillet_L",
        parent,
        mat,
        'L'
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


clear_scene()
monitor_plate = make_monitor_plate()
monitor_plate.location.z += mm(PLATE_Z_OFFSET)
bracketA = make_bracketA()
bracketB = make_bracketB()