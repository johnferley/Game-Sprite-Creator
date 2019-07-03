# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "Game Sprite Creator",
    "author" : "John Ferley",
    "description" : "This addon can render orhtogrpahic 2D game sprites from a 3D scene",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 1),
    "location" : "",
    "warning" : "",
    "category" : "Generic"
}

# Usage
#   In order for this plugin to work correctly, the scene must be set up corectly.
#   * All objects must be parented to an empty representing that sprite,
#     for example a characters hair, body and clothes must be parented to the same empty.
#   * Depending on the setting chosen in the Sprite Sheets dropdown, further empties will be required.
#       * If off, sprite sheets will not be created, each object and frame will be rendered to separate images (ie no compositing).
#           * Output Parent
#               * Object Parent
#       * If Based on Output Parent, all sprites will be on one large sprite sheet, object empties must be parented to an output empty.
#           * Output Parent
#               * Object Parent
#       * If Based on Sprite Sheet Parent, object empties will need parenting to a sprite sheet parent, and these sprite sheets parented to an output empty.
#         A sprite sheet will be created for each sprite sheet empty, with the child object empties rendered to each parent sprite sheet.
#           * Output Parent
#               * Sprite Sheet Parent
#                   * Object Parent
#       * If Based on Object Parent, a sprite sheet will be created for each object empty, object empties must be parented to an output empty.
#           * Output Parent
#               * Object Parent
#   * The top level output empty must be selected in the Output selection box.
#   * All parent objects must be empties.
#   * The above hierarchies are assumed by the program, and differences may cause issues, such as objects directly parented to the output that are not an object parent
#     or missing sprite parents.
#   * Any objects that are common to every sprite, such as a sun or ground plane, must be parented to a global empty.
#     This global empty must be selected in the Global selection box.
#   * Any objects required for each camera that must rotate with the camera, as well as the camera itseld, must be added to a camera empty.
#     This camera empty must be selected in the corresponding selection box.
#   * Note the selection box names are arbitary, the cameras do not even have to be orthographic, as the program simply rotates the camera empty so that
#     a number of images equal to the number specified in the No of Camera Angles box are rendered for each object. Multiple slection boxes are provided to allow for
#     all camera angles to be rendered at the same time.
#   * The object ratio box sets the othographic scale for the camera when created for a 1x1x1 cube (or 1x1xcos(35 + (16/60)) for the dimetric camera).
#     A ratio of 1 will fit the cube horizontally to the camera with no margin, 0.5 will mean the object is half the width, etc.
#     Note, this essentially sets the ortho scale to 1/ratio (or root(2)/ratio for the dimetric camera). A ratio of 0 will be treated as a ratio of 1.
#   * Origins for all empties must be 0,0,0. Obejct groups will be rendered one at a time, the object other groups will be hidden for that render.
#   * An animated object must have each animation for that object as a single NLA Action track. If an object has no tracks, only the first frame will be rendered for that object.
#   * NLA Animations must be pat of the object parent, all animations for all child objects will always be rendered
#   * Make sure all orphaned data has been removed
#
# To Do:
#   Make render operator show a progress indicator and allow for cancelling:
#       https://blender.stackexchange.com/questions/71454/is-it-possible-to-make-a-sequence-of-renders-and-give-the-user-the-option-to-can/71524#71524
#   Bug Testing
#   Documentation
#
# Notes
#   How should animations be handled?
#       NLA Actions? (current)
#       Animated textures?
#       Dope Sheet/Timelines/Keyframes?
#   How should orphaned data be handled?
#       Skip?
#       Delete?
#       Require User to fix? (current)
#   Use numpy for image manipulation
#
#   Require parents to be prefixed?
#       Eg ANIM for an animated object
#          OBJ for an object
#          SHEET for a sprite sheet
#   OR
#   Add to validation
#       Check scene hierarchy
#       Check parent origins

import bpy
from . addon import *

classes = (
    AddonProperties,
    CreateOrthoTemplate_OT_Operator,
    CreateDimeTemplate_OT_Operator,
    CreateTopCamera_OT_Operator,
    CreateDimeCamera_OT_Operator,
    CreateSideCamera_OT_Operator,
    CreateBirdCamera_OT_Operator,
    LoadExample_OT_Operator,
    RenderSprites_OT_Operator,
    OBJECT_MT_TemplateMenu,
    OBJECT_MT_CameraMenu,
    ADDON_PT_ScenePanel,
    ADDON_PT_SetupPanel,
    ADDON_PT_RenderPanel)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.addon_properties = bpy.props.PointerProperty(type=AddonProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.addon_properties

if __name__ == '__main__':
    register()