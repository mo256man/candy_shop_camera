import bpy
import bmesh
import math


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
MONITOR_X_MIN = -92
MONITOR_X_MAX = 92
MONITOR_Y_MIN = 0
MONITOR_Y_MAX = 24
MONITOR_Z_MIN = 0
MONITOR_Z_MAX = 101

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
PIPE_Z_MAX = 40
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
PIPE_HALF_CUTTER_Z_SIZE = 70
PIPE_INNER_CUTTER_DEPTH = 60

# bracketA connector
BRACKET_A_CONNECTOR_Y_START = BASE_PLATE_7_Y_MIN
BRACKET_A_CONNECTOR_HALF_WIDTH_START = 6
BRACKET_A_CONNECTOR_Z_MIN = 0
BRACKET_A_CONNECTOR_Z_MAX = 40

# bracketA connector cutter (yz平面の直角三角形をx軸方向に押し出し)
BRACKET_A_CONNECTOR_CUT_Y_PLATE = BRACKET_A_CONNECTOR_Y_START
BRACKET_A_CONNECTOR_CUT_Y_PIPE = PIPE_CENTER_Y + PIPE_OUTER_R
BRACKET_A_CONNECTOR_CUT_Z = 6
BRACKET_A_CONNECTOR_CUT_X_HALF = 100
BRACKET_A_CONNECTOR_CUT_MARGIN = 1

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

# board
BOARD_WIDTH = 20
BOARD_HEIGHT = 80
BOARD_THICKNESS = 10
BOARD_Y_MIN = 0
BOARD_Y_MAX = 10
BOARD_X_MIN = -10
BOARD_X_MAX = 10
BOARD_Z_MIN = 0
BOARD_Z_MAX = 80
BOARD_HOLE_D = 2.2
BOARD_HOLE_EDGE_OFFSET = 2
BOARD_HOLE_X = [BOARD_X_MIN + BOARD_HOLE_EDGE_OFFSET, BOARD_X_MAX - BOARD_HOLE_EDGE_OFFSET]
BOARD_HOLE_Z = [BOARD_Z_MIN + BOARD_HOLE_EDGE_OFFSET, BOARD_Z_MAX - BOARD_HOLE_EDGE_OFFSET]

# box
BOX_WALL_THICKNESS = 2
BOX_WALL_HEIGHT = 10
BOX_CLEARANCE = 0.2
BOX_Y_MIN = -2
BOX_Y_MAX = 10
BOX_X_MIN = -12.1
BOX_X_MAX = 12.1
BOX_Z_MIN = -2.1
BOX_Z_MAX = 82.1
BOX_HOLE_D = 2.2
# ボードの穴と同じXZ座標
BOX_HOLE_X = [BOARD_X_MIN + BOARD_HOLE_EDGE_OFFSET, BOARD_X_MAX - BOARD_HOLE_EDGE_OFFSET]
BOX_HOLE_Z = [BOARD_Z_MIN + BOARD_HOLE_EDGE_OFFSET, BOARD_Z_MAX - BOARD_HOLE_EDGE_OFFSET]

# bracketA plate
PLATE_THICKNESS = 2
BRACKET_A_PLATE_Y_MIN = -1
BRACKET_A_PLATE_Y_MAX = 1

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


def boolean_op(target, cutter, op):
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active = target

    mod = target.modifiers.new(name="bool", type='BOOLEAN')
    mod.operation = op
    mod.object = cutter
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier="bool")

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


# =========================
# monitor / base
# =========================

def make_board():
    mat = make_material("mat_board", (0.0, 0.8, 0.0, 1.0))
    board = add_box(
        "board",
        None,
        mat,
        BOARD_X_MIN,
        BOARD_X_MAX,
        BOARD_Y_MIN,
        BOARD_Y_MAX,
        BOARD_Z_MIN,
        BOARD_Z_MAX
    )

    # 四隅のy方向貫通穴
    for x in BOARD_HOLE_X:
        for z in BOARD_HOLE_Z:
            bpy.ops.mesh.primitive_cylinder_add(
                radius=mm(BOARD_HOLE_D / 2),
                depth=mm(BOARD_Y_MAX - BOARD_Y_MIN + SCREW_HOLE_EXTRA_DEPTH),
                location=(mm(x), mm((BOARD_Y_MIN + BOARD_Y_MAX) / 2), mm(z)),
                rotation=(math.pi / 2, 0, 0),
                vertices=CYLINDER_VERTICES_HOLE
            )
            hole = bpy.context.active_object
            boolean_op(board, hole, 'DIFFERENCE')

    hide_all_recursively(board)
    return board


def make_box():
    mat = make_material("mat_box", (0.3, 0.3, 0.3, 1.0))

    box = bpy.data.objects.new("box", None)
    bpy.context.collection.objects.link(box)

    # 底面（xz平面、厚さ2mm）
    box_bottom = add_box(
        "box_bottom",
        box,
        mat,
        BOX_X_MIN,
        BOX_X_MAX,
        BOX_Y_MIN,
        BOX_Y_MIN + BOX_WALL_THICKNESS,
        BOX_Z_MIN,
        BOX_Z_MAX
    )

    # 底面の四隅のy方向貫通穴
    for x in BOX_HOLE_X:
        for z in BOX_HOLE_Z:
            bpy.ops.mesh.primitive_cylinder_add(
                radius=mm(BOX_HOLE_D / 2),
                depth=mm(BOX_WALL_THICKNESS + SCREW_HOLE_EXTRA_DEPTH),
                location=(mm(x), mm((BOX_Y_MIN + BOX_Y_MIN + BOX_WALL_THICKNESS) / 2), mm(z)),
                rotation=(math.pi / 2, 0, 0),
                vertices=CYLINDER_VERTICES_HOLE
            )
            hole = bpy.context.active_object
            boolean_op(box_bottom, hole, 'DIFFERENCE')

    # -x壁（左）
    add_box(
        "box_wall_x_min",
        box,
        mat,
        BOX_X_MIN,
        BOX_X_MIN + BOX_WALL_THICKNESS,
        BOX_Y_MIN + BOX_WALL_THICKNESS,
        BOX_Y_MAX,
        BOX_Z_MIN,
        BOX_Z_MAX
    )

    # +x壁（右）
    add_box(
        "box_wall_x_max",
        box,
        mat,
        BOX_X_MAX - BOX_WALL_THICKNESS,
        BOX_X_MAX,
        BOX_Y_MIN + BOX_WALL_THICKNESS,
        BOX_Y_MAX,
        BOX_Z_MIN,
        BOX_Z_MAX
    )

    # -z壁（手前）
    add_box(
        "box_wall_z_min",
        box,
        mat,
        BOX_X_MIN + BOX_WALL_THICKNESS,
        BOX_X_MAX - BOX_WALL_THICKNESS,
        BOX_Y_MIN + BOX_WALL_THICKNESS,
        BOX_Y_MAX,
        BOX_Z_MIN,
        BOX_Z_MIN + BOX_WALL_THICKNESS
    )

    # +z壁（奥）
    add_box(
        "box_wall_z_max",
        box,
        mat,
        BOX_X_MIN + BOX_WALL_THICKNESS,
        BOX_X_MAX - BOX_WALL_THICKNESS,
        BOX_Y_MIN + BOX_WALL_THICKNESS,
        BOX_Y_MAX,
        BOX_Z_MAX - BOX_WALL_THICKNESS,
        BOX_Z_MAX
    )

    hide_all_recursively(box)
    return box


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


def make_bracketA_connector(name, parent, material):
    tx, ty = tangent_point_from_base_to_pipe(
        BRACKET_A_CONNECTOR_HALF_WIDTH_START,
        BRACKET_A_CONNECTOR_Y_START,
        PIPE_CENTER_X,
        PIPE_CENTER_Y,
        PIPE_OUTER_R
    )

    verts = []
    faces = []

    for j in range(CONNECTOR_SECTIONS):
        t = j / (CONNECTOR_SECTIONS - 1)

        y = BRACKET_A_CONNECTOR_Y_START + (ty - BRACKET_A_CONNECTOR_Y_START) * t
        half_w = BRACKET_A_CONNECTOR_HALF_WIDTH_START + (tx - BRACKET_A_CONNECTOR_HALF_WIDTH_START) * t

        section = [
            (-half_w, y, BRACKET_A_CONNECTOR_Z_MIN),
            (half_w, y, BRACKET_A_CONNECTOR_Z_MIN),
            (half_w, y, BRACKET_A_CONNECTOR_Z_MAX),
            (-half_w, y, BRACKET_A_CONNECTOR_Z_MAX),
        ]

        for x, yy, z in section:
            verts.append((mm(x), mm(yy), mm(z)))

    for j in range(CONNECTOR_SECTIONS - 1):
        a = j * 4
        b = (j + 1) * 4

        faces.append((a + 0, a + 1, b + 1, b + 0))
        faces.append((a + 1, a + 2, b + 2, b + 1))
        faces.append((a + 2, a + 3, b + 3, b + 2))
        faces.append((a + 3, a + 0, b + 0, b + 3))

    faces.append((3, 2, 1, 0))

    last = (CONNECTOR_SECTIONS - 1) * 4
    faces.append((last + 0, last + 1, last + 2, last + 3))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)
    mesh.update()

    conn = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(conn)
    conn.data.materials.append(material)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(PIPE_INNER_R),
        depth=mm(PIPE_INNER_CUTTER_DEPTH),
        location=(mm(PIPE_CENTER_X), mm(PIPE_CENTER_Y), mm(PIPE_CENTER_Z)),
        vertices=CYLINDER_VERTICES_PIPE
    )
    inner_cutter = bpy.context.active_object
    boolean_op(conn, inner_cutter, 'DIFFERENCE')

    # yz平面の直角三角形カッターでx軸に沿って削る
    # 斜辺は仕様の2点を通る直線上に保ちつつ、
    # 底辺(z=0)と高さ辺(y=-1)はconnector面と同一平面にならないようマージン分外側にはみ出す
    m = BRACKET_A_CONNECTOR_CUT_MARGIN
    cut_verts = [
        (BRACKET_A_CONNECTOR_CUT_Y_PLATE + m, BRACKET_A_CONNECTOR_Z_MIN - m),
        (BRACKET_A_CONNECTOR_CUT_Y_PIPE - m, BRACKET_A_CONNECTOR_Z_MIN - m),
        (BRACKET_A_CONNECTOR_CUT_Y_PLATE + m, BRACKET_A_CONNECTOR_CUT_Z + m),
    ]
    connector_cutter = add_prism_yz(
        "bracketA_connector_cutter",
        None,
        material,
        cut_verts,
        -BRACKET_A_CONNECTOR_CUT_X_HALF,
        BRACKET_A_CONNECTOR_CUT_X_HALF
    )
    boolean_op(conn, connector_cutter, 'DIFFERENCE')

    if parent:
        conn.parent = parent

    return conn


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


def make_bracketA_plate(name, parent, material):
    plate = add_box(
        name,
        parent,
        material,
        BOARD_X_MIN,
        BOARD_X_MAX,
        BRACKET_A_PLATE_Y_MIN,
        BRACKET_A_PLATE_Y_MAX,
        BOARD_Z_MIN,
        BOARD_Z_MAX
    )

    # 底面と同じXZ座標の四隅のy方向貫通穴
    for x in BOX_HOLE_X:
        for z in BOX_HOLE_Z:
            bpy.ops.mesh.primitive_cylinder_add(
                radius=mm(BOX_HOLE_D / 2),
                depth=mm(PLATE_THICKNESS + SCREW_HOLE_EXTRA_DEPTH),
                location=(mm(x), mm((BRACKET_A_PLATE_Y_MIN + BRACKET_A_PLATE_Y_MAX) / 2), mm(z)),
                rotation=(math.pi / 2, 0, 0),
                vertices=CYLINDER_VERTICES_HOLE
            )
            hole = bpy.context.active_object
            boolean_op(plate, hole, 'DIFFERENCE')

    return plate


# =========================
# bracket
# =========================

def make_bracketA():
    mat = make_material("mat_bracketA", (0.4, 0.7, 0.9, 1.0))

    parent = bpy.data.objects.new("bracketA", None)
    bpy.context.collection.objects.link(parent)

    make_pipe_half("bracketA_pipe", parent, mat, 'A')
    connector = make_bracketA_connector("bracketA_connector", parent, mat)
    connector.hide_set(False)

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

    make_bracketA_plate(
        "bracketA_plate",
        parent,
        mat
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


# =========================
# 生成
# =========================

make_bracketA()
make_bracketB()
make_board()
make_box()