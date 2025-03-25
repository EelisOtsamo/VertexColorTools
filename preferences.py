# SPDX-License-Identifier: GPL-3.0-or-later

# type: ignore

from bpy.types import (
	PropertyGroup,
	Scene,
	AddonPreferences)

import bpy.utils
from bpy.props import (
    FloatProperty,
	CollectionProperty,
	FloatVectorProperty,
	EnumProperty,
	BoolProperty,
	PointerProperty)

from .internal.color_utils import BLEND_MODE_ITEMS, srgb_to_linear
from bpy.app.handlers import persistent

class VCOLTOOLS_AddonPreferences(AddonPreferences):
	bl_idname = __package__
	
	_property_callbacks: dict = {}

	@classmethod
	def register_callback(cls, attribute_name: str, callback):
		if not attribute_name in cls._property_callbacks:
			cls._property_callbacks[attribute_name] = []
		cls._property_callbacks[attribute_name].append(callback)


	def notify(self, attribute_name: str):
		for callback in self._property_callbacks.get(attribute_name, []):
			callback(self.get(attribute_name))


	paint_palettes_enabled: bpy.props.BoolProperty(default=False, options={'SKIP_SAVE'})

	paint_palette_addon_compatibility: bpy.props.BoolProperty(
		name="Paint Palette Intergration",
		default=True,
		description="Enable to use the Blender built-in Paint Palette add-on for color palettes, if it is enabled",
		update=lambda self, _: self.notify("paint_palette_addon_compatibility"),
	)

	def draw(self, context):
		layout = self.layout
		row = layout.row()
		row.prop(self, "paint_palette_addon_compatibility")
		layout.label(text="Note: Requires the \"Paint Palettes\" add-on from extensions.blender.org to be enabled")
		layout.label(text="Paint Palette colors cannot store the alpha channel and values are limited to 0-1")



class VCOLTOOLS_PropertyGroup(PropertyGroup):
	'''
	Contains configuration used for painting vertex colors from the Edit panel
	'''

	blend_mode: EnumProperty(
		name="Blending Mode",
		default='MIX',
		items=BLEND_MODE_ITEMS,
		description="The blending mode used to mix colors")

	brush_color: FloatVectorProperty(
		name="Color",
		subtype='COLOR',
		default=(1.0, 1.0, 1.0, 1.0),
		soft_min=0.0,
		soft_max=1.0,
		precision=3,
		size=4,
		description="The color used for painting")

	factor: FloatProperty(
		name="Factor",
		subtype='FACTOR',
		default=1.00,
		soft_min=0.0,
		soft_max=1.0,
		step=1,
		precision=3,
		description="The factor value passed to the blending function")

	clip_colors: BoolProperty(
		name="Clip Colors",
		default=True,
		description="Clip the color values between 0 and 1. (Byte colors are always clipped)")

	active_only: BoolProperty(
		name="Active Corner Only",
		default=False,
		description='Paint only the active face corner of the selected face. Allows painting single vertices even when the color attribute is split between faces')


class VCOLTOOLS_PaletteColor(PropertyGroup):
	color: FloatVectorProperty(
		name="Color 1",
		subtype='COLOR',
		default=(1.0, 1.0, 1.0, 1.0),
		soft_min=0.0,
		soft_max=1.0,
		precision=3,
		size=4)

def load_palette_defaults(palette):
	palette.clear()
	for i in range(8):
		gray_value = srgb_to_linear(float(i) / 7)
		item: VCOLTOOLS_PaletteColor = palette.add()
		item.color = (gray_value, gray_value, gray_value, 1)


@persistent
def _post_load_handler(_) -> None:
	palette = bpy.context.scene.EditVertexColorsPalette
	if not palette or len(palette) != 0:
		return
	load_palette_defaults(palette)


def addon_preferences() -> VCOLTOOLS_AddonPreferences:
	return bpy.context.preferences.addons[__package__].preferences



classes = (
	VCOLTOOLS_AddonPreferences,
	VCOLTOOLS_PaletteColor,
	VCOLTOOLS_PropertyGroup
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	Scene.EditVertexColorsProperties = PointerProperty(
		type=VCOLTOOLS_PropertyGroup)
	Scene.EditVertexColorsPalette = CollectionProperty(
		type=VCOLTOOLS_PaletteColor)
	bpy.app.handlers.load_post.append(_post_load_handler)


def unregister():
	bpy.app.handlers.load_post.remove(_post_load_handler)
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	del Scene.EditVertexColorsProperties
	del Scene.EditVertexColorsPalette

