# SPDX-License-Identifier: GPL-3.0-or-later

from . import sidepanel

import bpy

from ..operators.edit import (EDITVERTCOL_OT_PaintColor,
	EDITVERTCOL_OT_CopyColorToSelected,
	EDITVERTCOL_OT_Clip,
	EDITVERTCOL_OT_SelectSimilarVertexColor,
	)

from ..operators.sidepanel import (
	EDITVERTCOL_OT_Apply
)


def draw_context_menu(self, context: bpy.types.Context):
	self.layout.separator()
	self.layout.operator(EDITVERTCOL_OT_Apply.bl_idname, icon='BRUSH_DATA')

def draw_select_similar(self, context: bpy.types.Context):
	self.layout.operator(EDITVERTCOL_OT_SelectSimilarVertexColor.bl_idname, text="Vertex Color")

def draw_edit_mesh(self, context: bpy.types.Context):
	self.layout.separator()
	self.layout.menu(EDITVERTCOL_MT_EditMesh.bl_idname)


class EDITVERTCOL_MT_EditMesh(bpy.types.Menu):
	bl_label = "Vertex Color"
	bl_idname = "EDITVERTCOL_MT_edit_mesh"

	def draw(self, context):
		self.layout.operator(EDITVERTCOL_OT_PaintColor.bl_idname)
		self.layout.operator(EDITVERTCOL_OT_CopyColorToSelected.bl_idname)
		self.layout.operator(EDITVERTCOL_OT_Clip.bl_idname)

classes = (
	EDITVERTCOL_MT_EditMesh,
)

submodules = (
	sidepanel,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	for mod in submodules:
		mod.register()

	bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(draw_context_menu)
	bpy.types.VIEW3D_MT_edit_mesh_select_similar.append(draw_select_similar)
	bpy.types.VIEW3D_MT_edit_mesh_vertices.append(draw_edit_mesh)


def unregister():
	bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(draw_context_menu)
	bpy.types.VIEW3D_MT_edit_mesh_select_similar.remove(draw_select_similar)
	bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(draw_edit_mesh)

	for mod in reversed(submodules):
		mod.unregister()

	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

