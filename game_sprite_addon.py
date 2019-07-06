import bpy
import mathutils
import math
import os
import numpy
import time

pil_installed = True
try:
    from PIL import Image
    pil_installed = True
except ImportError:
    pil_installed = False

# Define Global Constants
# Allow this to be adjusted?
# Need to check if code will work at any origin without changes
ORIGIN = mathutils.Vector((0.0, 0.0, 0.0))

class AddonProperties(bpy.types.PropertyGroup):
    """Declare properties to be used by the addon."""

    int_camera_angles: bpy.props.IntProperty(
        name = "No of Camera Angles",
        description = "The number of camera angles to render.",
        default = 8,
        min = 1,
        max = 360)

    float_object_ratio: bpy.props.FloatProperty(
        name = "Object Ratio",
        description = "The ratio of object to margin. For example if the render is 128x128px and the object ratio is 0.5, a cube will be 64x64px with a 32px margin on each side (ie will take up half the screen width and height). Note a ratio of 0 will be treated as a ratio of 1 (ie cube takes up full image)",
        default = 1,
        min = 0,
        max = 1)

    float_object_size: bpy.props.FloatProperty(
        name = "Object Size",
        description = "The size of a cube fitting the object being rendered.",
        default = 1)

    pointer_camera_one: bpy.props.PointerProperty(
        name = "Camera 1",
        description = "Camera rig parent.",
        type = bpy.types.Object)

    pointer_camera_two: bpy.props.PointerProperty(
        name = "Camera 2",
        description = "Camera rig parent.",
        type = bpy.types.Object)

    pointer_camera_three: bpy.props.PointerProperty(
        name = "Camera 3",
        description = "Camera rig parent.",
        type = bpy.types.Object)

    pointer_camera_four: bpy.props.PointerProperty(
        name = "Camera 4",
        description = "Camera rig parent.",
        type = bpy.types.Object)

    pointer_output_parent: bpy.props.PointerProperty(
        name = "Output",
        description = "The parent containing all objects to be rendered.",
        type = bpy.types.Object)

    pointer_global_parent: bpy.props.PointerProperty(
        name = "Global",
        description = "The parent containing objects common to every sprite.",
        type = bpy.types.Object)

    bool_keep_renders: bpy.props.BoolProperty(
        name = "Keep Individual Renders",
        description = "If enabled the individual render files will not be deleted at the end of the process.",
        default = False)

    enum_sprite_sheet: bpy.props.EnumProperty(
        items = [
            ('OFF', "Off", "", 0),
            ('OUTPUT', "Based on Output Parent", "", 1),
            ('SPRITE', "Based on Sprite Sheet Parent", "", 2),
            ('OBJECT', "Based on Object Parent", "", 3)],
        name = "Sprite Sheets",
        description = "Create sprite sheets based on hierarchy and selected option.\n\n* Off - No sprite sheets will be created, all rendered images will be left as individual files.\n* Based on Output Parent - A single sprite sheet will be created containing all objects parented to the Output Parent.\n* Based on Sprite Sheet Parent - A sprite sheet will be created for each sprite sheet child of the output parent, with all objects combined based on the parented sprite sheet.\n* Based on Object Parent - A sprite sheet will be created for each object child of the output parent.",
        default = 'OFF',
        update = None,
        get = None,
        set = None)

    string_output_path: bpy.props.StringProperty(
        name = "Output Path",
        description = "The folder to save the renders to.",
        subtype = 'DIR_PATH',
        default = "")

    bool_auto_folder: bpy.props.BoolProperty(
        name = "Auto Folder Creation",
        description = "If enabled images will be added to sub-folders based on the scene hierarchy.",
        default = False)


def find_children(parent_obj, obj_type=None):
    """Search child objects for object of specific type.
    If no type specified, return all children.
    """

    output_list = None
    if obj_type == None:
        output_list = [obj for obj in bpy.data.objects if obj.parent == parent_obj]
    else:
        output_list = [obj for obj in bpy.data.objects if (obj.parent == parent_obj and obj.type == obj_type)]
    return output_list


def merge_images(folder_path, save_path, direction='HORIZONTAL'):
    """Merge all images in a folder spedified by folder_path.
    Resulting image will be saved to a new folder save_path.
    The direction specifies which direction the images should be merged:
        'HORIZONTAL': Merge the iamges horizontally.
        'VERTICAL': Merge the images vertically.
    The function returns the new image as a PIL Image.
    """

    direction = direction.upper()
    if direction not in ('HORIZONTAL', 'VERTICAL'):
        print("Error: Unknown direction {0}, required HORIZONTAL or VERTICAL".format(direction))
        return None

    image_paths = []
    for file in os.listdir(folder_path):
        file_name = os.fsdecode(file)
        print(''.join((folder_path, "\\", file_name)))
        if file_name.endswith('.png'):
            image_paths.append(''.join((folder_path, "\\", file_name)))

    images = []
    for file in image_paths:
        images.append(Image.open(file))

    widths, heights = zip(*(img.size for img in images))

    output_width = None
    output_height = None
    if direction == 'HORIZONTAL':
        output_width = sum(widths)
        output_height = max(heights)
    elif direction == 'VERTICAL':
        output_width = max(widths)
        output_height = sum(heights)

    output_image = Image.new('RGBA', (output_width, output_height))

    print("Merging {} images ...".format(len(images)), end='')
    offset = 0
    for img in images:
        if direction == 'HORIZONTAL':
            output_image.paste(img, (offset, 0))
            offset += img.size[0]
        elif direction == 'VERTICAL':
            output_image.paste(img, (0, offset))
            offset += img.size[1]

    output_image.save(save_path)

    print(" Done")
    print("")

    return output_image


def remove_folder(folder_path):
    """Remove a folder and the files it contains."""

    for file in os.listdir(folder_path):
        file_name = os.fsdecode(file)
        os.remove(''.join((folder_path, "\\", file_name)))
    os.rmdir(folder_path)


# Validate the camera parent selection
def validate_camera_parent(caller, context):
    """Validate the camera parent selection boxes.
    At least one camera must be selected.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if (addon_prop.pointer_camera_one == None
            and addon_prop.pointer_camera_two == None
            and addon_prop.pointer_camera_three == None
            and addon_prop.pointer_camera_four == None):
        error = "* At least one camera parent must be selected"

    return error


# Validate the top parent selection
def validate_camera_one(caller, context):
    """Validate the first camera parent selection box.
    The parent must be an Empty object, positioned at the origin.
    There must be a child Camera object.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_camera_one != None:
        if addon_prop.pointer_camera_one.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_camera_one.name)
        elif addon_prop.pointer_camera_one.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_camera_one.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_camera_one, 'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_camera_one.name)

    return error


# Validate the dimetric parent selection
def validate_camera_two(caller, context):
    """Validate the second camera parent selection box.
    The parent must be an Empty object, positioned at the origin.
    There must be a child Camera object.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_camera_two != None:
        if addon_prop.pointer_camera_two.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_camera_two.name)
        elif addon_prop.pointer_camera_two.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_camera_two.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_camera_two, 'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_camera_two.name)

    return error


# Validate the side parent selection
def validate_camera_three(caller, context):
    """Validate the third camera parent selection box.
    The parent must be an Empty object, positioned at the origin.
    There must be a child Camera object.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_camera_three != None:
        if addon_prop.pointer_camera_three.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_camera_three.name)
        elif addon_prop.pointer_camera_three.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_camera_three.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_camera_three, 'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_camera_three.name)

    return error


# Validate the bird's eye view parent selection
def validate_camera_four(caller, context):
    """Validate the fourth camera parent selection box.
    The parent must be an Empty object, positioned at the origin.
    There must be a child Camera object.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_camera_four != None:
        if addon_prop.pointer_camera_four.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_camera_four.name)
        elif addon_prop.pointer_camera_four.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_camera_four.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_camera_four, 'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_camera_four.name)

    return error


# Validate the output parent selection
def validate_output_parent(caller, context):
    """Validate the output parent selection box
    The parent must be an Empty object, positioned at the origin.
    The parent must have at least one child object.

    The hierarchy of objects must match a specific pattern depending on the option selected in the Sprite Sheet dropdown:
        If Off, Based on Output Parent or Based on Object Parent:
            Output Parent
            L Object Parent
            L ...
            L Object Parent
        If Based on Sprite Sheet
            Output Parent
            L Sprite Parent
                L Object Parent
                L ...
                L Object Parent
            L ...
                L ...
            L Sprite Parent
                L ...
    Where:
        Object Parents must be at the origin.
        Sprite Sheet Parents must be an Empty, at the origin and have at least one child.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_output_parent == None:
        error = "* Output parent must be selected"
    else:
        if addon_prop.pointer_output_parent.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_output_parent.name)
        elif addon_prop.pointer_output_parent.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_output_parent.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_output_parent)) == 0:
            error = "* {0} has no children".format(addon_prop.pointer_output_parent.name)
        else:
            # Check hierarchy
            # Check based on sprite dropdown
            children = find_children(addon_prop.pointer_output_parent)
            error = []
            for child in children:
                if addon_prop.enum_sprite_sheet in ('OFF', 'OUTPUT', 'OBJECT'):
                    if child.location != ORIGIN:
                        error.append("{0} must be at ({1},{2},{3})".format(child.name, ORIGIN[0], ORIGIN[1], ORIGIN[2]))
                elif addon_prop.enum_sprite_sheet == 'SPRITE':
                    if child.type != 'EMPTY':
                        error.append("{0} must be empty".format(child.name))
                    elif child.location != ORIGIN:
                        error.append("{0} must be at ({1},{2},{3})".format(child.name, ORIGIN[0], ORIGIN[1], ORIGIN[2]))
                    elif len(find_children(child)) == 0:
                        error.append("{0} has no children".format(child.name))
                    else:
                        for sub_child in find_children(child):
                            if sub_child.location != ORIGIN:
                                error.append("{0} must be at ({1},{2},{3})".format(sub_child.name, ORIGIN[0], ORIGIN[1], ORIGIN[2]))
    if error == []:
        error = None
    return error


# Validate the output path
def validate_output_path(caller, context):
    """Validate the output path selection.
    The file path must be selected, and be valid.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.string_output_path == "":
        error = "* Select File Path"
    elif not os.path.isdir(addon_prop.string_output_path):
        error = "* Invalid File Path"

    return error


def validate_sprite_dropdown(caller, context):
    """Validate the Sprite Sheet dropdown
    If PIL if not installed this must be set to Off
    """

    addon_prop = context.scene.addon_properties

    error = None

    if not pil_installed and addon_prop.enum_sprite_sheet != 'OFF':
        error = "* PIL is not installed, sprite sheets cannot be created."

    return error


# Validate all properties
def validate_settings(caller, context):
    """Run all validation functions, returning True if the all pass."""

    ok = False

    if (validate_camera_parent(caller, context) == None
            and validate_camera_one(caller, context) == None
            and validate_camera_two(caller, context) == None
            and validate_camera_three(caller, context) == None
            and validate_camera_four(caller, context) == None
            and validate_output_parent(caller, context) == None
            and validate_output_path(caller, context) == None
            and validate_sprite_dropdown(caller, context) == None):
        ok = True

    return ok


class CreateOrthoTemplate_OT_Operator(bpy.types.Operator):
    """Create a cube dispalyed as a wireframe to represent an orthographic object bounding cube."""

    bl_idname = 'view3d.create_ortho_template'
    bl_label = "Orthographic"
    bl_description = "Creates several boxes for use as guides for object sizes in orthographic views."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')

        # Create cubes representing grid spaces in a dimetric (2:1 isometric) view
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=ORIGIN)
        block_1 = bpy.context.active_object
        block_z = 1
        bpy.ops.transform.translate(value=(0, 0, block_z / 2))
        block_1.name = "Template_Orthographic"
        block_1.display_type = 'WIRE'

        return {'FINISHED'}


class CreateDimeTemplate_OT_Operator(bpy.types.Operator):
    """Create a cube displayed as a wireframe to represent a dimetric object bounding cube.
    As dimetric is not true isometric, the cube needs to be squashed to create a proper dimetric grid.
    The exact scaling amount used to achieve this is calculated using trigonometry as:
        squareroot(2)*tan(30)
    Where:
        squareroot(2) is squareroot(1**2 + 1**2), or the size of the diagonal through the cube using pythagoras
        tan(30) is the angle of the camera from horizontal
    """

    bl_idname = 'view3d.create_dime_template'
    bl_label = "Dimetric"
    bl_description = "Creates several boxes for use as guides for object sizes in dimetric (2:1 isometric) view."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')

        # Create cube representing grid space in a dimetric (2:1 isometric) view
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=ORIGIN)
        block_1 = bpy.context.active_object
        block_z = math.sqrt(2) * math.tan(math.radians(30))
        bpy.ops.transform.resize(value=(1, 1, block_z))
        bpy.ops.transform.translate(value=(0, 0, block_z / 2))
        block_1.name = "Template_Dimetric"
        block_1.display_type = 'WIRE'

        return {'FINISHED'}


# Create a camera set up ready for use as a Top Down Camera, such as in calssic JRPG's
# Scale of 1 will fit a 1x1x1 cube horizontally
class CreateTopCamera_OT_Operator(bpy.types.Operator):
    bl_idname = 'view3d.create_top_camera'
    bl_label = "Top Down Camera"
    bl_description = "Create a top down camera."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        addon_prop = context.scene.addon_properties

        # Create a Top Down Camera
        bpy.ops.object.camera_add(location=ORIGIN)
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.name = "Camera_TopDown"
        cam.rotation_euler = (math.radians(45), math.radians(0), math.radians(0))
        cam.data.type = 'ORTHO'
        ortho_scale = addon_prop.float_object_size
        if addon_prop.float_object_ratio > 0 and addon_prop.float_object_ratio < 1:
            ortho_scale = ortho_scale / addon_prop.float_object_ratio
        cam.data.ortho_scale = ortho_scale

        return {'FINISHED'}


# Create a camera set uup ready for use as a Dimetric camera, otherwise known as a 2:1 isometric camera,
# commonly used in strategy games
# Scale of 1.415 will fit a 1x1x1 cube horizontally
class CreateDimeCamera_OT_Operator(bpy.types.Operator):
    bl_idname = 'view3d.create_dime_camera'
    bl_label = "Dimetric Camera"
    bl_description = "Create a dimetric (2:1 isometric) camera."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        addon_prop = context.scene.addon_properties

        orth_scale_dime = math.sqrt(addon_prop.float_object_size**2 + addon_prop.float_object_size**2)

        # Create a Dimetric (2:1 Isometric) Camera
        bpy.ops.object.camera_add(location=ORIGIN)
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.name = "Camera_Dimetric"
        cam.rotation_euler = (math.radians(60), math.radians(0), math.radians(45))
        cam.data.type = 'ORTHO'
        ortho_scale = orth_scale_dime
        if addon_prop.float_object_ratio > 0 and addon_prop.float_object_ratio < 1:
            ortho_scale = ortho_scale / addon_prop.float_object_ratio
        cam.data.ortho_scale = ortho_scale

        return {'FINISHED'}


# Create a side view camera, like the cameras used in side scrolling platformers
# Scale of 1 will fit a 1x1x1 cube horizontally
class CreateSideCamera_OT_Operator(bpy.types.Operator):
    bl_idname = 'view3d.create_side_camera'
    bl_label = "Side View Camera"
    bl_description = "Create a side view camera."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        addon_prop = context.scene.addon_properties

        # Create a Side View Camera
        bpy.ops.object.camera_add(location=ORIGIN)
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.name = "Camera_Side"
        cam.rotation_euler = (math.radians(90), math.radians(0), math.radians(0))
        cam.data.type = 'ORTHO'
        ortho_scale = addon_prop.float_object_size
        if addon_prop.float_object_ratio > 0 and addon_prop.float_object_ratio < 1:
            ortho_scale = ortho_scale / addon_prop.float_object_ratio
        cam.data.ortho_scale = ortho_scale

        return {'FINISHED'}


# Create a birds eye view camera, commonly used in twin stick shooters and bullet hell games
# Scale of 1 will fit a 1x1x1 cube horizontally
class CreateBirdCamera_OT_Operator(bpy.types.Operator):
    bl_idname = 'view3d.create_bird_camera'
    bl_label = "Bird's Eye View Camera"
    bl_description = "Create a bird's eye view camera."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        addon_prop = context.scene.addon_properties

        # Create a Bird's Eye View Camera
        bpy.ops.object.camera_add(location=ORIGIN)
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.name = "Camera_BirdsEye"
        cam.rotation_euler = (math.radians(270), math.radians(0), math.radians(0))
        cam.data.type = 'ORTHO'
        ortho_scale = addon_prop.float_object_size
        if addon_prop.float_object_ratio > 0 and addon_prop.float_object_ratio < 1:
            ortho_scale = ortho_scale / addon_prop.float_object_ratio
        cam.data.ortho_scale = ortho_scale

        return {'FINISHED'}


# Create a birds eye view camera, commonly used in twin stick shooters and bullet hell games
# Scale of 1 will fit a 1x1x1 cube horizontally
class LoadExample_OT_Operator(bpy.types.Operator):
    bl_idname = 'view3d.load_example'
    bl_label = "Load Example Scene"
    bl_description = "Load an example scene."
    bl_context = 'VIEW_3D'

    def execute(self, context):

        # Load Scene
        folder = os.getcwd()
        bpy.ops.wm.open_mainfile(filepath=''.join((folder, "\\example.blend")))

        return {'FINISHED'}


# Render the sprites as per the settings chosen
class RenderSprites_OT_Operator(bpy.types.Operator):
    bl_idname = 'view3d.render_sprites'
    bl_label = "Render Sprites"
    bl_description = "Render sprites based on selected options and scene setup."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        scn = context.scene
        addon_prop = scn.addon_properties

        # As validation must have passed for the button calling this operator to be enabled, the scene should be ok
        # However, since a user could potentially try to use this operator elsewhere, it is included here
        if validate_settings(self, context):
            print("Preparing to Render ...", end='')
            # Get Original Render Path
            orig_path = scn.render.filepath
            # Hide all objects
            for obj in bpy.data.objects:
                obj.hide_render = True
            # Unhide global parent hierarchy
            global_parent = addon_prop.pointer_global_parent
            global_parent.hide_render = False
            for child in find_children(global_parent):
                child.hide_render = False
            # Get parents
            output = addon_prop.pointer_output_parent
            cameras = []
            cam_orig_rotation = []
            if addon_prop.pointer_camera_one != None:
                cameras.append(addon_prop.pointer_camera_one)
                cam_orig_rotation.append(addon_prop.pointer_camera_one.rotation_euler)
            if addon_prop.pointer_camera_two != None:
                cameras.append(addon_prop.pointer_camera_two)
                cam_orig_rotation.append(addon_prop.pointer_camera_two.rotation_euler)
            if addon_prop.pointer_camera_three != None:
                cameras.append(addon_prop.pointer_camera_three)
                cam_orig_rotation.append(addon_prop.pointer_scamera_three.rotation_euler)
            if addon_prop.pointer_camera_four != None:
                cameras.append(addon_prop.pointer_camera_four)
                cam_orig_rotation.append(addon_prop.pointer_camera_four.rotation_euler)
            # 2d array, where each row represents the sprite sheets, and columns represent the objects for each sprite
            # [[...],[...],[...]]
            # [.................] = List of sprite sheets
            #  [...] [...] [...]  = Lists of objects
            sheets = []
            sheet_option = addon_prop.enum_sprite_sheet
            if sheet_option in ('OFF', 'OUTPUT'):
                # For simplificatoin OFF will be set up as if for OUTPUT, and will simply skip the composition stage
                # One sprite sheet containing all objects
                sheets.append(find_children(output))
            elif sheet_option == 'SPRITE':
                # Multiple sprite sheets containing multiple objects
                for child in find_children(output):
                    sheets.append(find_children(child))
            elif sheet_option == 'OBJECT':
                # Multiple sprite sheets containing a single object each
                for child in find_children(output):
                    sheets.append([child])
            print(" Done")
            print("")
            print("Rendering ...")
            print("")
            # Create Renders
            for sheet in sheets:
                for obj in sheet:
                    sheet_name = obj.parent.name
                    # Show object and children
                    obj.hide_render = False
                    for child in find_children(obj):
                        child.hide_render = False
                    obj_animations = obj.animation_data
                    # Find animations, if any
                    if obj_animations:
                        # Object has animation tracks
                        # Mute all tracks
                        for track in obj_animations.nla_tracks:
                            track.mute = True
                        for track in obj_animations.nla_tracks:
                            # Show this track
                            track.mute = False
                            # For each camera
                            for cam in cameras:
                                # Show camera hierarchy
                                obj_cam = find_children(cam, 'CAMERA')[0]
                                cam.hide_render = False
                                for child in find_children(cam):
                                    child.hide_render = False
                                scn.camera = obj_cam
                                # For each angle
                                for i_angle in range(0, addon_prop.int_camera_angles):
                                    # Rotate camera
                                    cam.rotation_euler.z = math.radians(i_angle * (360 / addon_prop.int_camera_angles))
                                    # Set render path
                                    # If folder creation is enabled, add to folder:
                                    # <sprite_sheet_name>\<object_name>\<camera_name>\<angle>\<track_name>
                                    if addon_prop.bool_auto_folder:
                                        output_folder = "{}{}\\{}\\{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, track.name, cam.name, int(i_angle * (360 / addon_prop.int_camera_angles)))
                                    else:
                                        output_folder = addon_prop.string_output_path
                                    # Get nla track start and end frames
                                    strips = track.strips
                                    anim_start = None
                                    anim_end = 0
                                    for strip in strips:
                                        if strip.frame_end > anim_end:
                                            anim_end = int(strip.frame_end)
                                        if anim_start == None or strip.frame_start < anim_start:
                                            anim_start = int(strip.frame_start)
                                    # Render each frame
                                    for frame in range(anim_start, anim_end + 1):
                                        scn.frame_set(frame)
                                        # Set render file name
                                        # Each render will have the format:
                                        # <sprite_sheet_name>_<object_name>_<cam_name>_<angle>_<track_name>_<frame_number>.png
                                        output_name = "{}_{}_{}_{}_{}_{}{}".format(sheet_name, obj.name, track.name, cam.name, int(i_angle * (360 / addon_prop.int_camera_angles)), str(frame).zfill(3), scn.render.file_extension)
                                        scn.render.filepath = ''.join((output_folder, output_name))
                                        #print(scn.render.filepath)
                                        bpy.ops.render.render(write_still=True)
                                    # If not 'OFF' merge frames into angle
                                    if addon_prop.enum_sprite_sheet != 'OFF':
                                        source_folder = output_folder
                                        save_folder = "{}{}\\{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, track.name, cam.name)
                                        save_name = "{}_{}_{}_{}_{}{}".format(sheet_name, obj.name, track.name, cam.name, int(i_angle * (360 / addon_prop.int_camera_angles)), scn.render.file_extension)
                                        merge_images(source_folder, ''.join((save_folder, save_name)), 'HORIZONTAL')
                                        # If renders not being kept, remove them
                                        if addon_prop.bool_keep_renders == False:
                                            remove_folder(source_folder)
                                # Hide camera hierarchy
                                cam.hide_render = True
                                for child in find_children(cam):
                                    child.hide_render = True
                                # If not 'OFF' merge angles into camera
                                if addon_prop.enum_sprite_sheet != 'OFF':
                                    source_folder = "{}{}\\{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, track.name, cam.name)
                                    save_folder = "{}{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, track.name)
                                    save_name = "{}_{}_{}_{}{}".format(sheet_name, obj.name, track.name, cam.name, scn.render.file_extension)
                                    merge_images(source_folder, ''.join((save_folder, save_name)), 'VERTICAL')
                                    # If renders not being kept, remove them
                                    if addon_prop.bool_keep_renders == False:
                                        remove_folder(source_folder)
                            # Mute this track
                            track.mute = True
                            # If not 'OFF' merge cameras into track
                            if addon_prop.enum_sprite_sheet != 'OFF':
                                source_folder = "{}{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, track.name)
                                save_folder = "{}{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name)
                                save_name = "{}_{}_{}{}".format(sheet_name, obj.name, track.name, scn.render.file_extension)
                                merge_images(source_folder, ''.join((save_folder, save_name)), 'HORIZONTAL')
                                # If renders not being kept, remove them
                                if addon_prop.bool_keep_renders == False:
                                    remove_folder(source_folder)
                        # Unmute all tracks
                        for track in obj_animations.nla_tracks:
                            track.mute = False
                        # If not 'OFF' merge tracks into object
                        if addon_prop.enum_sprite_sheet != 'OFF':
                            source_folder = "{}{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name)
                            save_folder = "{}{}\\".format(addon_prop.string_output_path, sheet_name)
                            save_name = "{}_{}{}".format(sheet_name, obj.name, scn.render.file_extension)
                            merge_images(source_folder, ''.join((save_folder, save_name)), 'VERTICAL')
                            # If renders not being kept, remove them
                            if addon_prop.bool_keep_renders == False:
                                remove_folder(source_folder)
                    else:
                        # Object has no animation tracks
                        for cam in cameras:
                            # Show camera hierarchy
                            obj_cam = find_children(cam, 'CAMERA')[0]
                            cam.hide_render = False
                            for child in find_children(cam):
                                child.hide_render = False
                            scn.camera = obj_cam
                            # For each angle
                            for i_angle in range(0, addon_prop.int_camera_angles):
                                # Rotate camera
                                cam.rotation_euler.z = math.radians(i_angle * (360 / addon_prop.int_camera_angles))
                                # Set render path
                                # If folder creation is enabled, add to folder:
                                # <sprite_sheet_name>\<object_name>\<camera_name>\<angle>
                                if addon_prop.bool_auto_folder:
                                    output_folder = "{}{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, cam.name)
                                else:
                                    output_folder = addon_prop.string_output_path
                                # Set render file name
                                # Each render will have the format:
                                # <sprite_sheet_name>_<object_name>_<cam_name>_<angle>.png
                                output_name = "{}_{}_{}_{}{}".format(sheet_name, obj.name, cam.name, int(i_angle * (360 / addon_prop.int_camera_angles)), scn.render.file_extension)
                                scn.render.filepath = ''.join((output_folder, output_name))
                                #print(scn.render.filepath)
                                bpy.ops.render.render(write_still=True)
                            # Hide camera hierarchy
                            cam.hide_render = True
                            for child in find_children(cam):
                                child.hide_render = True
                            # If not 'OFF' merge angles into camera
                            if addon_prop.enum_sprite_sheet != 'OFF':
                                source_folder = "{}{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, cam.name)
                                save_folder = "{}{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name)
                                save_name = "{}_{}_{}{}".format(sheet_name, obj.name, cam.name, scn.render.file_extension)
                                merge_images(source_folder, ''.join((save_folder, save_name)), 'HORIZONTAL')
                                # If renders not being kept, remove them
                                if addon_prop.bool_keep_renders == False:
                                    remove_folder(source_folder)
                        # If not 'OFF' merge cameras into object
                        if addon_prop.enum_sprite_sheet != 'OFF':
                            source_folder = "{}{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name)
                            save_folder = "{}{}\\".format(addon_prop.string_output_path, sheet_name)
                            save_name = "{}_{}{}".format(sheet_name, obj.name, scn.render.file_extension)
                            merge_images(source_folder, ''.join((save_folder, save_name)), 'HORIZONTAL')
                            # If renders not being kept, remove them
                            if addon_prop.bool_keep_renders == False:
                                remove_folder(source_folder)
                    # Hide Object and children
                    obj.hide_render = True
                    for child in find_children(obj):
                        child.hide_render = True
                # If not 'OFF' merge objects into sheet
                if addon_prop.enum_sprite_sheet != 'OFF':
                    source_folder = "{}{}\\".format(addon_prop.string_output_path, sheet_name)
                    save_folder = "{}".format(addon_prop.string_output_path)
                    save_name = "{}{}".format(sheet_name, scn.render.file_extension)
                    merge_images(source_folder, ''.join((save_folder, save_name)), 'VERTICAL')
                    # If renders not being kept, remove them
                    if addon_prop.bool_keep_renders == False:
                        remove_folder(source_folder)
            print("Done")
            print("")
            # Clean Up
            print("Cleaning Up ... ", end='')
            # Show all objects
            for obj in bpy.data.objects:
                obj.hide_render = False
            # Reset camera rotation
            for i_cam, cam in enumerate(cameras):
                cam.rotation_euler = cam_orig_rotation[i_cam]
            # Reset Render Path
            scn.render.filepath = orig_path
            print(" Done")
            print("")

            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# The template creation dropdown
class OBJECT_MT_TemplateMenu(bpy.types.Menu):
    bl_idname = 'OBJECT_MT_TemplateMenu'
    bl_name = "Create Template"
    bl_label = "Create Template"
    bl_description = "Create template for selected view types."

    def draw(self, context):
        layout = self.layout

        layout.operator('view3d.create_ortho_template', icon='OUTLINER_OB_GROUP_INSTANCE')
        layout.operator('view3d.create_dime_template', icon='OUTLINER_OB_GROUP_INSTANCE')


# The camera creation dropdown
class OBJECT_MT_CameraMenu(bpy.types.Menu):
    bl_idname = 'OBJECT_MT_CameraMenu'
    bl_name = "Create Camera"
    bl_label = "Create Camera"
    bl_description = "Create camera with selected settings."

    def draw(self, context):
        layout = self.layout

        layout.operator('view3d.create_top_camera', icon='OUTLINER_OB_CAMERA')
        layout.operator('view3d.create_dime_camera', icon='OUTLINER_OB_CAMERA')
        layout.operator('view3d.create_side_camera', icon='OUTLINER_OB_CAMERA')
        layout.operator('view3d.create_bird_camera', icon='OUTLINER_OB_CAMERA')


# The scene setup sub panel
class ADDON_PT_ScenePanel(bpy.types.Panel):
    bl_idname = 'ADDON_PT_scenepanel'
    bl_label = "Scene Setup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Game Sprite Creator"

    def draw(self, context):
        layout = self.layout
        addon_prop = context.scene.addon_properties

        col = layout.column(align=True)
        col.operator('view3d.load_example', icon='FILE_BLEND')

        col = layout.column(align=True)
        col.menu('OBJECT_MT_TemplateMenu', text="Create Template", icon='ADD')

        col = layout.column(align=True)
        col.label(text="Create Preset Camera:")
        col.prop(addon_prop, 'float_object_ratio')
        col.prop(addon_prop, 'float_object_size')
        col.menu('OBJECT_MT_CameraMenu', text="Add", icon='ADD')


# The render setup sub panel
class ADDON_PT_SetupPanel(bpy.types.Panel):
    bl_idname = 'ADDON_PT_setuppanel'
    bl_label = "Render Setup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Game Sprite Creator"

    def draw(self, context):
        layout = self.layout
        addon_prop = context.scene.addon_properties

        col = layout.column(align=True)
        col.prop(addon_prop, 'int_camera_angles')

        col = layout.column(align=True)
        col.label(text="Camera Parents:")
        col.prop(addon_prop, 'pointer_camera_one')
        error = validate_camera_one(self, context)
        if not error == None:
            box = col.box()
            box.label(text=error)

        col.prop(addon_prop, 'pointer_camera_two')
        error = validate_camera_two(self, context)
        if not error == None:
            box = col.box()
            box.label(text=error)

        col.prop(addon_prop, 'pointer_camera_three')
        error = validate_camera_three(self, context)
        if error != None:
            box = col.box()
            box.label(text=error)

        col.prop(addon_prop, 'pointer_camera_four')
        error = validate_camera_four(self, context)
        if not error == None:
            box = col.box()
            box.label(text=error)

        error = validate_camera_parent(self, context)
        if not error == None:
            box = col.box()
            box.label(text=error)

        col = layout.column(align=True)
        col.label(text="Render Parents:")
        col.prop(addon_prop, 'pointer_output_parent')
        error = validate_output_parent(self, context)
        if not error == None:
            box = col.box()
            if isinstance(error, str):
                box.label(text=error)
            else:
                for error_line in error:
                    box.label(text=error_line)

        col.prop(addon_prop, 'pointer_global_parent')

        col = layout.column(align=True)
        col.prop(addon_prop, 'bool_keep_renders')
        if addon_prop.enum_sprite_sheet == 'OFF':
            col.enabled = False

        col = layout.column(align=True)
        col.prop(addon_prop, 'enum_sprite_sheet')
        error = validate_sprite_dropdown(self, context)
        if error != None:
            box = col.box()
            box.label(text=error)


# The render sprites sub panel
class ADDON_PT_RenderPanel(bpy.types.Panel):
    bl_idname = 'ADDON_PT_renderpanel'
    bl_label = "Render Sprites"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Game Sprite Creator"

    def draw(self, context):
        layout = self.layout
        addon_prop = context.scene.addon_properties

        col = layout.column(align=True)
        col.prop(addon_prop, 'string_output_path')
        error = validate_output_path(self, context)
        if not error == None:
            box = col.box()
            box.label(text=error)

        col = layout.column(align=True)
        col.prop(addon_prop, 'bool_auto_folder')

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('view3d.render_sprites', icon='RENDER_RESULT')
        row.enabled = validate_settings(self, context)
        if not row.enabled:
            box = col.box()
            box.label(text="* Check for errors above")
