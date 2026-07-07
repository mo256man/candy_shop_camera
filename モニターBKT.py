import bpy
import math

# 既存モデルを全表示してから全削除
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


def mm(v):
    return v / 1000


def make_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = color
    return mat


def hide_object_tree(obj):
    obj.hide_set(True)
    obj.hide_render = True
    for child in obj.children:
        hide_object_tree(child)


def add_box(name, parent, material, x_min, x_max, y_min, y_max, z_min, z_max):
    sx = mm(x_max - x_min)
    sy = mm(y_max - y_min)
    sz = mm(z_max - z_min)
    cx = mm((x_max + x_min) / 2)
    cy = mm((y_max + y_min) / 2)
    cz = mm((z_max + z_min) / 2)

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

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    return obj


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


def make_rounded_rect_verts_xz(x_min, x_max, z_min, z_max, r, seg=12):
    verts = []

    corners = [
        (x_max - r, z_min + r, -math.pi / 2, 0),
        (x_max - r, z_max - r, 0, math.pi / 2),
        (x_min + r, z_max - r, math.pi / 2, math.pi),
        (x_min + r, z_min + r, math.pi, math.pi * 3 / 2),
    ]

    for cx, cz, a0, a1 in corners:
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            verts.append((cx + r * math.cos(a), cz + r * math.sin(a)))

    return verts


def make_hex_verts_xz_no_horizontal(center_x, center_z, flat_to_flat):
    r = flat_to_flat / math.sqrt(3)
    verts = []

    for i in range(6):
        a = math.radians(30 + i * 60)
        verts.append((
            center_x + r * math.cos(a),
            center_z + r * math.sin(a)
        ))

    return verts


def make_monitor():
    mat = make_material("mat_monitor", (0.1, 0.1, 0.1, 1.0))
    return add_box("monitor", None, mat, -92, 92, 0, 24, 0, 101)


def make_base():
    mat = make_material("mat_base", (0.8, 0.6, 0.3, 1.0))

    base = bpy.data.objects.new("base", None)
    bpy.context.collection.objects.link(base)

    add_box("base_bottom", base, mat, -95, 95, -4, 26, -4, 0)

    add_box("base_wall_front_R_rect", base, mat, 75, 95, 24, 26, 0, 10)
    add_box("base_wall_front_L_rect", base, mat, -95, -75, 24, 26, 0, 10)

    add_prism_xz(
        "base_wall_front_R_slope",
        base,
        mat,
        [(75, 10), (75, 0), (45, 0)],
        24,
        26
    )

    add_prism_xz(
        "base_wall_front_L_slope",
        base,
        mat,
        [(-75, 10), (-45, 0), (-75, 0)],
        24,
        26
    )

    back_wall = add_box("base_wall_back", base, mat, -95, 95, -4, 0, 0, 40)

    hole_verts = make_rounded_rect_verts_xz(-55, -15, 5, 20, 5, seg=12)
    hole_cutter = add_prism_xz(
        "base_wall_back_hole_cutter",
        None,
        mat,
        hole_verts,
        -5,
        1
    )
    boolean_op(back_wall, hole_cutter, 'DIFFERENCE')

    add_box("base_wall_left", base, mat, -95, -93, -4, 26, 0, 10)
    add_box("base_wall_right", base, mat, 93, 95, -4, 26, 0, 10)

    hide_object_tree(base)

    return base


def make_base_small():
    mat = make_material("mat_base_small", (0.2, 0.8, 0.8, 1.0))

    base_small = bpy.data.objects.new("base_small", None)
    bpy.context.collection.objects.link(base_small)

    add_box("base_small_plate_12mm", base_small, mat, -6, 6, 1, 3.8, 0, 44)
    add_box("base_small_plate_7mm", base_small, mat, -3.5, 3.5, -1, 1, 0, 44)

    return base_small


def make_pipe_half(name, parent, material, side):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(15),
        depth=mm(20),
        location=(0, mm(-24), mm(10)),
        vertices=96
    )
    pipe = bpy.context.active_object
    pipe.name = name

    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(14.25),
        depth=mm(30),
        location=(0, mm(-24), mm(10)),
        vertices=96
    )
    inner = bpy.context.active_object
    boolean_op(pipe, inner, 'DIFFERENCE')

    if side == 'A':
        y_min, y_max = -24, 30
    else:
        y_min, y_max = -80, -24

    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(0, mm((y_min + y_max) / 2), mm(10))
    )
    cutter = bpy.context.active_object
    cutter.scale = (mm(80), mm(y_max - y_min), mm(50))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boolean_op(pipe, cutter, 'INTERSECT')

    pipe.data.materials.append(material)

    if parent:
        pipe.parent = parent

    return pipe


def make_connector_original(name, parent, material):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(10),
        depth=mm(20),
        location=(0, mm(-14), mm(10)),
        rotation=(math.pi / 2, 0, 0),
        vertices=64
    )
    conn = bpy.context.active_object
    conn.name = name

    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(15),
        depth=mm(40),
        location=(0, mm(-24), mm(10)),
        vertices=96
    )
    pipe_cutter = bpy.context.active_object
    boolean_op(conn, pipe_cutter, 'DIFFERENCE')

    conn.data.materials.append(material)

    if parent:
        conn.parent = parent

    return conn


def rectangle_point_from_angle(angle, half_w, half_h, center_z):
    c = math.cos(angle)
    s = math.sin(angle)

    tx = half_w / abs(c) if abs(c) > 1e-9 else 1e9
    tz = half_h / abs(s) if abs(s) > 1e-9 else 1e9
    t = min(tx, tz)

    return t * c, center_z + t * s


def make_connector_small(name, parent, material):
    y_start = -1
    y_end = -24

    sections = 18
    verts_per_section = 96

    verts = []
    faces = []

    for j in range(sections):
        t = j / (sections - 1)
        y = y_start + (y_end - y_start) * t

        for i in range(verts_per_section):
            a = 2 * math.pi * i / verts_per_section

            rx, rz = rectangle_point_from_angle(a, 6, 10, 10)
            cx = 10 * math.cos(a)
            cz = 10 + 10 * math.sin(a)

            x = rx * (1 - t) + cx * t
            z = rz * (1 - t) + cz * t

            verts.append((mm(x), mm(y), mm(z)))

    for j in range(sections - 1):
        for i in range(verts_per_section):
            a = j * verts_per_section + i
            b = j * verts_per_section + (i + 1) % verts_per_section
            c = (j + 1) * verts_per_section + (i + 1) % verts_per_section
            d = (j + 1) * verts_per_section + i
            faces.append((a, b, c, d))

    faces.append(tuple(range(verts_per_section - 1, -1, -1)))

    last_start = (sections - 1) * verts_per_section
    faces.append(tuple(range(last_start, last_start + verts_per_section)))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    conn = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(conn)
    conn.data.materials.append(material)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(15),
        depth=mm(40),
        location=(0, mm(-24), mm(10)),
        vertices=96
    )
    pipe_cutter = bpy.context.active_object
    boolean_op(conn, pipe_cutter, 'DIFFERENCE')

    if parent:
        conn.parent = parent

    return conn


def make_reinforcement_rib(parent, material):
    return add_prism_yz(
        "bracketA_reinforcement_rib",
        parent,
        material,
        [
            (-1, 20),
            (-6, 20),
            (-1, 40),
        ],
        -3.5,
        3.5
    )


def add_screw_hole_y(target, x, y_min, y_max, z, diameter):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(diameter / 2),
        depth=mm((y_max - y_min) + 4),
        location=(mm(x), mm((y_min + y_max) / 2), mm(z)),
        rotation=(math.pi / 2, 0, 0),
        vertices=32
    )
    hole = bpy.context.active_object
    boolean_op(target, hole, 'DIFFERENCE')


def add_m4_nut_pocket_y(target, x, y_outer, depth, z, material):
    r = 7.4 / math.sqrt(3)
    y0 = y_outer - depth
    y1 = y_outer + 0.3

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=6,
        radius=mm(r),
        depth=mm(y1 - y0),
        location=(mm(x), mm((y0 + y1) / 2), mm(z)),
        rotation=(math.radians(90), 0, 0)
    )
    pocket = bpy.context.active_object
    pocket.name = "m4_nut_pocket_cutter"
    pocket.data.materials.append(material)

    boolean_op(target, pocket, 'DIFFERENCE')


def cut_pipe_inner_void_z(target):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=mm(14.25),
        depth=mm(30),
        location=(0, mm(-24), mm(10)),
        vertices=96
    )
    cutter = bpy.context.active_object
    boolean_op(target, cutter, 'DIFFERENCE')


def make_flange_verts(side, inner_x):
    seg = 16

    if side == 'R':
        verts = [(inner_x, 0), (21, 0)]

        for i in range(1, seg):
            a = -math.pi / 2 + math.pi * i / seg
            verts.append((21 + 10 * math.cos(a), 10 + 10 * math.sin(a)))

        verts.append((21, 20))
        verts.append((inner_x, 20))

    else:
        verts = [(-inner_x, 20), (-21, 20)]

        for i in range(1, seg):
            a = math.pi / 2 + math.pi * i / seg
            verts.append((-21 + 10 * math.cos(a), 10 + 10 * math.sin(a)))

        verts.append((-21, 0))
        verts.append((-inner_x, 0))

    return verts


def make_flange_half(name, parent, material, y_min, y_max, side, nut_pocket=False):
    inner_x = 13.5
    verts = make_flange_verts(side, inner_x)

    hole_x = 23 if side == 'R' else -23

    flange = add_prism_xz(name, None, material, verts, y_min, y_max)

    cut_pipe_inner_void_z(flange)

    if nut_pocket:
        add_m4_nut_pocket_y(
            target=flange,
            x=hole_x,
            y_outer=y_max,
            depth=3,
            z=10,
            material=material
        )

    add_screw_hole_y(
        target=flange,
        x=hole_x,
        y_min=y_min,
        y_max=y_max,
        z=10,
        diameter=5
    )

    if parent:
        flange.parent = parent

    return flange


def make_bracketA():
    mat = make_material("mat_bracketA", (0.4, 0.7, 0.9, 1.0))

    parent = bpy.data.objects.new("bracketA", None)
    bpy.context.collection.objects.link(parent)

    make_pipe_half("bracketA_pipe", parent, mat, 'A')

    old_connector = make_connector_original("bracketA_connector", parent, mat)
    old_connector.hide_set(True)
    old_connector.hide_render = True

    make_connector_small("bracketA_connector_small", parent, mat)
    make_reinforcement_rib(parent, mat)

    make_flange_half("bracketA_flange_R", parent, mat, -24, -20, 'R', nut_pocket=True)
    make_flange_half("bracketA_flange_L", parent, mat, -24, -20, 'L', nut_pocket=True)

    return parent


def make_bracketB():
    mat = make_material("mat_bracketB", (0.9, 0.5, 0.4, 1.0))

    parent = bpy.data.objects.new("bracketB", None)
    bpy.context.collection.objects.link(parent)

    make_pipe_half("bracketB_pipe", parent, mat, 'B')

    make_flange_half("bracketB_flange_R", parent, mat, -26, -24, 'R', nut_pocket=False)
    make_flange_half("bracketB_flange_L", parent, mat, -26, -24, 'L', nut_pocket=False)

    return parent


make_monitor()
make_base()
make_base_small()
make_bracketA()
make_bracketB()