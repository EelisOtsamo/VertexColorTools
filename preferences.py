# SPDX-License-Identifier: GPL-2.0-or-later

from bpy.types import PropertyGroup, Scene
import bpy.utils
from bpy.props import (
    FloatProperty,
	CollectionProperty,
	FloatVectorProperty,
	EnumProperty,
	BoolProperty,
	PointerProperty)

from .internal.color_utils import BLEND_MODE_ITEMS
from bpy.app.handlers import persistent

class EDITVERTCOL_PropertyGroup(PropertyGroup):
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


class EDITVERTCOL_PaletteColor(PropertyGroup):
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
		item: EDITVERTCOL_PaletteColor = palette.add()
		item.color = (float(i) / 7, float(i) / 7,float(i) / 7,1)


@persistent
def _post_load_handler(_) -> None:
	palette = bpy.context.scene.EditVertexColorsPalette
	if not palette or len(palette) != 0:
		return
	load_palette_defaults(palette)


classes = (
	EDITVERTCOL_PropertyGroup,
	EDITVERTCOL_PaletteColor
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	Scene.EditVertexColorsProperties = PointerProperty(
		type=EDITVERTCOL_PropertyGroup)
	Scene.EditVertexColorsPalette = CollectionProperty(
		type=EDITVERTCOL_PaletteColor)
	bpy.app.handlers.load_post.append(_post_load_handler)


def unregister():
	bpy.app.handlers.load_post.remove(_post_load_handler)
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	del Scene.EditVertexColorsProperties
	del Scene.EditVertexColorsPalette

