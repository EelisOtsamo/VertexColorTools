# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
	'name': "Vertex Color Tools",
	'author': "Eelis Otsamo",
	'version': (1, 1, 0),
	'blender': (3, 2, 0),
	'description': "Modify, select, and paint gradients using vertex colors.",
    'support': 'COMMUNITY',
	'category': 'Paint',
	'location': "View 3D > Sidebar > Edit (Edit Mode)",
	'doc_url': "https://github.com/EelisOtsamo/VertexColorTools"
}

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
	
