import bpy
import bmesh
import mathutils
import math
import os

pil_installed = True
try:
    from PIL import Image
    pil_installed = True
except ImportError:
    pil_installed = False


class ValidationError(Exception):
    """ Raised when validation fails"""
    def __init__(self, message=None):
        if message is None:
            message = "See Blender UI for errors."
        super(ValidationError, self).__init__(message)


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

    string_output_order: bpy.props.StringProperty(
        name = "Group Order",
        description = "The order in which to arrange the render folders and image merge grouping.\n\nUse the following values without quotes, separated by commas:\n* 'sheet' - The sprite sheets as specified above, this must be the first element.\n* 'object' - The objects as specified above, must be placed somewhere after 'sheet'.\n* 'track' - The animation tracks for each object, must be placed somewhere after 'object'.\n* 'camera' - The cameras as specified above.\n* 'angle' - The camera angles as specified above.\n* 'frame' - The frames of each track, must be placed somewhere after 'track'\n\nAll six values must be used, and follow the ordering rules as listed.",
        default = "sheet,object,camera,track,angle,frame")

    string_output_orientation: bpy.props.StringProperty(
        name = "Output Orientation",
        description = "The orientation of each level of the output, 'h' for horizontal, 'v' for vertical, separated by commas. The first element must be '-', as sprite sheets are not merged. There must be six values corresponding to the values in Output Order.",
        default = "-,v,h,v,v,h")



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
    The parent must be an Empty object.
    There must be a child Camera object.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_camera_one != None:
        if addon_prop.pointer_camera_one.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_camera_one.name)
        elif len(find_children(addon_prop.pointer_camera_one, 'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_camera_one.name)

    return error


# Validate the dimetric parent selection
def validate_camera_two(caller, context):
    """Validate the second camera parent selection box.
    The parent must be an Empty object.
    There must be a child Camera object.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_camera_two != None:
        if addon_prop.pointer_camera_two.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_camera_two.name)
        elif len(find_children(addon_prop.pointer_camera_two, 'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_camera_two.name)

    return error


# Validate the side parent selection
def validate_camera_three(caller, context):
    """Validate the third camera parent selection box.
    The parent must be an Empty object.
    There must be a child Camera object.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_camera_three != None:
        if addon_prop.pointer_camera_three.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_camera_three.name)
        elif len(find_children(addon_prop.pointer_camera_three, 'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_camera_three.name)

    return error


# Validate the bird's eye view parent selection
def validate_camera_four(caller, context):
    """Validate the fourth camera parent selection box.
    The parent must be an Empty object.
    There must be a child Camera object.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_camera_four != None:
        if addon_prop.pointer_camera_four.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_camera_four.name)
        elif len(find_children(addon_prop.pointer_camera_four, 'CAMERA')) == 0:
            error = "* {0} does not have a child camera".format(addon_prop.pointer_camera_four.name)

    return error


# Validate the output parent selection
def validate_output_parent(caller, context):
    """Validate the output parent selection box
    The parent must be an Empty object.
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
        Sprite Sheet Parents must be an Empty and have at least one child.
    """

    addon_prop = context.scene.addon_properties

    error = None

    if addon_prop.pointer_output_parent == None:
        error = "* Output parent must be selected"
    else:
        if addon_prop.pointer_output_parent.type != 'EMPTY':
            error = "* {0} must be an empty".format(addon_prop.pointer_output_parent.name)
        elif len(find_children(addon_prop.pointer_output_parent)) == 0:
            error = "* {0} has no children".format(addon_prop.pointer_output_parent.name)
        else:
            # Check hierarchy
            # Check based on sprite dropdown
            children = find_children(addon_prop.pointer_output_parent)
            error = []
            for child in children:
                if addon_prop.enum_sprite_sheet == 'SPRITE':
                    if child.type != 'EMPTY':
                        error.append("{0} must be empty".format(child.name))
                    elif len(find_children(child)) == 0:
                        error.append("{0} has no children".format(child.name))
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


def validate_render(caller, context):
    """Only enable the render button if the file has been saved"""

    error = None

    if not bpy.data.is_saved:
        error = "* The file has not been saved."
    elif bpy.data.is_dirty:
        error = "* There are unsaved changes"

    return error


def validate_output_order(caller,context):
    """Validate the Output Order field
    The field must contain the following six values separated by commas:
    angle, camera, frame, object, sheet, track

    sheet must be the first value
    object must come after sheet
    track must come after object
    frame must come after track
    """

    addon_prop = context.scene.addon_properties

    error = None

    output_string = addon_prop.string_output_order.lower()
    output_array = output_string.split(',')
    output_types = ["angle","camera","frame","object", "sheet", "track"]

    if len(output_array) < 6:
        error = "* The following six elements must be in the list, separated by commas:\nangle, camera, frame, object, sheet, track."
    else:
        error = []
        for element in output_array:
            if element not in output_types:
                error.append("* {0} is not a recognised element.".format(element))
        if error == []:
            for output_type in output_types:
                type_count = output_array.count(output_type)
                if type_count > 1:
                    error.append("* {0} must only appear once.".format(output_type))
                elif type_count < 1:
                    error.append("* {0} must appear once.".format(output_type))
            if error == []:
                if output_array[0] != "sheet":
                    error.append("* The first element must be 'sheet'")
                if output_array.index("object") < output_array.index("sheet"):
                    error.append("* 'object' must be after 'sheet'")
                if output_array.index("track")< output_array.index("object"):
                    error.append("* 'track' must be after 'object'")
                if output_array.index("frame")< output_array.index("track"):
                    error.append("* 'frame' must be after 'track'")
                if error == []:
                    error = None
        else:
            error.append("* Elements must be one of:\nangle, camera, frame, object, sheet, track")

    return error


def validate_output_orientation(caller,context):
    """Validate the Output Order field
    The field must contain six values from the following list separated by commas:
    -,h,v

    - must be the first value, and included only once
    h represents horizontal orientation
    v represent vertical orientation
    """

    addon_prop = context.scene.addon_properties

    error = None

    output_string = addon_prop.string_output_orientation.lower()
    output_array = output_string.split(',')
    output_types = ["-","h","v"]

    if len(output_array) < 6:
        error = "* The string must contain a '-' followed by six values of either 'h' or 'v', separated by commas."
    else:
        error = []
        for element in output_array:
            if element not in output_types:
                error.append("* {0} is not a recognised element.".format(element))
        if error == []:
                if output_array[0] != "-":
                    error.append("* The first element must be '-'")
                if error == []:
                    error = None
        else:
            error.append("* Elements must be one of: -, h, v")

    return error


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
            and validate_sprite_dropdown(caller, context) == None
            and validate_output_order(caller, context) == None
            and validate_output_orientation(caller, context) == None):
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
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=bpy.context.scene.cursor.location)
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
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=bpy.context.scene.cursor.location)
        block_1 = bpy.context.active_object
        block_z = math.sqrt(2) * math.tan(math.radians(30))
        bpy.ops.transform.resize(value=(1, 1, block_z))
        bpy.ops.transform.translate(value=(0, 0, block_z / 2))
        block_1.name = "Template_Dimetric"
        block_1.display_type = 'WIRE'

        return {'FINISHED'}


class CreateTopCamera_OT_Operator(bpy.types.Operator):
    """Create a top down orthographic camera at the cursor.
    This points at 45 degrees from vertical.
    The orthographic scale is set based on the specified object size and ratio.
    """

    bl_idname = 'view3d.create_top_camera'
    bl_label = "Top Down Camera"
    bl_description = "Create a top down camera."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        addon_prop = context.scene.addon_properties

        # Create a Top Down Camera
        bpy.ops.object.camera_add(location=bpy.context.scene.cursor.location)
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.name = "Camera_TopDown"
        cam.rotation_euler = (math.radians(45), math.radians(0), math.radians(0))
        cam.data.type = 'ORTHO'
        # Initialise the scale based on object size
        ortho_scale = addon_prop.float_object_size
        # Adjust the scale based on the required ratio
        if addon_prop.float_object_ratio > 0 and addon_prop.float_object_ratio < 1:
            ortho_scale = ortho_scale / addon_prop.float_object_ratio
        cam.data.ortho_scale = ortho_scale

        return {'FINISHED'}


class CreateDimeCamera_OT_Operator(bpy.types.Operator):
    """Create a dimetric orthographic camera at the cursor.
    This uses an angle of 60 degrees from vertical to create a 2:1 Isometric view.
    The orthographic scale is set based on the specified object size and ratio.
    """

    bl_idname = 'view3d.create_dime_camera'
    bl_label = "Dimetric Camera"
    bl_description = "Create a dimetric (2:1 isometric) camera."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        addon_prop = context.scene.addon_properties

        orth_scale_dime = math.sqrt(addon_prop.float_object_size**2 + addon_prop.float_object_size**2)

        # Create a Dimetric (2:1 Isometric) Camera
        bpy.ops.object.camera_add(location=bpy.context.scene.cursor.location)
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.name = "Camera_Dimetric"
        cam.rotation_euler = (math.radians(60), math.radians(0), math.radians(45))
        cam.data.type = 'ORTHO'
        # Initialise the scale based on object size
        ortho_scale = orth_scale_dime
        # Adjust the scale based on the required ratio
        if addon_prop.float_object_ratio > 0 and addon_prop.float_object_ratio < 1:
            ortho_scale = ortho_scale / addon_prop.float_object_ratio
        cam.data.ortho_scale = ortho_scale

        return {'FINISHED'}


class CreateSideCamera_OT_Operator(bpy.types.Operator):
    """Create a side orthographic camera at the cursor.
    This points horizontally.
    The orthographic scale is set based on the specified object size and ratio.
    """

    bl_idname = 'view3d.create_side_camera'
    bl_label = "Side View Camera"
    bl_description = "Create a side view camera."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        addon_prop = context.scene.addon_properties

        # Create a Side View Camera
        bpy.ops.object.camera_add(location=bpy.context.scene.cursor.location)
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.name = "Camera_Side"
        cam.rotation_euler = (math.radians(90), math.radians(0), math.radians(0))
        cam.data.type = 'ORTHO'
        # Initialise the scale based on object size
        ortho_scale = addon_prop.float_object_size
        # Adjust the scale based on the required ratio
        if addon_prop.float_object_ratio > 0 and addon_prop.float_object_ratio < 1:
            ortho_scale = ortho_scale / addon_prop.float_object_ratio
        cam.data.ortho_scale = ortho_scale

        return {'FINISHED'}


class CreateBirdCamera_OT_Operator(bpy.types.Operator):
    """Create a birds eye view orthographic camera at the cursor.
    This points vertically downwards.
    The orthographic scale is set based on the specified object size and ratio.
    """

    bl_idname = 'view3d.create_bird_camera'
    bl_label = "Bird's Eye View Camera"
    bl_description = "Create a bird's eye view camera."
    bl_context = 'VIEW_3D'

    def execute(self, context):
        addon_prop = context.scene.addon_properties

        # Create a Bird's Eye View Camera
        bpy.ops.object.camera_add(location=bpy.context.scene.cursor.location)
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.name = "Camera_BirdsEye"
        cam.rotation_euler = (math.radians(0), math.radians(0), math.radians(0))
        cam.data.type = 'ORTHO'
        # Initialise the scale based on object size
        ortho_scale = addon_prop.float_object_size
        # The orthographic scale is set based on the specified object size and ratio.
        if addon_prop.float_object_ratio > 0 and addon_prop.float_object_ratio < 1:
            ortho_scale = ortho_scale / addon_prop.float_object_ratio
        cam.data.ortho_scale = ortho_scale

        return {'FINISHED'}


class LoadExample_OT_Operator(bpy.types.Operator):
    """Load an example scene for use during testing.
    The file is opened from the blender folder when normally.
    When run from the IDE this is loaded from this programs folder.
    """

    bl_idname = 'view3d.load_example'
    bl_label = "Load Example Scene"
    bl_description = "Load an example scene."
    bl_context = 'VIEW_3D'

    def execute(self, context):

        # Load Scene
        folder = os.getcwd()
        bpy.ops.wm.open_mainfile(filepath=''.join((folder, "\\example.blend")))

        return {'FINISHED'}


class OriginToFloor_OT_Operator(bpy.types.Operator):
    """Move the origin point of selected objects so that z = 0.
    """

    bl_idname = 'view3d.origin_to_floor'
    bl_label = "Move Origin to Floor"
    bl_description = "Move the origin point of selected objects so that z = 0."
    bl_context = 'VIEW_3D'

    def execute(self, context):

        for obj in bpy.context.selected_objects:
            new_origin = mathutils.Vector((obj.matrix_world.translation[0], obj.matrix_world.translation[1], 0))
            transform_matrix = mathutils.Matrix.Translation(obj.matrix_world.translation - new_origin)
            obj_data = obj.data
            if obj_data.is_editmode:
                bm = bmesh.from_edit_mesh(obj_data)
                bm.transform(transform_matrix)
                bmesh.update_edit_mesh(obj_data, False, False)
            else:
                obj_data.transform(transform_matrix)

            obj_data.update()

            obj.matrix_world.translation = new_origin

        return {'FINISHED'}


class RenderSprites():
    """ This class contains all the variables, lists and functions related to rendering sprites.
    Calling iterate() will render a sprite, then increment the lists to the next frame, angle, camera, object, track or sheet based on the settings provided.
    If there are still iamges to be rendered, iterate will return True, and will return False once it has finished.
    In order to render all images iterate() must therefore be called in a loop that breaks when it returns False.
    """

    # The following properties contain the lists and curent element indexes for the output groups
    angles = None
    i_current_angle = 0

    cameras = None
    i_current_camera = 0

    frames = None
    i_current_frame = 0

    sheets = None
    i_current_sheet = 0

    objects = None
    i_current_object = 0

    tracks = None
    i_current_track = 0

    # These variables determine the order the lists are grouped in and the orientation fo each group
    output_order = None
    output_orientation = None

    # This is used to get properties from the Blender UI
    context = None

    # These variables are used to store the initial scene layout so that it can be reset once rendering is completed
    cam_orig_location = None
    cam_orig_rotation = None
    orig_scene_camera = None
    global_parent_orig_location = None
    orig_frame = None
    orig_render_path = None
    orig_visibility = None

    # This is used to tell an outer loop calling iterate() if the program is currently doing an iteration
    # This allows for the outer loop to call cleanup() if the loop is cancelled part way through
    iterating = False

    def __init__(self, context):
        """ Initialise the renderer"""

        # Set the context for retreiving UI options
        self.context = context

        # Check that all options have been set correctly
        if not validate_settings(self, context):
            raise ValidationError

        # Get the current settings from the UI
        addon_prop = self.context.scene.addon_properties

        output_order_string = addon_prop.string_output_order
        output_orientation_string = addon_prop.string_output_orientation

        self.output_order = output_order_string.split(',')
        self.output_orientation = output_orientation_string.split(',')

        self.prepare_render()

    def iterate(self):
        """ Wraps a single iteration of the renderer with cleanup code and output flags
        Returns True if rendering has not finished, False if it has finished
        """
        # Get the current settings from the UI
        addon_prop = self.context.scene.addon_properties

        self.iterating = True
        self.render_iteration()
        self.iterating = False

        finished = False

        # Increment all list indexes
        # Starts at the innermost level, if this value wraps round it increments the next level out once
        # If the outermost level wraps rendering has finished
        for level_index in range(len(self.output_order)-1, -1, -1):
            wrap = self.incr_index(level_index)
            if not wrap:
                break
            elif level_index == 0 and wrap:
                finished = True
                if addon_prop.enum_sprite_sheet != 'OFF':
                    self.merge_images(addon_prop.string_output_path, True)
                self.cleanup()

        return finished

    def incr_index(self, level_index):
        """ This function increments an index based on the level and the output order
        If the index wraps then it outputs True, otherwise it outputs False
        """

        index_type = self.output_order[level_index]

        wrap = False

        if index_type == "angle":
            self.i_current_angle += 1
            # Wrap the index if it goes past the end of the list
            self.i_current_angle %= len(self.angles)
            if self.i_current_angle == 0:
                wrap = True
        elif index_type == "camera":
            self.i_current_camera += 1
            # Wrap the index if it goes past the end of the list
            self.i_current_camera %= len(self.cameras)
            if self.i_current_camera == 0:
                wrap = True
        elif index_type == "frame":
            self.i_current_frame += 1
            # Wrap the index if it goes past the end of the list
            self.i_current_frame %= len(self.frames)
            if self.i_current_frame == 0:
                wrap = True
        elif index_type == "object":
            self.i_current_object += 1
            # Wrap the index if it goes past the end of the list
            self.i_current_object %= len(self.objects)
            if self.i_current_object == 0:
                wrap = True
        elif index_type == "sheet":
            self.i_current_sheet += 1
            # Wrap the index if it goes past the end of the list
            self.i_current_sheet %= len(self.sheets)
            if self.i_current_sheet == 0:
                wrap = True
        elif index_type == "track":
            self.i_current_track += 1
            # Wrap the index if it goes past the end of the list
            self.i_current_track %= len(self.tracks)
            if self.i_current_track == 0:
                wrap = True

        return wrap

    def update_lists(self, level_index, reset=False):
        """ Update a list based on the output order
        This needs to be called on each iteration to make sure that lists that depend on parent lists are correctly updated,
        such as animation tracks that depend on an object
        If reset is True then the list is set to None
        """

        addon_prop = self.context.scene.addon_properties

        list_type = self.output_order[level_index]

        if list_type == "angle":
            if not reset:
                # Return the range of camera angles to loop over
                self.angles = range(0, addon_prop.int_camera_angles)
            else:
                self.angles = None
        elif list_type == "camera":
            if not reset:
                # Returns a list of pointers to the camera objects
                cameras = []
                if addon_prop.pointer_camera_one != None:
                    cameras.append(addon_prop.pointer_camera_one)
                if addon_prop.pointer_camera_two != None:
                    cameras.append(addon_prop.pointer_camera_two)
                if addon_prop.pointer_camera_three != None:
                    cameras.append(addon_prop.pointer_camera_three)
                if addon_prop.pointer_camera_four != None:
                    cameras.append(addon_prop.pointer_camera_four)
                self.cameras = cameras
            else:
                self.cameras = None
        elif list_type == "frame":
            if not reset:
                # tracks must be set
                if self.tracks:
                    # If no animations
                    if self.tracks == ["No Action"]:
                        self.frames = [0]
                    else:
                        # Get the smallest and largest frame numbers of all animation strips in the track
                        strips = self.tracks[self.i_current_track].strips
                        anim_start = None
                        anim_end = 0
                        for strip in strips:
                            if strip.frame_end > anim_end:
                                anim_end = int(strip.frame_end)
                            if anim_start == None or strip.frame_start < anim_start:
                                anim_start = int(strip.frame_start)
                        # Render the range of frame numbers for the specified animation
                        self.frames = range(anim_start, anim_end + 1)
            else:
                self.frames = None
        elif list_type == "object":
            if not reset:
                # sheets must be set
                if self.sheets:
                    self.objects = self.sheets[self.i_current_sheet]
            else:
                self.objects = None
        elif list_type == "sheet":
            if not reset:
                # Get the scenes root empty node
                output = addon_prop.pointer_output_parent
                # 2d array, where each row represents the sprite sheets, and columns represent the objects for each sprite
                # [[...],[...],[...]]
                # [.................] = List of sprite sheets
                #  [...] [...] [...]  = Lists of object pointers
                sheet_array = []
                sheet_option = addon_prop.enum_sprite_sheet
                if sheet_option in ('OFF', 'OUTPUT'):
                    # For simplification OFF will be set up as if for OUTPUT, and will simply skip the composition stage
                    # One sprite sheet containing all objects
                    sheet_array.append(find_children(output))
                elif sheet_option == 'SPRITE':
                    # Multiple sprite sheets containing multiple objects
                    for child in find_children(output):
                        sheet_array.append(find_children(child))
                elif sheet_option == 'OBJECT':
                    # Multiple sprite sheets containing a single object each
                    for child in find_children(output):
                        sheet_array.append([child])
                self.sheets = sheet_array
            else:
                self.sheets = None
        elif list_type == "track":
            if not reset:
                # objects must be set
                if self.objects:
                    obj_animations = self.objects[self.i_current_object].animation_data
                    if obj_animations:
                        self.tracks = obj_animations.nla_tracks
                    else:
                        self.tracks = ["No Action"]
            else:
                self.tracks = None

        return self.get_list(level_index)

    def get_list(self, level_index):
        """ Gets a list for a group level as specified by the output order"""

        list_type = self.output_order[level_index]

        if list_type == "angle":
            return self.angles
        elif list_type == "camera":
            return self.cameras
        elif list_type == "frame":
            return self.frames
        elif list_type == "object":
            return self.objects
        elif list_type == "sheet":
            return self.sheets
        elif list_type == "track":
            return self.tracks

    def get_item_string(self, level_index):
        """ Gets a string for use in output folders and files for a group level"""

        addon_prop = self.context.scene.addon_properties

        item_type = self.output_order[level_index]

        if item_type == "angle":
            return str(int(self.angles[self.i_current_angle] * (360 / addon_prop.int_camera_angles))).zfill(3)
        elif item_type == "camera":
            return self.cameras[self.i_current_camera].name
        elif item_type == "frame":
            return str(self.frames[self.i_current_frame]).zfill(3)
        elif item_type == "object":
            return self.objects[self.i_current_object].name
        elif item_type == "sheet":
            return self.objects[self.i_current_object].parent.name
        elif item_type == "track":
            if self.tracks != ["No Action"]:
                return self.tracks[self.i_current_track].name
            else:
                return "Static"

    def prepare_render(self):
        """Sets the visibility of objects ready for rendering"""

        addon_prop = self.context.scene.addon_properties
        global_parent = addon_prop.pointer_global_parent

        self.orig_visibility = []

        # Hide all objects
        for o in bpy.data.objects:
            self.orig_visibility.append([o, o.hide_render])
            o.hide_render = True
        # Unhide global parent hierarchy
        if global_parent != None:
            global_parent.hide_render = False
            for child in find_children(global_parent):
                child.hide_render = False

    def cleanup(self):
        """Reverts the changes made by prepare_render()"""

        # Show all objects
        if self.orig_visibility:
            for o in self.orig_visibility:
                o[0].hide_render = o[1]
        else:
            for o in bpy.data.objects:
                o.hide_render = False

        if self.iterating:
            self.iterating = False
            self.reset_scene()

    def setup_scene(self):
        """Needs to be run each render before render_scene()
        Adjusts object visibility, camera position, location and visibility and animation frame for each iteration
        """

        scn = self.context.scene
        addon_prop = self.context.scene.addon_properties
        global_parent = addon_prop.pointer_global_parent

        # Setup scene
        # Show current object and children
        self.objects[self.i_current_object].hide_render = False
        for child in find_children(self.objects[self.i_current_object]):
            child.hide_render = False
        obj_animations = self.objects[self.i_current_object].animation_data
        # Mute all tracks
        if self.tracks != ["No Action"]:
            for track in obj_animations.nla_tracks:
                track.mute = True
            # Show current track
            self.tracks[self.i_current_track].mute = False
        # Show camera hierarchy
        obj_cam = find_children(self.cameras[self.i_current_camera], 'CAMERA')[0]
        self.cameras[self.i_current_camera].hide_render = False
        for child in find_children(self.cameras[self.i_current_camera]):
            child.hide_render = False
        self.orig_scene_camera = scn.camera
        scn.camera = obj_cam
        # Move Camera to object
        self.cam_orig_location = self.cameras[self.i_current_camera].matrix_world.to_translation()
        self.cameras[self.i_current_camera].location = self.objects[self.i_current_object].matrix_world.to_translation()
        # Rotate camera
        self.cam_orig_rotation = self.cameras[self.i_current_camera].rotation_euler.z
        self.cameras[self.i_current_camera].rotation_euler.z = math.radians(self.angles[self.i_current_angle] * (360 / addon_prop.int_camera_angles))
        # Move Global to object
        if global_parent != None:
            self.global_parent_orig_location = global_parent.matrix_world.to_translation()
            global_parent.location = self.objects[self.i_current_object].matrix_world.to_translation()
        # Set frame
        self.orig_frame = scn.frame_current
        scn.frame_set(self.frames[self.i_current_frame])

    def render_scene(self):
        """Renders the scene using the current scene state as set by setup_scene()"""

        scn = self.context.scene
        addon_prop = self.context.scene.addon_properties

        # Set render path
        # <item_1>\<item_2>\<item_3>\<item_4>\<item_5>\
        output_folder = "{}{}\\{}\\{}\\{}\\{}\\".format(addon_prop.string_output_path, self.get_item_string(0), self.get_item_string(1), self.get_item_string(2), self.get_item_string(3), self.get_item_string(4))

        # Set render filename
        # <item_1>_<item_2>_<item_3>_<item_4>_<item_5>_<item_6>.<file_extension>
        output_name = "{}_{}_{}_{}_{}_{}{}".format(self.get_item_string(0), self.get_item_string(1), self.get_item_string(2), self.get_item_string(3), self.get_item_string(4), self.get_item_string(5), scn.render.file_extension)

        # Render frame
        self.orig_render_path = scn.render.filepath
        scn.render.filepath = ''.join((output_folder, output_name))
        bpy.ops.render.render(write_still=True)

        # Reset render path
        scn.render.filepath = self.orig_render_path
        self.orig_render_path = None


    def reset_scene(self):
        """Reverts the changes made by setup_scene()"""

        scn = self.context.scene
        addon_prop = self.context.scene.addon_properties
        global_parent = addon_prop.pointer_global_parent

        # Reset scene
        # Hide current object and children
        self.objects[self.i_current_object].hide_render = True
        for child in find_children(self.objects[self.i_current_object]):
            child.hide_render = True
        # Unmute all tracks
        if self.tracks != ["No Action"]:
            obj_animations = self.objects[self.i_current_object].animation_data
            for track in obj_animations.nla_tracks:
                track.mute = False
        # Hide camera hierarchy
        self.cameras[self.i_current_camera].hide_render = True
        for child in find_children(self.cameras[self.i_current_camera]):
            child.hide_render = True
        scn.camera = self.orig_scene_camera
        # Reset camera
        if self.cam_orig_location:
            self.cameras[self.i_current_camera].location = self.cam_orig_location
            self.cam_orig_location = None
        if self.cam_orig_rotation:
            self.cameras[self.i_current_camera].rotation_euler.z = self.cam_orig_rotation
            self.cam_orig_rotation = None
        # Reset global
        if global_parent != None:
            global_parent.location = self.global_parent_orig_location
            self.global_parent_orig_location = None
        # Reset frame
        if self.orig_frame:
            scn.frame_set(self.orig_frame)
            self.orig_frame = None

    def merge_images(self, folder_path, recursive=False, level=0, direction=None):
        """ Merge all images into a single image based on orientation

        The image is placed in the parent folder
        The name of the image has the end suffix removed (ie the text after the last "_" and before the extension)
        Depending on the setting chosen, the folder is then emptied and removed
        If recursive is true, check for sub folders first, merging them if found

        To correctly merge all files output by the render code leave level and direction as default
        """

        scn = self.context.scene
        addon_prop = self.context.scene.addon_properties

        merge = True

        # Loop through sub-directories first to ensure that all iamges are correctly merged
        if recursive:
            for f in os.listdir(folder_path):
                sub_folder = os.path.join(folder_path, f)
                if os.path.isdir(sub_folder):
                    self.merge_images(sub_folder, recursive, level + 1)

        # If a direction is specified, use that, otherwise base the direction on the output orientation property
        if direction:
            direction = direction.upper()
            if direction not in ('HORIZONTAL', 'VERTICAL'):
                print("Error: Unknown direction {0}, required HORIZONTAL or VERTICAL".format(direction))
                return None
        else:
            # Get direction from list
            d = self.output_orientation[level]
            if d == 'v':
                direction = 'VERTICAL'
            elif d == 'h':
                direction = 'HORIZONTAL'
            elif d == '-':
                direction = None
                merge = False

        # Merge images
        if merge:
            # Set the file paths
            p = folder_path.split('\\')
            save_path = '\\'.join(p[:-1])
            save_path += '\\'
            folder_path += '\\'

            # Get the images to be merged
            images = []
            save_name = None
            for f in os.listdir(folder_path):
                file_name = os.fsdecode(f)
                if file_name.endswith(scn.render.file_extension):
                    image_path = ''.join((folder_path, "\\", file_name))
                    print(image_path)
                    images.append(Image.open(image_path))
                    if not save_name:
                        save_name = os.path.splitext(file_name)[0]
                        n = save_name.split('_')
                        save_name = '_'.join(n[:-1])

            # Calculate the width and height for the merged image
            widths, heights = zip(*(img.size for img in images))
            output_width = None
            output_height = None
            if direction == 'HORIZONTAL':
                output_width = sum(widths)
                output_height = max(heights)
            elif direction == 'VERTICAL':
                output_width = max(widths)
                output_height = sum(heights)

            # Create the merged image
            output_image = Image.new('RGBA', (output_width, output_height))

            print("Saving as\n{0}{1}{2}".format(save_path,save_name,scn.render.file_extension))
            print("Merging {} images ...".format(len(images)), end='')
            offset = 0
            for img in images:
                if direction == 'HORIZONTAL':
                    output_image.paste(img, (offset, 0))
                    offset += img.size[0]
                elif direction == 'VERTICAL':
                    output_image.paste(img, (0, offset))
                    offset += img.size[1]

            output = ''.join((save_path,save_name,scn.render.file_extension))

            output_image.save(output)

            # Empty the folder of all images
            if not addon_prop.bool_keep_renders:
                self.empty_folder(folder_path, scn.render.file_extension)

            print(" Done")
            print("")

    def empty_folder(self, folder_path, extension):
        """ Delete all file with a specified extension in a folder, and remove the folder if it is subsequently emptied
        extension can be a tuple containing all file types to be deleted or a string if only a single type is to be deleted
        """

        for f in os.listdir(folder_path):
            file_name = os.fsdecode(f)
            if file_name.endswith(extension):
                os.remove(''.join((folder_path, "\\", file_name)))
        try:
            os.rmdir(folder_path)
        except OSError:
            print("{0}\nThis folder still contains files so has not been deleted.".format(folder_path))

    def render_iteration(self):
        """Render a single iteration
        This should only be called from iterate()
        """

        for level_index in range(0,len(self.output_order)):
            self.update_lists(level_index)
        self.setup_scene()
        self.render_scene()
        self.reset_scene()


class RenderSprites_OT_Operator(bpy.types.Operator):
    """Render the sprites as per the chosen settings.
    It loops through the sheets, objects, tracks and frames, rendering each frame.
    If enabled, it then merges the images into sprite sheets.
    Finally, it sets the scene back to its original state as best as possible.
    """

    bl_idname = 'view3d.render_sprites'
    bl_label = "Render Sprites"
    bl_description = "Render sprites based on selected options and scene setup."
    bl_context = 'VIEW_3D'

    _time = None
    stop_modal = False
    r = None

    def modal(self, context, event):
        # As validation must have passed for the button calling this operator to be enabled, the scene should be ok
        # However, since a user could potentially try to use this operator elsewhere, it is included here
        if not validate_settings(self, context):
            print("Validation Error")
            self.stop_modal = False
            return self.cancel(context)
        if event.type == 'ESC' or bpy.data.is_dirty:
            print("Cancelled Render")
            self.r.cleanup()
            self.stop_modal = False
            return self.cancel(context)
        if self.stop_modal:
            print("Finished Render")
            self.stop_modal = False
            return self.cancel(context)
        if event.type == 'TIMER':
            self.stop_modal = self.r.iterate()

        return {'PASS_THROUGH'}

    def execute(self, context):

        try:
            self.r = RenderSprites(context)
        except ValidationError:
            return {'CANCELLED'}

        print("Beginning Render")
        self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)
        return {'CANCELLED'}


class OBJECT_MT_TemplateMenu(bpy.types.Menu):
    """The Create Template dropdown menu"""

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
    """The Create Camera dropdown menu"""

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
    """The Scene Setup panel"""

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

        col = layout.column(align=True)
        if not len(bpy.context.selected_objects):
            col.enabled = False
        col.operator('view3d.origin_to_floor')


# The render setup sub panel
class ADDON_PT_SetupPanel(bpy.types.Panel):
    """The Render Setup panel"""

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
    """The Render Sprites panel"""

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
        col.prop(addon_prop, 'string_output_order')
        error = validate_output_order(self, context)
        if not error == None:
            box = col.box()
            if isinstance(error, str):
                box.label(text=error)
            else:
                for error_line in error:
                    box.label(text=error_line)
        col.prop(addon_prop, 'string_output_orientation')
        error = validate_output_orientation(self, context)
        if not error == None:
            box = col.box()
            if isinstance(error, str):
                box.label(text=error)
            else:
                for error_line in error:
                    box.label(text=error_line)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('view3d.render_sprites', icon='RENDER_RESULT')
        error = validate_render(self, context)
        if not error == None:
            box = col.box()
            box.label(text=error)
            row.enabled = False
        input_ok = validate_settings(self, context)
        if not input_ok:
            box = col.box()
            box.label(text="* Check for errors above")
            row.enabled = False
