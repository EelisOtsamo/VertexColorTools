# SPDX-License-Identifier: GPL-3.0-or-later

import addon_utils
import bpy
import sys
import importlib

from .internal.color_utils import (
	srgb_to_linear,
	linear_to_srgb
)

from .preferences import (EDITVERTCOL_PropertyGroup, addon_preferences, palette_addon)


def check_paint_pallette_addon():
	loaded_modules: list = addon_utils.modules()
	for mod in loaded_modules:
		if (mod.bl_info.get('name') == 'Paint Palettes') and (mod.bl_info.get('author') == "Dany Lebel (Axon D)"):
			initialize_paint_palette_compat(sys.modules['paint_palette'])
			return
	

def initialize_paint_palette_compat(mod):
	prefs = addon_preferences()

	prefs.palette_addon_enabled = True
	
	monkeypatch_palette_compat(mod)


def disable_paint_palette_compat():
	prefs = addon_preferences()

	loaded_default, loaded_state = addon_utils.check("paint_palettes")
	if prefs.palette_addon_enabled and loaded_state:
		# Reimport the palette addon
		importlib.reload(palette_addon())
	
	prefs.palette_addon_enabled = False



def enable_paint_palette_compat():
	bpy.app.timers.register(check_paint_pallette_addon, first_interval=0)


def monkeypatch_palette_compat(mod):
	# Patch functions of the paint_palette addon module

	class BrushProxy:
		# This class allows the paint palette addon to modify our color properties,
		# even though we are not using a bpy.types.Brush to store our properties
		
		@property
		def color(self):
			props: EDITVERTCOL_PropertyGroup = bpy.context.scene.EditVertexColorsProperties
			return [linear_to_srgb(c) for c in props.brush_color[:3]]
		
		@color.setter
		def color(self, value: tuple[float,float,float]):
			props: EDITVERTCOL_PropertyGroup = bpy.context.scene.EditVertexColorsProperties
			props.brush_color[:3] = [srgb_to_linear(c) for c in value[:3]]


	current_brush_SUPER = mod.current_brush
	def current_brush():
		brush = current_brush_SUPER()

		if brush:
			return brush

		context = bpy.context
		if context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH' and context.edit_object:
			brush = BrushProxy()
		else:
			brush = None
		return brush

	mod.current_brush = current_brush


def _on_palette_addon_compat_changed(is_enabled: bool):
	if is_enabled:
		enable_paint_palette_compat()
	else:
		disable_paint_palette_compat()


def register():
	# Palette module might not be loaded yet
	prefs = addon_preferences()

	prefs.register_callback('paint_palette_addon_compatibility', _on_palette_addon_compat_changed)
	
	if prefs.paint_palette_addon_compatibility:
		enable_paint_palette_compat()


def unregister():
	disable_paint_palette_compat()