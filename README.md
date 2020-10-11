# Game-Sprite-Creator v2beta
Blender 2.8 addon for creating sprites for 2D games.

## Changelog
* v2.1
  * Corrected the rotation of the Dimetric Parent in the example scene so that it is 0&#176; rather than 315&#176;.
  * Corrected pip installation command (--update had been auto-formatted to –update).
  * The scene should now be correctly reset after the script has run.

* v2.0beta
  * Added move origin to floor function that sets the origin for selected objects so that z = 0.
  * Additional options to change the output grouping.
  * More complex scene resetting, takes into account original render visibility.

## Notes on v2beta
The main rendering loop has been dramatically changed from v1.
The plugin has been tested, but only on a limited number of setting combinations, other combinations will be tested when I have time.
Please report any bugs, and make sure to include the error log and the current settings.
Rendering may take marginally longer than in v1, if you have a particularly large scene and can live without the changes above it may be preferable to continue using v1.
Due to the changes Blender will no longer hang, pressing Esc or causing changes that require saving will cancel the rendering process.

## Features
* Camera pre-sets for top down, dimetric/2:1 isometric, side view and bird's eye view cameras.
* Automatic rendering of multiple objects to individual renders, including animations.
* Automatic creation of sprite sheets using PIL.
* Additional convenience tools

## Requirements
In order to create the sprite sheets from the individual renders this plugin requires Python Pillow 6.1.0.
The addon will be able to render the individual images without Pillow.

To install Pillow for Blender in Windows:
1. Open Command Prompt or PowerShell.
2. Navigate to the Python bin folder included with Blender:

   `cd 'path\to\blender\2.80\python\bin'`

3. Make sure pip is installed:

   `.\python -m ensurepip`

   `.\python -m pip install --upgrade pip setuptools wheel`

4. Install Pillow:

   `.\python -m pip install Pillow`

## How to use
### UI
![UI Screenshot](https://github.com/johnferley/Game-Sprite-Creator/blob/master/images/ui_v2.png)

From top to bottom:
1. Scene Setup section
   * Load Example Scene

     Loads 'example.blend' from the Blender folder

   * Create Template

     Creates wireframe bounding cubes for use as templates.
     The dimetric bounding cube has been scaled to properly fit a grid from a dimetric/2:1 isometric camera view.

   * Object Ratio

     The ratio of object to margin for the camera created by the Add dropdown.
     Can be any value from 0 to 1, a value of 0 will be treated as if it was 1.
     A value of 1 will fit an object to the camera horizontally, 0.5 will cause the object to be half the width of the image.

   * Object Size

     The size of the object to scale the camera to.
     This is the length of the side of a cube that completely contains the target object.

   * Add

     Adds a camera rotated and scaled to match the specified type.

   * Move Origin to Floor

     Sets the origin of all selected objects so that z = 0.

2. Render Setup
   * No of Camera Angles

     The number of angles to render each object from.
     Camera parent empties will be rotated by an angle such that this number of images are rendered for each object and frame.

   * Camera 1 to Camera 4

     The parent object for each camera.
     This parent must be an empty and must have a camera parent.
     If there is more than one child camera, only the first one will be used.
     As well as a camera child object, this can contain any other type of object that needs rotating with the camera, such as lighting.

   * Output

     The parent object of the scene hierarchy.
     The parent must be an empty and must have a chid object.

     Depending on the option chosen in the Sprite Sheets dropdown, the hierarchy must be as follows:

     * Off, Based on Output Parent or Based on Object Parent:

        * Output Parent
           * Object Parent
           * ...
           * Object Parent

     * Based on Sprite Sheet Parent:

        * Output Parent
           * Sprite Sheet Parent
              * Object Parent
              * ...
              * Object Parent
           * ...
           * Sprite Sheet Parent
              * Object Parent
              * ...
              * Object Parent

     Where Sprite Sheet Parent is an empty with at least one child.
     Any animations must be NLA Tracks belonging to the Object Parent.
     Any type of object can be parented to an Object Parent and will be included in renders for that object.

   * Global

     The parent object of all objects common to every render.
     The parent, if there is one, must be an empty and must have a chid object.
     This object is optional.
     It can contain any object that must not be rotated with the camera that needs including in every render.

   * Keep Individual Renders

     If enabled, all individual renders generated by this addon will be kept.
     If disabled these individual renders will be removed, leaving only the merged sprite sheets.

   * Sprite Sheets

     This dropdown specifies exactly how the renders will be merged, and how the scene hierarchy needs to be setup (see Output above)

     The dropdown contains the following options:

     * Off

       No sprite sheets will be created.
       Keep Individual Renders will be ignored and treated as if it was enabled.
       This is the only option usable if Pillow is not installed.

     * Based on Output Parent

       A single large sprite sheet will be created containing all child Objects Parents of the Output Parent.

     * Based on Sprite Sheet Parent

       A sprite sheet will be created for each child Sprite Sheet Parent of the Output Parent.

     * Based on Object Parent

       A sprite sheet will be created for each child Object Parent of the Output Parent

3. Render Sprites
   * Output Path

     The folder to output the renders and sprite sheets to.
     Sub-folders will be created containing all the renders based on Group Order as specified below.

     The rendered images will be named based on Group Order as specified below.
     The merged sprite sheets will contain a subset of this file name based on the groups it's made up of.

   * Group Order

     The order in which to arrange the render folders and image merge grouping.

     Use the following values without quotes, separated by commas:

     * 'angle' - The camera angles as specified above.
     * 'camera' - The cameras as specified above.
     * 'frame' - The frames of each track, must be placed somewhere after 'track'.
     * 'object' - The objects as specified above, must be placed somewhere after 'sheet'.
     * 'sheet' - The sprite sheets as specified above, this must be the first element.
     * 'track' - The animation tracks for each object, must be placed somewhere after 'object'.

     All six values must be used, and follow the ordering rules as listed.

     For example 'sheet,object,camera,track,angle,frame' will create files in the following path:
     'output path\sheet\object\camera\track\angle\sheet_object_camera_track_angle_frame.png'
     Note that the last level is not given a folder to avoid having folders containing a single file.

     As the renders are merged levels will be stripped from the path.
     For example after completing the frames loop for an angle the path would be:
     'output path\sheet\object\camera\track\angle\sheet_object_camera_track_angle.png'

   * Output Orientation

     Sets the orientation each group gets merged in, if merging is enabled.

     Use 'h' and 'v' separated by commas, with each value corresponding to a value in Group Order.

     * 'h' - Merge the images horizontally
     * 'v' - Merge the images vertically

     The first group, which must be sheet, does not get merged and so has an orientation of '-'.
     There must be a value for every group.

     For example '-,v,h,v,v,h' with the example group above will set the orientations as follows:

     * sheet - Not applicable, does not get merged.
     * object - Merged vertically.
     * camera - Merged horizontally.
     * track - Merged vertically.
     * angle - Merged vertically.
     * frame - Merged horizontally.

   * Render Sprites

     Renders the scene based on the settings above.
     If there are any errors, displayed as boxes below the property containing an error, this button will be disabled.

### Scene Setup

The addon renders the scene based on its hierarchy, as detailed above, depending on the settings.

* If Off is selected, the scene will be rendered as individual images only, see 'example_off.blend'.

* For rendering all objects to a single large sheet:

  * Use the 'Based on Output Parent' Sprite Sheet option.
  * For an example see 'example_output.blend'.

* For rendering specific objects to specific sprite sheets:

  * Use the 'Based on Sprite Sheet Parent' Sprite Sheet option.
  * For an example see 'example_sprite.blend'.

* For rendering objects to individual sprite sheets for each object:

  * Use the 'Based on Object Parent' Sprite Sheet option.
  * For an example see 'example_object.blend'.

### Rendering
When running the process can be cancelled by pressing Esc.
Making any changes that cause the file to require saving will also cause the process to end.
It is recommended to display the System Console using the Window>Toggle System Console menu when running this addon as progress notifications will be output as the process runs.
The render button will be disabled until the file has been saved and all errors have been fixed.

Large numbers of objects and long animations can cause the rendering process to take a long time.
v2beta also takes slightly longer to run that v1.
This may not be noticeable depending on the computer, however for large machines using v1 may allow for the rendering to be completed sooner.

## License
See [LICENSE.md](../master/LICENSE)

The character and animations included in the example files are from [Mixamo](https://www.mixamo.com).
