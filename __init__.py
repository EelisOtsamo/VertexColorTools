# SPDX-License-Identifier: GPL-3.0-or-later

if "bpy" in locals():
	import importlib
	if "ui" in locals():
		importlib.reload(ui)
	if "tools" in locals():
		importlib.reload(tools)
	if "paint_palette_compat" in locals():
		importlib.reload(paint_palette_compat)
	if "preferences" in locals():
		importlib.reload(preferences)
	if "operators" in locals():
		importlib.reload(operators)


import bpy

from . import preferences, tools, operators, ui, paint_palette_compat


def register():
	operators.register()

	preferences.register()
	paint_palette_compat.register()

	if not bpy.app.background:
		ui.register()
		tools.register_tools()


def unregister():
	if not bpy.app.background:
		tools.unregister_tools()
		ui.unregister()

	paint_palette_compat.unregister()
	preferences.unregister()

	operators.unregister()
	
