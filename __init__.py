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
    "version" : (0, 0, 2),
    "location" : "",
    "warning" : "",
    "category" : "Generic"
}

import bpy
from . game_sprite_addon import *

classes = (
    AddonProperties,
    CreateOrthoTemplate_OT_Operator,
    CreateDimeTemplate_OT_Operator,
    CreateTopCamera_OT_Operator,
    CreateDimeCamera_OT_Operator,
    CreateSideCamera_OT_Operator,
    CreateBirdCamera_OT_Operator,
    OriginToFloor_OT_Operator,
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
