# Game-Sprite-Creator
Blender 2.8 addon for creating sprites for 2D games.

## Features
* Camera pre-sets for top down, dimetric/2:1 isometric, side view and bird's eye view cameras.
* Automatic rendering of multiple objects to individual renders, including animations.
* Automatic creation of sprite sheets using PIL.

## Requirements
In order to create the sprite sheets from the individual renders this plugin requires Python Pillow 6.1.0.
The addon will be able to render the individual images without Pillow.

To install Pillow for Blender in Windows:
1. Open Command Prompt or PowerShell.
2. Navigate to the Python bin folder included with Blender:

   `cd 'path\to\blender\2.80\python\bin'`

3. Make sure pip is installed:

   `.\python -m ensurepip`

   `.\python -m pip install –upgrade pip setuptools wheel`

4. Install Pillow:

   `.\python -m pip install Pillow`

## How to use
### UI
![UI Screenshot](https://github.com/johnferley/Game-Sprite-Creator/blob/master/images/ui.png)

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
     The orthographic scale of the camera will be set based on Object Ratio and Object Size.

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
     Sub-folders will be created containing all the renders in the following pattern:

     'sprite sheet name\object name\camera name\angle\track name\'

     The track name folder will not be included if the Object Parent has no NLA tracks.

     The rendered images will be named as follows:

     'sprite sheet name_object name_camera name_angle_track name_frame number.png'

     The track name and frame number will be omitted if the Object Parent has no NLA tracks.
     The merged sprite sheets will contain a subset of this file name based on the images it's made up of.

   * Render Sprites

     Renders the scene based on the settings above.
     If there are any errors, displayed as boxes below the property containing an error, this button will be disabled.

### Scene Setup

The addon renders the scene based on its hierarchy, as detailed above, depending on the settings.

* If Off is selected, the scene will be rendered as individual images only, see 'example_off.blend'.

* For rendering all objects to a single large sheet:

  * Use the 'Based on Output Parent' Sprite Sheet option.
  * Objects animations will first be rendered frame by frame and aligned horizontally.
    These will then be merged vertically with the other animations for that object, and the animations for other objects.
  * For an example see 'example_output.blend'.

* For rendering specific objects to specific sprite sheets:

  * Use the 'Based on Sprite Sheet Parent' Sprite Sheet option.
  * Objects animations will first be rendered frame by frame and aligned horizontally.
    These will then be merged vertically with the other animations for that object.
    The object sheets will then be merged with other objects that are parented to the same Sprite Sheet Parent.
  * For an example see 'example_sprite.blend'.

* For rendering objects to individual sprite sheets for each object:

  * Use the 'Based on Object Parent' Sprite Sheet option.
  * Objects animations will be rendered frame by frame and aligned horizontally, with no further processing.
  * For an example see 'example_object.blend'.

### Rendering
When running Blender will appear to become unresponsive.
It is recommended to display the System Console using the Window>Toggle System Console menu when running this addon as progress notifications will be output as the process runs.
It is also only possible to cancel the operation by forcing Blender to close, so the file must be saved before starting the rendering process.
The render button will be disabled until the file has been saved.

Large numbers of objects and long animations can cause the rendering process to take a long time

## License
See [LICENSE.md](../master/LICENSE)

The character and animations included in the example files are from [Mixamo](https://www.mixamo.com).
