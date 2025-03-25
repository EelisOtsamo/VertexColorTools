# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from bpy.types import Context, SpaceView3D, Mesh, Operator
import bpy.utils
from bpy.props import (
	FloatProperty,
	FloatVectorProperty,
	EnumProperty,
	BoolProperty)

from ..internal.color_attribute import (
	set_selection_color,
	clip_color_attribute,
	select_similar_color,
	select_linked,
	copy_active_color_to_selected)

from ..internal.types import ContextException

from ..preferences import BLEND_MODE_ITEMS
from ..internal.color_utils import BLEND_MODES
from .shared import poll_active_color_attribute
		

class EDITVERTCOL_OT_PaintColor(Operator):
	bl_idname = "vertex_color_edit_tools.paint_color"
	bl_label = "Paint Vertex Colors"
	bl_description = "Set selected vertex colors"
	bl_options = {'REGISTER', 'UNDO'}

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
		description="Paint only the active face corner of the selected face. Allows painting single vertices even when the color attribute is split between faces")

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		blend_func = BLEND_MODES[self.blend_mode][0]

		mesh: Mesh = context.active_object.data # type: ignore
		
		try:
			set_selection_color(
				mesh,
				self.active_only,
				blend_func,
				self.factor,
				self.brush_color,
				self.clip_colors)

		except ContextException as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0])
			return {'CANCELLED'}

		return {'FINISHED'}


class EDITVERTCOL_OT_SelectLinkedVertexColor(Operator):
	bl_idname = "vertex_color_edit_tools.select_linked_color"
	bl_label = "Select Linked Vertex Color"
	bl_description = "Select elements connected to the active element with similar vertex color"
	bl_options = {'REGISTER', 'UNDO'}

	threshold: FloatProperty(
		name="Threshold", default=0.0, subtype='FACTOR', soft_min=0, soft_max=1)
	
	ignore_alpha: BoolProperty(
		name="Ignore Alpha", description="Ignore alpha component when comparing colors", default=True)

	deselect: BoolProperty(
		name="Deselect", description="Deselect all matching elements", default=False)

	check_corners: BoolProperty(
		name="Corners", description="Check for faces linked by vertices instead of edges", default=False)

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)
	
	def draw(self, context: Context):
		layout = self.layout
		layout.use_property_split = True
		layout.prop(self, 'threshold')
		layout.prop(self, 'deselect')

		if context.active_object.data.color_attributes.active_color.domain == 'CORNER': # pyright: ignore (Validated in `poll`)
			layout.prop(self, 'check_corners')
		layout.prop(self, 'ignore_alpha')


	def execute(self, context: Context):
		mesh: Mesh = context.active_object.data # type: ignore

		if mesh.total_vert_sel == 0:
			self.report({'ERROR_INVALID_INPUT'}, "No selection")
			return {'FINISHED'}

		try:
			select_linked(mesh,
				 	self.check_corners,
					self.threshold,
					self.ignore_alpha,
					self.deselect)
		except ContextException as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0])
			return {'CANCELLED'}

		return {'FINISHED'}


class EDITVERTCOL_OT_SelectSimilarVertexColor(Operator):
	bl_idname = "vertex_color_edit_tools.select_similar_color"
	bl_label = "Select Similar Vertex Color"
	bl_description = "Select similar vertices or faces by the vertex colors of the current selection"
	bl_options = {'REGISTER', 'UNDO'}

	threshold: FloatProperty(
		name="Threshold", default=0.0, subtype='FACTOR', soft_min=0, soft_max=1)
	
	ignore_alpha: BoolProperty(
		name="Ignore Alpha", description="Ignore alpha component when comparing colors", default=True)
	
	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		mesh: Mesh = context.active_object.data # type: ignore

		if mesh.total_vert_sel == 0:
			self.report({'ERROR_INVALID_INPUT'}, "No selection")
			return {'FINISHED'}

		try:
			select_similar_color(mesh,
					self.threshold,
					self.ignore_alpha)
		except ContextException as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0])
			return {'CANCELLED'}

		return {'FINISHED'}



class EDITVERTCOL_OT_Clip(Operator):
	bl_idname = "vertex_color_edit_tools.clip_all"
	bl_label = "Clip All Vertex Colors"
	bl_description = "Clip the color components of the current color attribute between 0 and 1"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		mesh: Mesh = context.active_object.data # type: ignore
		clip_color_attribute(mesh)
		return {'FINISHED'}


class EDITVERTCOL_OT_CopyColorToSelected(Operator):
	bl_idname = "vertex_color_edit_tools.copy_active_color_to_selected"
	bl_label = "Copy Color Attribute to Selected from Active"
	bl_description = "Transfer color attribute from active face to selected"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		mesh: Mesh = context.active_object.data # type: ignore

		try:
			copy_active_color_to_selected(mesh)
		except ContextException as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0])
			return {'CANCELLED'}

		return {'FINISHED'}


class EDITVERTCOL_OT_Preview(Operator):
	bl_idname = "vertex_color_edit_tools.preview"
	bl_label = "Viewport Preview"
	bl_description = "Set viewport mode to preview vertex colors"

	@classmethod
	def poll(cls, context: Context):
		if not (isinstance(context.space_data, SpaceView3D)):
			cls.poll_message_set("Current space is not a 3D View space.")
			return False
		return True

	def invoke(self, context: Context, event):
		space: SpaceView3D = context.space_data # pyright: ignore[reportAssignmentType]
		space.shading.color_type = 'VERTEX'
		space.shading.type = 'SOLID'
		return {'FINISHED'}


classes = (
	EDITVERTCOL_OT_PaintColor,
	EDITVERTCOL_OT_Preview,
	EDITVERTCOL_OT_Clip,
	EDITVERTCOL_OT_SelectSimilarVertexColor,
	EDITVERTCOL_OT_CopyColorToSelected,
	EDITVERTCOL_OT_SelectLinkedVertexColor
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
