# SPDX-License-Identifier: GPL-3.0-or-later

# type: ignore

import addon_utils
import bpy
import sys
import importlib

from .internal.color_utils import (
	srgb_to_linear,
	linear_to_srgb
)

from .preferences import (EDITVERTCOL_PropertyGroup, addon_preferences,)

_PAINT_PALETTES_MOD_NAME = 'bl_ext.blender_org.paint_palettes'
_UNPATCHED_CURRENT_BRUSH = None

def get_paint_palettes_module():
	_, loaded_state = addon_utils.check(_PAINT_PALETTES_MOD_NAME)
	if not loaded_state:
		return None
	return sys.modules.get(_PAINT_PALETTES_MOD_NAME)

	
def _disable_paint_palette_compat():
	global _UNPATCHED_CURRENT_BRUSH
	prefs = addon_preferences()
	mod = get_paint_palettes_module()
	if prefs.paint_palettes_enabled and mod:
		# Remove the monkeypatch
		mod.current_brush = _UNPATCHED_CURRENT_BRUSH

	_UNPATCHED_CURRENT_BRUSH = None
	prefs.paint_palettes_enabled = False


def _enable_paint_palette_compat():
	def _check_paint_pallettes_addon():
		prefs = addon_preferences()
		mod = get_paint_palettes_module()
		if mod:
			prefs.paint_palettes_enabled = True
			_monkeypatch_palette_compat(mod)
			
	bpy.app.timers.register(_check_paint_pallettes_addon, first_interval=0)


def _monkeypatch_palette_compat(mod):
	'''
	Patch functions of the paint_palettes addon module
	'''
	global _UNPATCHED_CURRENT_BRUSH
	_UNPATCHED_CURRENT_BRUSH = mod.current_brush

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

	def patched_current_brush():
		brush = _UNPATCHED_CURRENT_BRUSH()

		if brush:
			return brush

		context = bpy.context
		if context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH' and context.edit_object:
			brush = BrushProxy()
		else:
			brush = None
		return brush

	mod.current_brush = patched_current_brush


def _on_palette_addon_compat_changed(is_enabled: bool):
	if is_enabled:
		_enable_paint_palette_compat()
	else:
		_disable_paint_palette_compat()


def register():
	# Palette module might not be loaded yet
	prefs = addon_preferences()

	prefs.register_callback('paint_palette_addon_compatibility', _on_palette_addon_compat_changed)
	
	if prefs.paint_palette_addon_compatibility:
		_enable_paint_palette_compat()


def unregister():
	_disable_paint_palette_compat()