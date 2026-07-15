import bpy
import bmesh
import math

# =========================
# 共通単位
# =========================
MM = 0.001


# =========================
# board / bracket / base / parts 定数
# =========================
BOARD_WIDTH = 94 * MM
BOARD_HEIGHT = 59 * MM
BOARD_THICKNESS = 1.6 * MM

CLEARANCE_X = 0.1 * MM
CLEARANCE_Y = 0.2 * MM

BRACKET_LEG_X = 10 * MM
BRACKET_LEG_Z = 10 * MM
BRACKET_THICKNESS = 2 * MM
WALL_THICKNESS = 2 * MM

BASE_WIDTH = 100 * MM
BASE_THICKNESS = 2.4 * MM

PARTS_WIDTH = 80 * MM
PARTS_Z_MIN = 6 * MM
PARTS_Z_MAX = 57 * MM
PARTS_Y_MIN = -5 * MM
PARTS_Y_MAX = 20 * MM


# =========================
# male / female / connector 定数
# =========================
female_width = 24 * MM
female_y_min_base = 0 * MM
female_y_max = 18 * MM
body_width = female_width
body_y_min = -20 * MM
body_y_max = 0 * MM
neck_width = 12 * MM
neck_y_min = 0 * MM
neck_y_max = 8 * MM
head_width = 18 * MM
head_y_min = neck_y_max
head_y_max = 13 * MM
x_clearance = 0.3 * MM
y_clearance = 0.3 * MM
female_y_min = female_y_min_base + y_clearance
r_fillet = 1.5 * MM
r_chamfer = 1.0 * MM
model_z_top = 20 * MM
female_top_thickness = 3 * MM
male_z_start = 0.0
male_extrude_height = model_z_top - male_z_start
female_wall_z_start = 0.0
female_wall_extrude_height = model_z_top
female_top_z_start = female_wall_z_start + female_wall_extrude_height
female_top_extrude_height = female_top_thickness
boolean_cut_margin = 1 * MM
arc_segments = 16
female_enable_rounding = True
connector_depth = 10 * MM
male_color = (0.1, 0.35, 1.0, 1.0)
female_wall_color = (1.0, 0.45, 0.1, 1.0)
female_top_color = (0.2, 0.8, 0.35, 1.0)
connector_color = (0.7, 0.7, 0.2, 1.0)
body_upper_height = 20 * MM

# =========================
# 全体オフセット
# =========================
Y_OFFSET = (female_y_max + connector_depth) - PARTS_Y_MIN
Z_OFFSET = BASE_THICKNESS


# =========================
# bracketA / bracketB 定数
# =========================
CYLINDER_VERTICES_PIPE = 96
CYLINDER_VERTICES_HOLE = 32
CYLINDER_VERTICES_NUT = 6
FLANGE_ROUND_SEGMENTS = 16
FILLET_SEGMENTS = 8

PIPE_CENTER_X = 0 * MM
PIPE_CENTER_Y = -24 * MM
PIPE_Z_MIN = 0 * MM
PIPE_Z_MAX = 56 * MM
PIPE_HEIGHT = PIPE_Z_MAX - PIPE_Z_MIN
PIPE_CENTER_Z = (PIPE_Z_MIN + PIPE_Z_MAX) / 2

PIPE_OUTER_D = 34 * MM
PIPE_INNER_D = 28 * MM
PIPE_OUTER_R = PIPE_OUTER_D / 2
PIPE_INNER_R = PIPE_INNER_D / 2

PIPE_A_Y_MIN = PIPE_CENTER_Y
PIPE_A_Y_MAX = 30 * MM
PIPE_B_Y_MIN = -80 * MM
PIPE_B_Y_MAX = PIPE_CENTER_Y

PIPE_HALF_CUTTER_X_SIZE = 100 * MM
PIPE_HALF_CUTTER_Z_SIZE = PIPE_HEIGHT + 10 * MM
PIPE_INNER_CUTTER_DEPTH = 60 * MM

FLANGE_Z_MIN = 0 * MM
FLANGE_Z_MAX = 20 * MM
FLANGE_Z_CENTER = 10 * MM

FLANGE_INNER_X = 13.5 * MM
FLANGE_ROUND_CENTER_X = 21 * MM
FLANGE_ROUND_R = 10 * MM

BRACKET_A_FLANGE_Y_MIN = -24 * MM
BRACKET_A_FLANGE_Y_MAX = -22 * MM

BRACKET_B_FLANGE_Y_MIN = -28 * MM
BRACKET_B_FLANGE_Y_MAX = -24 * MM

FLANGE_PIPE_FILLET_R = 2.0 * MM

FLANGE_HOLE_X = 23 * MM
FLANGE_HOLE_D = 5 * MM
SCREW_HOLE_EXTRA_DEPTH = 4 * MM

M4_NUT_FLAT_TO_FLAT = 7.4 * MM
M4_NUT_DEPTH = 3 * MM
NUT_POCKET_OVER_CUT = 0.3 * MM

# =========================
# 共通ユーティリティ
# =========================
def clear_all():
    for obj in bpy.data.objects:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.001
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"


def make_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = color
    return mat


def add_mesh_object(name, verts, faces, material):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    return obj


def extrude_profile_y(name, profile_xz, y_min, y_max, material):
    n = len(profile_xz)
    verts = [(x, y_min, z) for x, z in profile_xz] + [(x, y_max, z) for x, z in profile_xz]
    faces = [tuple(range(n)), tuple(range(n, 2 * n))[::-1]]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    return add_mesh_object(name, verts, faces, material)


def create_prism_from_profile(points, name, height, z_start=0.0, material=None):
    n = len(points)
    verts = [(x, y, z_start) for x, y in points] + [(x, y, z_start + height) for x, y in points]
    faces = [list(range(n)), list(range(n, n * 2))[::-1]]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, j + n, i + n])
    return add_mesh_object(name, verts, faces, material)


def arc_points(cx, cy, rx, ry, start_deg, end_deg, segments=arc_segments):
    pts = []
    for i in range(segments + 1):
        t = i / segments
        a = math.radians(start_deg + (end_deg - start_deg) * t)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts


def apply_boolean_difference(target, cutter):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    mod = target.modifiers.new("female_cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


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
    sx = x_max - x_min
    sy = y_max - y_min
    sz = z_max - z_min
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    cz = (z_min + z_max) / 2
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
    n = len(verts_xz)
    verts = [(x, y_min, z) for x, z in verts_xz]
    verts += [(x, y_max, z) for x, z in verts_xz]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
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
    n = len(verts_xy)
    verts = [(x, y, z_min) for x, y in verts_xy]
    verts += [(x, y, z_max) for x, y in verts_xy]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
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
# board / bracket / base / parts 生成
# =========================
def bracket_y_range():
    y_near_max = -CLEARANCE_Y
    y_near_min = y_near_max - BRACKET_THICKNESS
    y_far_min = BOARD_THICKNESS + CLEARANCE_Y
    y_far_max = y_far_min + BRACKET_THICKNESS
    return y_near_min, y_near_max, y_far_min, y_far_max


def create_board():
    profile = [
        (-BOARD_WIDTH / 2, 0),
        ( BOARD_WIDTH / 2, 0),
        ( BOARD_WIDTH / 2, BOARD_HEIGHT),
        (-BOARD_WIDTH / 2, BOARD_HEIGHT),
    ]
    mat = make_material("board_mat", (0.0, 0.6, 0.0, 1.0))
    return extrude_profile_y("board", profile, 0.0, BOARD_THICKNESS, mat)


def create_bracket():
    mat = make_material("bracket_mat", (0.8, 0.5, 0.1, 1.0))
    x_edge = BOARD_WIDTH / 2 + CLEARANCE_X

    tri_left = [
        (-x_edge, 0),
        (-x_edge, BRACKET_LEG_Z),
        (-x_edge + BRACKET_LEG_X, 0),
    ]
    tri_right = [
        ( x_edge, 0),
        ( x_edge - BRACKET_LEG_X, 0),
        ( x_edge, BRACKET_LEG_Z),
    ]

    y_near_min, y_near_max, y_far_min, y_far_max = bracket_y_range()

    parts = [
        extrude_profile_y("bracket_tri_L_near", tri_left,  y_near_min, y_near_max, mat),
        extrude_profile_y("bracket_tri_R_near", tri_right, y_near_min, y_near_max, mat),
        extrude_profile_y("bracket_tri_L_far",  tri_left,  y_far_min,  y_far_max,  mat),
        extrude_profile_y("bracket_tri_R_far",  tri_right, y_far_min,  y_far_max,  mat),
    ]

    wall_left = [
        (-x_edge - WALL_THICKNESS, 0),
        (-x_edge,                  0),
        (-x_edge,                  BRACKET_LEG_Z),
        (-x_edge - WALL_THICKNESS, BRACKET_LEG_Z),
    ]
    wall_right = [
        ( x_edge,                  0),
        ( x_edge + WALL_THICKNESS, 0),
        ( x_edge + WALL_THICKNESS, BRACKET_LEG_Z),
        ( x_edge,                  BRACKET_LEG_Z),
    ]

    parts.append(extrude_profile_y("bracket_wall_L", wall_left,  y_near_min, y_far_max, mat))
    parts.append(extrude_profile_y("bracket_wall_R", wall_right, y_near_min, y_far_max, mat))

    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = "bracket"
    joined.data.name = "bracket_mesh"
    return joined


def create_base():
    mat = make_material("base_mat", (0.2, 0.4, 0.8, 1.0))
    _, _, _, y_far_max = bracket_y_range()
    profile = [
        (-BASE_WIDTH / 2, -BASE_THICKNESS),
        ( BASE_WIDTH / 2, -BASE_THICKNESS),
        ( BASE_WIDTH / 2, 0),
        (-BASE_WIDTH / 2, 0),
    ]
    return extrude_profile_y("base", profile, PARTS_Y_MIN, y_far_max, mat)


def create_parts():
    mat = make_material("parts_mat", (0.1, 0.4, 0.15, 1.0))
    profile = [
        (-PARTS_WIDTH / 2, PARTS_Z_MIN),
        ( PARTS_WIDTH / 2, PARTS_Z_MIN),
        ( PARTS_WIDTH / 2, PARTS_Z_MAX),
        (-PARTS_WIDTH / 2, PARTS_Z_MAX),
    ]
    return extrude_profile_y("parts", profile, PARTS_Y_MIN, PARTS_Y_MAX, mat)


# =========================
# male / female 生成
# =========================
def build_male_profile():
    bx = body_width / 2
    nx = neck_width / 2
    hx = head_width / 2
    pts = []
    pts.append((-bx, body_y_min))
    pts.append((bx, body_y_min))
    pts.append((bx, body_y_max))
    pts.append((nx + r_fillet, body_y_max))
    pts.extend(arc_points(nx + r_fillet, body_y_max + r_fillet, r_fillet, r_fillet, -90, -180)[1:])
    pts.append((nx, head_y_min - r_fillet))
    pts.extend(arc_points(nx + r_fillet, head_y_min - r_fillet, r_fillet, r_fillet, 180, 90)[1:])
    pts.append((hx - r_chamfer, head_y_min))
    pts.extend(arc_points(hx - r_chamfer, head_y_min + r_chamfer, r_chamfer, r_chamfer, -90, 0)[1:])
    pts.append((hx, head_y_max - r_chamfer))
    pts.extend(arc_points(hx - r_chamfer, head_y_max - r_chamfer, r_chamfer, r_chamfer, 0, 90)[1:])
    pts.append((-hx + r_chamfer, head_y_max))
    pts.extend(arc_points(-hx + r_chamfer, head_y_max - r_chamfer, r_chamfer, r_chamfer, 90, 180)[1:])
    pts.append((-hx, head_y_min + r_chamfer))
    pts.extend(arc_points(-hx + r_chamfer, head_y_min + r_chamfer, r_chamfer, r_chamfer, 180, 270)[1:])
    pts.append((-nx - r_fillet, head_y_min))
    pts.extend(arc_points(-nx - r_fillet, head_y_min - r_fillet, r_fillet, r_fillet, 90, 0)[1:])
    pts.append((-nx, body_y_max + r_fillet))
    pts.extend(arc_points(-nx - r_fillet, body_y_max + r_fillet, r_fillet, r_fillet, 0, -90)[1:])
    pts.append((-bx, body_y_max))
    return pts


def build_female_outer_profile():
    fx = female_width / 2
    return [
        (-fx, female_y_min),
        (fx, female_y_min),
        (fx, female_y_max),
        (-fx, female_y_max),
    ]


def build_female_cut_profile(enable_rounding=False):
    nx = neck_width / 2 + x_clearance
    hx = head_width / 2 + x_clearance
    y_neck_bottom = neck_y_min - y_clearance
    y_head_bottom = head_y_min - y_clearance
    y_head_top = head_y_max + y_clearance

    if not enable_rounding:
        return [
            (-nx, y_neck_bottom),
            (nx, y_neck_bottom),
            (nx, y_head_bottom),
            (hx, y_head_bottom),
            (hx, y_head_top),
            (-hx, y_head_top),
            (-hx, y_head_bottom),
            (-nx, y_head_bottom),
        ]

    r_nb = r_chamfer
    r_nh = r_chamfer
    r_h = r_fillet
    y_nb_center = neck_y_min + r_fillet
    y_nb_arc_start = y_nb_center - r_nb

    pts = []
    pts.append((-nx - r_nb, y_neck_bottom))
    pts.append((nx + r_nb, y_neck_bottom))
    pts.append((nx + r_nb, y_nb_arc_start))
    pts.extend(arc_points(nx + r_nb, y_nb_center, r_nb, r_nb, -90, -180)[1:])
    pts.append((nx, y_head_bottom - r_nh))
    pts.extend(arc_points(nx + r_nh, y_head_bottom - r_nh, r_nh, r_nh, 180, 90)[1:])
    pts.append((hx - r_h, y_head_bottom))
    pts.extend(arc_points(hx - r_h, y_head_bottom + r_h, r_h, r_h, -90, 0)[1:])
    pts.append((hx, y_head_top - r_h))
    pts.extend(arc_points(hx - r_h, y_head_top - r_h, r_h, r_h, 0, 90)[1:])
    pts.append((-hx + r_h, y_head_top))
    pts.extend(arc_points(-hx + r_h, y_head_top - r_h, r_h, r_h, 90, 180)[1:])
    pts.append((-hx, y_head_bottom + r_h))
    pts.extend(arc_points(-hx + r_h, y_head_bottom + r_h, r_h, r_h, 180, 270)[1:])
    pts.append((-nx - r_nh, y_head_bottom))
    pts.extend(arc_points(-nx - r_nh, y_head_bottom - r_nh, r_nh, r_nh, 90, 0)[1:])
    pts.append((-nx, y_nb_center))
    pts.extend(arc_points(-nx - r_nb, y_nb_center, r_nb, r_nb, 0, -90)[1:])
    pts.append((-nx - r_nb, y_neck_bottom))
    return pts


def create_male():
    mat = make_material("male_blue", male_color)
    profile = build_male_profile()
    male_obj = create_prism_from_profile(profile, "male", male_extrude_height, male_z_start, mat)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=PIPE_INNER_D / 2,
        depth=male_extrude_height + 10 * MM,
        location=(PIPE_CENTER_X, PIPE_CENTER_Y, male_z_start + male_extrude_height / 2),
        vertices=CYLINDER_VERTICES_PIPE,
    )
    cutter = bpy.context.active_object
    boolean_op(male_obj, cutter, 'DIFFERENCE')
    return male_obj

def create_female_wall():
    mat = make_material("female_wall_orange", female_wall_color)
    outer_profile = build_female_outer_profile()
    cut_profile = build_female_cut_profile(enable_rounding=female_enable_rounding)
    wall = create_prism_from_profile(outer_profile, "female_wall", female_wall_extrude_height, female_wall_z_start, mat)
    cutter = create_prism_from_profile(cut_profile, "female_cut_through", female_wall_extrude_height + 2 * boolean_cut_margin, female_wall_z_start - boolean_cut_margin, None)
    apply_boolean_difference(wall, cutter)
    return wall


def create_female_top():
    mat = make_material("female_top_green", female_top_color)
    outer_profile = build_female_outer_profile()
    return create_prism_from_profile(outer_profile, "female_top", female_top_extrude_height, female_top_z_start, mat)

def create_connector():
    mat = make_material("connector_mat", connector_color)
    profile_xy = [
        (-female_width / 2, female_y_max),
        ( female_width / 2, female_y_max),
        ( BASE_WIDTH / 2,   female_y_max + connector_depth),
        (-BASE_WIDTH / 2,   female_y_max + connector_depth),
    ]
    return add_prism_xy("connector", None, mat, profile_xy, 0.0, model_z_top + female_top_thickness)

def create_body_upper():
    mat = make_material("body_upper_mat", (0.3, 0.6, 0.9, 1.0))

    profile_yz = [
        (body_y_min, model_z_top),
        (body_y_max, model_z_top),
        (body_y_min, model_z_top + body_upper_height),
    ]

    n = len(profile_yz)
    x_min = -body_width / 2
    x_max =  body_width / 2
    verts = [(x_min, y, z) for y, z in profile_yz] + [(x_max, y, z) for y, z in profile_yz]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))

    obj = add_mesh_object("body_upper", verts, faces, mat)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=PIPE_INNER_D / 2,
        depth=body_upper_height + 10 * MM,
        location=(PIPE_CENTER_X, PIPE_CENTER_Y, model_z_top + body_upper_height / 2),
        vertices=CYLINDER_VERTICES_PIPE,
    )
    cutter = bpy.context.active_object
    boolean_op(obj, cutter, 'DIFFERENCE')
    return obj

# =========================
# pipe
# =========================
def make_pipe_half(name, parent, material, side):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=PIPE_OUTER_R,
        depth=PIPE_HEIGHT,
        location=(PIPE_CENTER_X, PIPE_CENTER_Y, PIPE_CENTER_Z),
        vertices=CYLINDER_VERTICES_PIPE
    )
    pipe = bpy.context.active_object
    pipe.name = name

    bpy.ops.mesh.primitive_cylinder_add(
        radius=PIPE_INNER_R,
        depth=PIPE_HEIGHT + 10 * MM,
        location=(PIPE_CENTER_X, PIPE_CENTER_Y, PIPE_CENTER_Z),
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
        location=(PIPE_CENTER_X, (y_min + y_max) / 2, PIPE_CENTER_Z)
    )
    cutter = bpy.context.active_object
    cutter.scale = (PIPE_HALF_CUTTER_X_SIZE, y_max - y_min, PIPE_HALF_CUTTER_Z_SIZE)
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
        radius=diameter / 2,
        depth=(y_max - y_min) + SCREW_HOLE_EXTRA_DEPTH,
        location=(x, (y_min + y_max) / 2, z),
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
        radius=r,
        depth=y1 - y0,
        location=(x, (y0 + y1) / 2, z),
        rotation=(math.pi / 2, 0, 0)
    )
    pocket = bpy.context.active_object
    pocket.name = "m4_nut_pocket_cutter"
    pocket.data.materials.append(material)
    boolean_op(target, pocket, 'DIFFERENCE')


def cut_pipe_inner_void_z(target):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=PIPE_INNER_R,
        depth=PIPE_INNER_CUTTER_DEPTH,
        location=(PIPE_CENTER_X, PIPE_CENTER_Y, PIPE_CENTER_Z),
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

    bpy.ops.mesh.primitive_cylinder_add(
        radius=PIPE_INNER_D / 2,
        depth=(FLANGE_Z_MAX - FLANGE_Z_MIN) + 10 * MM,
        location=(PIPE_CENTER_X, PIPE_CENTER_Y, FLANGE_Z_CENTER),
        vertices=CYLINDER_VERTICES_PIPE,
    )
    inner_cutter = bpy.context.active_object
    boolean_op(flange, inner_cutter, 'DIFFERENCE')

    if nut_pocket:
        if pocket_outer_side == "min":
            add_m4_nut_pocket_y(flange, hole_x, y_min, "plus_y", FLANGE_Z_CENTER, material)
        else:
            add_m4_nut_pocket_y(flange, hole_x, y_max, "minus_y", FLANGE_Z_CENTER, material)

    add_screw_hole_y(flange, hole_x, y_min, y_max, FLANGE_Z_CENTER, FLANGE_HOLE_D)

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
    fillet = add_prism_xy(name, None, material, verts_xy, FLANGE_Z_MIN, FLANGE_Z_MAX)
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

    make_flange_half("bracketA_flange_R", parent, mat,
                     BRACKET_A_FLANGE_Y_MIN, BRACKET_A_FLANGE_Y_MAX, 'R', nut_pocket=False)
    make_flange_half("bracketA_flange_L", parent, mat,
                     BRACKET_A_FLANGE_Y_MIN, BRACKET_A_FLANGE_Y_MAX, 'L', nut_pocket=False)

    make_pipe_flange_fillet("bracketA_fillet_R", parent, mat, 'R',
                            BRACKET_A_FLANGE_Y_MAX, "plus_y")
    make_pipe_flange_fillet("bracketA_fillet_L", parent, mat, 'L',
                            BRACKET_A_FLANGE_Y_MAX, "plus_y")

    return parent


def make_bracketB():
    mat = make_material("mat_bracketB", (0.9, 0.5, 0.4, 1.0))
    parent = bpy.data.objects.new("bracketB", None)
    bpy.context.collection.objects.link(parent)

    make_pipe_half("bracketB_pipe", parent, mat, 'B')

    make_flange_half("bracketB_flange_R", parent, mat,
                     BRACKET_B_FLANGE_Y_MIN, BRACKET_B_FLANGE_Y_MAX, 'R',
                     nut_pocket=True, pocket_outer_side="min")
    make_flange_half("bracketB_flange_L", parent, mat,
                     BRACKET_B_FLANGE_Y_MIN, BRACKET_B_FLANGE_Y_MAX, 'L',
                     nut_pocket=True, pocket_outer_side="min")

    make_pipe_flange_fillet("bracketB_fillet_R", parent, mat, 'R',
                            BRACKET_B_FLANGE_Y_MIN, "minus_y")
    make_pipe_flange_fillet("bracketB_fillet_L", parent, mat, 'L',
                            BRACKET_B_FLANGE_Y_MIN, "minus_y")

    return parent


# =========================
# main
# =========================
def main():
    clear_all()
    objs = [create_board(), create_bracket(), create_base(), create_parts()]
    for obj in objs:
        obj.location.y += Y_OFFSET
        obj.location.z += Z_OFFSET
    create_male()
    create_female_wall()
    create_female_top()
    create_connector()
    create_body_upper()
    make_bracketA()
    make_bracketB()


main()