import bpy
import math

MM = 0.001
body_width = 50 * MM
body_y_min = -20 * MM
body_y_max = 0 * MM
neck_width = 12 * MM
neck_y_min = 0 * MM
neck_y_max = 8 * MM
head_width = 18 * MM
head_y_min = neck_y_max
head_y_max = 13 * MM
female_width = 24 * MM
female_y_min_base = 0 * MM
female_y_max = 18 * MM
x_clearance = 0.3 * MM
y_clearance = 0.3 * MM
female_y_min = female_y_min_base + y_clearance
r_fillet = 1.5 * MM
r_chamfer = 1.0 * MM
model_z_top = 20 * MM
female_bottom_thickness = 3 * MM
male_z_start = female_bottom_thickness
male_extrude_height = model_z_top - male_z_start
female_wall_z_start = female_bottom_thickness
female_wall_extrude_height = model_z_top - female_wall_z_start
female_bottom_z_start = 0.0
female_bottom_extrude_height = female_bottom_thickness
boolean_cut_margin = 1 * MM
arc_segments = 16
female_enable_rounding = True
male_color = (0.1, 0.35, 1.0, 1.0)
female_wall_color = (1.0, 0.45, 0.1, 1.0)
female_bottom_color = (0.2, 0.8, 0.35, 1.0)


def clear_scene():
    for obj in bpy.data.objects:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.001
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"


def make_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def arc_points(cx, cy, rx, ry, start_deg, end_deg, segments=arc_segments):
    pts = []
    for i in range(segments + 1):
        t = i / segments
        a = math.radians(start_deg + (end_deg - start_deg) * t)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts


def create_prism_from_profile(points, name, height, z_start=0.0, material=None):
    verts = []
    faces = []
    n = len(points)

    for x, y in points:
        verts.append((x, y, z_start))
    for x, y in points:
        verts.append((x, y, z_start + height))

    faces.append(list(range(n)))
    faces.append(list(range(n, n * 2))[::-1])

    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, j + n, i + n])

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    if material:
        obj.data.materials.append(material)

    return obj


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


def build_female_cut_profile(female_enable_rounding=False):
    nx = neck_width / 2 + x_clearance
    hx = head_width / 2 + x_clearance
    y_neck_bottom = neck_y_min - y_clearance
    y_head_bottom = head_y_min - y_clearance
    y_head_top = head_y_max + y_clearance

    if not female_enable_rounding:
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

    r_neck_body_chamfer = r_chamfer
    r_neck_head_chamfer = r_chamfer
    r_head_fillet = r_fillet
    y_neck_body_center = neck_y_min + r_fillet
    y_neck_body_arc_start = y_neck_body_center - r_neck_body_chamfer

    pts = []

    pts.append((-nx - r_neck_body_chamfer, y_neck_bottom))
    pts.append((nx + r_neck_body_chamfer, y_neck_bottom))
    pts.append((nx + r_neck_body_chamfer, y_neck_body_arc_start))
    pts.extend(arc_points(nx + r_neck_body_chamfer, y_neck_body_center, r_neck_body_chamfer, r_neck_body_chamfer, -90, -180)[1:])

    pts.append((nx, y_head_bottom - r_neck_head_chamfer))
    pts.extend(arc_points(nx + r_neck_head_chamfer, y_head_bottom - r_neck_head_chamfer, r_neck_head_chamfer, r_neck_head_chamfer, 180, 90)[1:])

    pts.append((hx - r_head_fillet, y_head_bottom))
    pts.extend(arc_points(hx - r_head_fillet, y_head_bottom + r_head_fillet, r_head_fillet, r_head_fillet, -90, 0)[1:])

    pts.append((hx, y_head_top - r_head_fillet))
    pts.extend(arc_points(hx - r_head_fillet, y_head_top - r_head_fillet, r_head_fillet, r_head_fillet, 0, 90)[1:])

    pts.append((-hx + r_head_fillet, y_head_top))
    pts.extend(arc_points(-hx + r_head_fillet, y_head_top - r_head_fillet, r_head_fillet, r_head_fillet, 90, 180)[1:])

    pts.append((-hx, y_head_bottom + r_head_fillet))
    pts.extend(arc_points(-hx + r_head_fillet, y_head_bottom + r_head_fillet, r_head_fillet, r_head_fillet, 180, 270)[1:])

    pts.append((-nx - r_neck_head_chamfer, y_head_bottom))
    pts.extend(arc_points(-nx - r_neck_head_chamfer, y_head_bottom - r_neck_head_chamfer, r_neck_head_chamfer, r_neck_head_chamfer, 90, 0)[1:])

    pts.append((-nx, y_neck_body_center))
    pts.extend(arc_points(-nx - r_neck_body_chamfer, y_neck_body_center, r_neck_body_chamfer, r_neck_body_chamfer, 0, -90)[1:])

    pts.append((-nx - r_neck_body_chamfer, y_neck_bottom))
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


def make_male(material):
    profile = build_male_profile()
    return create_prism_from_profile(profile, "male", male_extrude_height, male_z_start, material)


def make_female_wall(material):
    outer_profile = build_female_outer_profile()
    cut_profile = build_female_cut_profile(female_enable_rounding=female_enable_rounding)

    wall = create_prism_from_profile(outer_profile, "female_wall", female_wall_extrude_height, female_wall_z_start, material)
    cutter = create_prism_from_profile(cut_profile, "female_cut_through", female_wall_extrude_height + 2 * boolean_cut_margin, female_wall_z_start - boolean_cut_margin, None)

    apply_boolean_difference(wall, cutter)
    return wall


def make_female_bottom(material):
    outer_profile = build_female_outer_profile()
    return create_prism_from_profile(outer_profile, "female_bottom", female_bottom_extrude_height, female_bottom_z_start, material)


def main():
    clear_scene()

    male_mat = make_material("male_blue", male_color)
    female_wall_mat = make_material("female_wall_orange", female_wall_color)
    female_bottom_mat = make_material("female_bottom_green", female_bottom_color)

    make_male(male_mat)
    make_female_wall(female_wall_mat)
    make_female_bottom(female_bottom_mat)


main()