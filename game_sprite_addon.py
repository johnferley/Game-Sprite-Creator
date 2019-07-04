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

# Declare constants
ORIGIN = mathutils.Vector((0.0,0.0,0.0))

# Declare properties to be used by the addon
class AddonProperties(bpy.types.PropertyGroup):
    int_camera_angles: bpy.props.IntProperty(
        name = "No of Camera Angles",
        description = "The number of camera angles to render.",
        default = 8,
        min=1,
        max=360)
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
    pointer_top_parent: bpy.props.PointerProperty(
        name = "Top Down",
        description = "The top down camera rig parent.",
        type = bpy.types.Object)
    pointer_dime_parent: bpy.props.PointerProperty(
        name = "Dimetric",
        description = "The dimetric (2:1 isometric) camera rig parent.",
        type = bpy.types.Object)
    pointer_side_parent: bpy.props.PointerProperty(
        name = "Side View",
        description = "The side view camera rig parent.",
        type = bpy.types.Object)
    pointer_bird_parent: bpy.props.PointerProperty(
        name = "Bird's Eye View",
        description = "The birds eye view camera rig parent.",
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
            ('OFF',"Off","",0),
            ('OUTPUT',"Based on Output Parent","",1),
            ('SPRITE',"Based on Sprite Sheet Parent","",2),
            ('OBJECT',"Based on Object Parent","",3)],
        name = "Sprite Sheets",
        description = "Create sprite sheets based on hierarchy and selected option.\n\n* Off - No sprite sheets will be created, all rendered images will be left as individual files.\n* Based on Output Parent - A single sprite sheet will be created containing all objects parented to the Output Parent.\n* Based on Sprite Sheet Parent - A sprite sheet will be created for each sprite sheet child of the output parent, with all objects combined based on the parented sprite sheet.\n* Based on Object Parent - A sprite sheet will be created for each object child of the output parent.",
        default = 'OFF',
        update=None,
        get=None,
        set=None)
    string_output_path: bpy.props.StringProperty(
        name = "Output Path",
        description = "The folder to save the renders to.",
        subtype = 'DIR_PATH',
        default = "")
    bool_auto_folder: bpy.props.BoolProperty(
        name = "Auto Folder Creation",
        description = "If enabled images will be added to sub-folders based on the scene hierarchy.",
        default = False)

# Search child objects for object of specific type
def find_children(parent_obj, obj_type = None):
    output_list = None
    if obj_type == None:
        output_list = [obj for obj in bpy.data.objects if obj.parent == parent_obj]
    else:
        output_list = [obj for obj in bpy.data.objects if (obj.parent == parent_obj and obj.type == obj_type)]
    return output_list

def merge_images(folder_path, save_path, direction='HORIZONTAL'):
    direction = direction.upper()
    if direction not in ('HORIZONTAL', 'VERTICAL'):
        print("Error: Unknown direction {0}, required HORIZONTAL or VERTICAL".format(direction))
        return None

    image_paths = []
    for file in os.listdir(folder_path):
        file_name = os.fsdecode(file)
        print(folder_path + "\\" + file_name)
        if file_name.endswith('.png'):
            image_paths.append(folder_path + "\\" + file_name)

    images = []
    for file in image_paths:
        images.append(Image.open(file))

    widths, heights = zip(*(i.size for i in images))

    output_width = None
    output_height = None
    if direction == 'HORIZONTAL':
        output_width = sum(widths)
        output_height = max(heights)
    elif direction == 'VERTICAL':
        output_width = max(widths)
        output_height = sum(heights)
    
    output_image = Image.new('RGBA', (output_width, output_height))

    print("Merging {} images ...".format(len(images)),end='')
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
    for file in os.listdir(folder_path):
        file_name = os.fsdecode(file)
        os.remove(folder_path + "\\" + file_name)
    os.rmdir(folder_path)

# The next few functions validate the properties input by the user
# These are called in the draw event of each UI panel

# Validate the camera parent selection
def validate_camera_parent(caller, context):
    addon_prop = context.scene.addon_properties

    error = None

    if (addon_prop.pointer_top_parent == None
            and addon_prop.pointer_dime_parent == None
            and addon_prop.pointer_side_parent == None
            and addon_prop.pointer_bird_parent == None):
        error = "* At least one camera parent must be selected"

    return error

# Validate the top parent selection
def validate_top_parent(caller, context):
    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_top_parent != None:
        if addon_prop.pointer_top_parent.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_top_parent.name)
        elif addon_prop.pointer_top_parent.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_top_parent.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_top_parent,'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_top_parent.name)

    return error

# Validate the dimetric parent selection
def validate_dime_parent(caller, context):
    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_dime_parent != None:
        if addon_prop.pointer_dime_parent.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_dime_parent.name)
        elif addon_prop.pointer_dime_parent.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_dime_parent.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_dime_parent,'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_dime_parent.name)

    return error

# Validate the side parent selection
def validate_side_parent(caller, context):
    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_side_parent != None:
        if addon_prop.pointer_side_parent.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_side_parent.name)
        elif addon_prop.pointer_side_parent.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_side_parent.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_side_parent,'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_side_parent.name)

    return error

# Validate the bird's eye view parent selection
def validate_bird_parent(caller, context):
    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_bird_parent != None:
        if addon_prop.pointer_bird_parent.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_bird_parent.name)
        elif addon_prop.pointer_bird_parent.location != ORIGIN:
            error = "* {0} must be at ({1},{2},{3})".format(addon_prop.pointer_bird_parent.name, ORIGIN[0], ORIGIN[1], ORIGIN[2])
        elif len(find_children(addon_prop.pointer_bird_parent,'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_bird_parent.name)

    return error

# Validate the output parent selection
def validate_output_parent(caller, context):
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
                    # Hierarchy must be:
                    #   Output Parent
                    #    L Object Parent
                    #    L ...
                    #    L Object Parent
                    if child.location != ORIGIN:
                        error.append("{0} must be at ({1},{2},{3})".format(child.name, ORIGIN[0], ORIGIN[1], ORIGIN[2]))
                elif addon_prop.enum_sprite_sheet == 'SPRITE':
                    # Hierarchy must be:
                    #   Output Parent
                    #    L Sprite Parent
                    #       L Object Parent
                    #       L ...
                    #       L Object Parent
                    #    L ...
                    #       L ...
                    #    L Sprite Parent
                    #       L ...
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
    if error == []: error = None
    return error

# Validate the output path
def validate_output_path(caller, context):
    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.string_output_path == "":
        error = "* Select File Path"
    elif not os.path.isdir(addon_prop.string_output_path):
        error = "* Invalid File Path"

    return error

def validate_sprite_dropdown(caller, context):
    addon_prop = context.scene.addon_properties

    error = None

    if not pil_installed and addon_prop.enum_sprite_sheet != 'OFF':
        error = "* Pillow is not installed, sprite sheets cannot be created."

    return error

# Validate all properties
def validate_settings(caller, context):

    ok = False

    if (validate_camera_parent(caller, context) == None
            and validate_top_parent(caller, context) == None
            and validate_dime_parent(caller, context) == None
            and validate_side_parent(caller, context) == None
            and validate_bird_parent(caller, context) == None
            and validate_output_parent(caller, context) == None
            and validate_output_path(caller, context) == None
            and validate_sprite_dropdown(caller, context) == None):
        ok = True

    return ok

# Create a set of cubes rendered as wireframes to represent an orthographic grid
# This simply creates a stack of cubes
class CreateOrthoTemplate_OT_Operator(bpy.types.Operator):
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
        bpy.ops.transform.translate(value=(0, 0, block_z/2))
        block_1.name = "Template_Orthographic"
        block_1.display_type = 'WIRE'
        
        return {'FINISHED'}

# Create a set of cubes rendered as wireframes to represent a dimetric (2:1 isometric) grid
# This is important to preserve the 2:1 ratio and grid, however it means that a grid
# "cube" does not take up a 1x1x1 cube, but is instead squashed by cos(35 + (16/60))%
class CreateDimeTemplate_OT_Operator(bpy.types.Operator):
    bl_idname = 'view3d.create_dime_template'
    bl_label = "Dimetric"
    bl_description = "Creates several boxes for use as guides for object sizes in dimetric (2:1 isometric) view."
    bl_context = 'VIEW_3D'

    def execute(self, context):

        bpy.ops.object.select_all(action='DESELECT')

        # Create cube representing grid space in a dimetric (2:1 isometric) view
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=ORIGIN)
        block_1 = bpy.context.active_object
        block_z = math.cos(math.radians(35 + (16/60)))
        bpy.ops.transform.resize(value=(1, 1, block_z))
        bpy.ops.transform.translate(value=(0, 0, block_z/2))
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
        cam.rotation_euler = (math.radians(45),math.radians(0),math.radians(0))
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
        cam.rotation_euler = (math.radians(60),math.radians(0),math.radians(45))
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
        cam.rotation_euler = (math.radians(90),math.radians(0),math.radians(0))
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
        cam.rotation_euler = (math.radians(270),math.radians(0),math.radians(0))
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
        bpy.ops.wm.open_mainfile(filepath=folder + "\\example.blend")
        
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
            print("Preparing to Render ...",end='')
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
            if addon_prop.pointer_top_parent != None:
                cameras.append(addon_prop.pointer_top_parent)
                cam_orig_rotation.append(addon_prop.pointer_top_parent.rotation_euler)
            if addon_prop.pointer_dime_parent != None:
                cameras.append(addon_prop.pointer_dime_parent)
                cam_orig_rotation.append(addon_prop.pointer_dime_parent.rotation_euler)
            if addon_prop.pointer_side_parent != None:
                cameras.append(addon_prop.pointer_side_parent)
                cam_orig_rotation.append(addon_prop.pointer_side_parent.rotation_euler)
            if addon_prop.pointer_bird_parent != None:
                cameras.append(addon_prop.pointer_bird_parent)
                cam_orig_rotation.append(addon_prop.pointer_bird_parent.rotation_euler)
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
                                obj_cam = find_children(cam,'CAMERA')[0]
                                cam.hide_render = False
                                for child in find_children(cam):
                                    child.hide_render = False
                                scn.camera = obj_cam
                                # For each angle
                                for i in range(0, addon_prop.int_camera_angles):
                                    # Rotate camera
                                    cam.rotation_euler.z = math.radians(i * (360 / addon_prop.int_camera_angles))
                                    # Set render path
                                    # If folder creation is enabled, add to folder:
                                    # <sprite_sheet_name>\<object_name>\<camera_name>\<angle>\<track_name>
                                    if addon_prop.bool_auto_folder:
                                        output_folder = "{}{}\\{}\\{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, track.name, cam.name, int(i * (360 / addon_prop.int_camera_angles)))
                                    else:
                                        output_folder = addon_prop.string_output_path
                                    # Get nla track start and end frames
                                    strips = track.strips
                                    anim_start = None
                                    anim_end = 0
                                    for strip in strips:
                                        if strip.action_frame_end > anim_end:
                                            anim_end = int(strip.action_frame_end)
                                        if anim_start == None or strip.action_frame_start < anim_start:
                                            anim_start = int(strip.action_frame_start)
                                    # Render each frame
                                    for frame in range(anim_start,anim_end + 1):
                                        scn.frame_set(frame)
                                        # Set render file name
                                        # Each render will have the format:
                                        # <sprite_sheet_name>_<object_name>_<cam_name>_<angle>_<track_name>_<frame_number>.png
                                        output_name = "{}_{}_{}_{}_{}_{}{}".format(sheet_name, obj.name, track.name, cam.name, int(i * (360 / addon_prop.int_camera_angles)), str(frame).zfill(3), scn.render.file_extension)
                                        scn.render.filepath = output_folder + output_name
                                        #print(scn.render.filepath)
                                        bpy.ops.render.render(write_still=True)
                                    # If not 'OFF' merge frames into angle
                                    if addon_prop.enum_sprite_sheet != 'OFF':
                                        source_folder = output_folder
                                        save_folder = "{}{}\\{}\\{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name, track.name, cam.name)
                                        save_name = "{}_{}_{}_{}_{}{}".format(sheet_name, obj.name, track.name, cam.name, int(i * (360 / addon_prop.int_camera_angles)), scn.render.file_extension)
                                        merge_images(source_folder,save_folder + save_name,'HORIZONTAL')
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
                                    merge_images(source_folder,save_folder + save_name,'VERTICAL')
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
                                merge_images(source_folder,save_folder + save_name,'HORIZONTAL')
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
                            merge_images(source_folder,save_folder + save_name,'VERTICAL')
                            # If renders not being kept, remove them
                            if addon_prop.bool_keep_renders == False:
                                remove_folder(source_folder)
                    else:
                        # Object has no animation tracks
                        for cam in cameras:
                            # Show camera hierarchy
                            obj_cam = find_children(cam,'CAMERA')[0]
                            cam.hide_render = False
                            for child in find_children(cam):
                                child.hide_render = False
                            scn.camera = obj_cam
                            # For each angle
                            for i in range(0, addon_prop.int_camera_angles):
                                # Rotate camera
                                cam.rotation_euler.z = math.radians(i * (360 / addon_prop.int_camera_angles))
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
                                output_name = "{}_{}_{}_{}{}".format(sheet_name, obj.name, cam.name, int(i * (360 / addon_prop.int_camera_angles)), scn.render.file_extension)
                                scn.render.filepath = output_folder + output_name
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
                                merge_images(source_folder,save_folder + save_name,'HORIZONTAL')
                                # If renders not being kept, remove them
                                if addon_prop.bool_keep_renders == False:
                                    remove_folder(source_folder)
                        # If not 'OFF' merge cameras into object
                        if addon_prop.enum_sprite_sheet != 'OFF':
                            source_folder = "{}{}\\{}\\".format(addon_prop.string_output_path, sheet_name, obj.name)
                            save_folder = "{}{}\\".format(addon_prop.string_output_path, sheet_name)
                            save_name = "{}_{}{}".format(sheet_name, obj.name, scn.render.file_extension)
                            merge_images(source_folder,save_folder + save_name,'HORIZONTAL')
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
                    merge_images(source_folder,save_folder + save_name,'VERTICAL')
                    # If renders not being kept, remove them
                    if addon_prop.bool_keep_renders == False:
                        remove_folder(source_folder)
            print("Done")
            print("")
            # Clean Up
            print("Cleaning Up ... ",end='')
            # Show all objects
            for obj in bpy.data.objects:
                obj.hide_render = False
            # Reset camera rotation
            for i,cam in enumerate(cameras):
                cam.rotation_euler = cam_orig_rotation[i]
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
        col.prop(addon_prop, 'pointer_top_parent')
        error = validate_top_parent(self, context)
        if not error == None:
            box = col.box()
            box.label(text=error)

        col.prop(addon_prop, 'pointer_dime_parent')
        error = validate_dime_parent(self, context)
        if not error == None:
            box = col.box()
            box.label(text=error)

        col.prop(addon_prop, 'pointer_side_parent')
        error = validate_side_parent(self, context)
        if error != None:
            box = col.box()
            box.label(text=error)

        col.prop(addon_prop, 'pointer_bird_parent')
        error = validate_bird_parent(self, context)
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
                for e in error:
                    box.label(text=e)

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
