# SPDX-License-Identifier: GPL-3.0-or-later


import bpy

from bpy.types import Context, Event, Mesh, Operator, Attribute
import bpy.utils

from bpy.props import (
	BoolProperty,
	IntProperty
)
import mathutils

from ..internal.color_utils import BLEND_MODES, srgb_to_linear

from ..internal.color_attribute import (
	get_selection_color,
	get_active_corner_color,
	set_selection_color)

from ..internal.types import ContextException

from ..preferences import (
	VCOLTOOLS_PropertyGroup,
	load_palette_defaults,
	addon_preferences,
)

from ..paint_palette_compat import get_paint_palettes_module

from .shared import poll_active_color_attribute


class VCOLTOOLS_OT_Apply(Operator):
	bl_idname = "vertex_color_edit_tools.apply"
	bl_label = "Paint Vertex Colors"
	bl_description = "Set selected vertex colors"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		mesh: Mesh = context.active_object.data # type: ignore
		props: VCOLTOOLS_PropertyGroup = context.scene.EditVertexColorsProperties
		blend_func = BLEND_MODES[props.blend_mode][0]
		try:
			set_selection_color(
				mesh,
				props.active_only,
				blend_func,
				props.factor,
				props.brush_color,
				props.clip_colors)

		except ContextException as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0])
			return {'CANCELLED'}

		return {'FINISHED'}


class VCOLTOOLS_OT_CopyActiveCorner(Operator):
	bl_idname = "vertex_color_edit_tools.copy_active_corner"
	bl_label = "Copy Active Face Corner Vertex Color"
	bl_description = "Copy the vertex color from the active corner of the selected face. (Shift + Click to only copy to the clipboard)"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	clipboard_only: BoolProperty(
		name="Only copy to clipboard",
		default=False
	)

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def invoke(self, context: Context, event: Event):
		self.clipboard_only = event.shift

		self.execute(context)
		return {'FINISHED'}

	def execute(self, context: Context):
		props: VCOLTOOLS_PropertyGroup = context.scene.EditVertexColorsProperties
		mesh: Mesh = context.active_object.data # type: ignore

		color_attribute: Attribute = mesh.color_attributes.active_color # pyright: ignore[reportAssignmentType]
		select_mode = context.scene.tool_settings.mesh_select_mode

		if color_attribute.domain != 'CORNER':
			self.report({'ERROR_INVALID_CONTEXT'}, "Color attribute must be using the Face Corner domain")
			return {'FINISHED'}

		if mesh.total_face_sel != 1:
			self.report({'ERROR_INVALID_INPUT'}, "Exactly one face must be selected")
			return {'FINISHED'}

		if not select_mode[0]:
			self.report({'ERROR_INVALID_INPUT'}, "Vertex selection mode required")
			return {'FINISHED'}

		try:
			selection_color = get_active_corner_color(mesh)
		except ContextException as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0])
			return {'FINISHED'}
	
		if color_attribute.data_type == 'BYTE_COLOR':
			selection_color[:3] = [srgb_to_linear(c) for c in selection_color[:3]]
			

		if not self.clipboard_only:
			props.brush_color = selection_color

		context.window_manager.clipboard = vector_clipboard_format(selection_color)

			
		return {'FINISHED'}



class VCOLTOOLS_OT_CopySelected(Operator):
	bl_idname = "vertex_color_edit_tools.copy_selected"
	bl_label = "Copy Selected Vertex Color"
	bl_description = "Copy vertex color from current selection.  (Shift + Click to only copy to the clipboard)"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	clipboard_only: BoolProperty(
		name="Only copy to clipboard",
		default=False
	)
	
	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)
	
	def invoke(self, context: Context, event: Event):
		self.clipboard_only = event.shift

		self.execute(context)
		return {'FINISHED'}

	def execute(self, context: Context):
		props: VCOLTOOLS_PropertyGroup = context.scene.EditVertexColorsProperties
		mesh: Mesh = context.active_object.data # type: ignore

		color_attribute: Attribute = mesh.color_attributes.active_color # pyright: ignore[reportAssignmentType]
		if mesh.total_vert_sel == 0:
			self.report({'ERROR_INVALID_INPUT'}, "No selection")
			return {'FINISHED'}

		try:
			selection_color = get_selection_color(mesh)
			
		except ContextException as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0])
			return {'FINISHED'}
		
		if color_attribute.data_type == 'BYTE_COLOR':
			selection_color[:3] = [srgb_to_linear(c) for c in selection_color[:3]]

		if not self.clipboard_only:
			props.brush_color = selection_color

		context.window_manager.clipboard = vector_clipboard_format(selection_color)

		return {'FINISHED'}




class VCOLTOOLS_OT_PaletteColorReset(Operator):
	bl_idname = "vertex_color_edit_tools.palette_color_reset"
	bl_label = "Load Default Palette"
	bl_description = "Replaces the palette colors with the default palette"
	bl_options = {'REGISTER', 'INTERNAL'}

	def invoke(self, context: Context, event):
		return context.window_manager.invoke_confirm(self, event)

	def execute(self, context: Context):
		load_palette_defaults(context.scene.EditVertexColorsPalette)
		return {'FINISHED'}
	

class VCOLTOOLS_OT_PaletteColorAdd(Operator):
	bl_idname = "vertex_color_edit_tools.palette_color_add"
	bl_label = "Add Palette Color"
	bl_description = "Add the current color to the palette"
	bl_options = {'REGISTER', 'INTERNAL'}


	def execute(self, context: Context):
		props: VCOLTOOLS_PropertyGroup = context.scene.EditVertexColorsProperties
		palette = context.scene.EditVertexColorsPalette
		item = palette.add()
		item.color = props.brush_color

		return {'FINISHED'}
	
class VCOLTOOLS_OT_PaletteColorRemove(Operator):
	bl_idname = "vertex_color_edit_tools.palette_color_remove"
	bl_label = "Remove Palette Color"
	bl_description = "Remove the latest color from the palette"
	bl_options = {'REGISTER', 'INTERNAL'}


	def execute(self, context: Context):
		props: VCOLTOOLS_PropertyGroup = context.scene.EditVertexColorsProperties
		
		palette = context.scene.EditVertexColorsPalette
		num_colors = len(palette)
		if num_colors == 0:
			return {'FINISHED'}
		
		for i, col in enumerate(palette):
			if col == props.brush_color:
				palette.remove(i)
				return {'FINISHED'}
			
		palette.remove(num_colors - 1)
		return {'FINISHED'}


class VCOLTOOLS_OT_PaletteColorSelect(Operator):
	bl_idname = "vertex_color_edit_tools.palette_select_color"
	bl_label = "Select Palette Color"
	bl_description = "Select color (SHIFT to quick apply, CTRL to select and apply)"
	bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

	color_index: IntProperty()

	@classmethod
	def poll(cls, context: Context):
		return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

	def invoke(self, context: Context, event: Event):
		if event.shift:
			return self.execute(context)
		elif event.ctrl:
			self.execute(context)
		
		if addon_preferences().paint_palettes_enabled and get_paint_palettes_module():
			palette_props = context.scene.palette_props 
			palette_props.current_color_index = self.color_index
			get_paint_palettes_module().update_panels() # pyright: ignore[reportOptionalMemberAccess]

		else:
			palette = context.scene.EditVertexColorsPalette
			props: VCOLTOOLS_PropertyGroup = context.scene.EditVertexColorsProperties
			props.brush_color = palette[self.color_index].color
		return {'FINISHED'}


	def execute(self, context: Context):
		props: VCOLTOOLS_PropertyGroup = context.scene.EditVertexColorsProperties

		if addon_preferences().paint_palettes_enabled and get_paint_palettes_module():
			palette_props = context.scene.palette_props
			palette_color = palette_props.colors[self.color_index].color

			color = [0.0, 0.0, 0.0, 1.0]
			color[:3] = [srgb_to_linear(c) for c in palette_color[:3]]
			
		else:
			palette = context.scene.EditVertexColorsPalette
			color = palette[self.color_index].color

		try:
			bpy.ops.vertex_color_edit_tools.paint_color(
				blend_mode	= props.blend_mode,
				brush_color	= color,
				factor		= props.factor,
				clip_colors	= props.clip_colors,
				active_only	= props.active_only
			)
		except Exception as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0].split("poll() ")[-1])
			return {'CANCELLED'}


		return {'FINISHED'}




def vector_clipboard_format(vec: mathutils.Vector) -> str:
	return f"[{','.join([str(v) for v in vec])}]"



classes = (
	VCOLTOOLS_OT_Apply,
	VCOLTOOLS_OT_CopySelected,
	VCOLTOOLS_OT_CopyActiveCorner,
	VCOLTOOLS_OT_PaletteColorAdd,
	VCOLTOOLS_OT_PaletteColorRemove,
	VCOLTOOLS_OT_PaletteColorReset,
	VCOLTOOLS_OT_PaletteColorSelect
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
