# SPDX-License-Identifier: GPL-3.0-or-later

import bpy

from bpy.types import Operator, Context, Object, Mesh

from bpy.props import (
	EnumProperty,
	FloatProperty,
	BoolProperty,
)

from .shared import poll_active_color_attribute

from ..internal.color_attribute import bright_contrast_color_attribute


class VCOLTOOLS_OT_Convert(Operator):
	bl_idname = "vertex_color_edit_tools.convert"
	bl_label = "Convert Color Attribute"
	bl_description = "Change the format of the active color attribute. Vertex color information may be lost"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	domain: EnumProperty(name="Domain", default='POINT', items=[
		('POINT', "Point", ""), ('CORNER', "Corner", "")])
	
	data_type: EnumProperty(name="Data Type", default='FLOAT_COLOR', items=[
		('FLOAT_COLOR', "Float Color", ""), ('BYTE_COLOR', "Byte Color", "")])

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)
	
	def execute(self, context: Context):
		bpy.ops.object.mode_set(mode='OBJECT')
		bpy.ops.geometry.color_attribute_convert(
			domain=self.domain, data_type=self.data_type)
		bpy.ops.object.mode_set(mode='EDIT')
		return {'FINISHED'}

	def invoke(self, context: Context, event):
		return context.window_manager.invoke_confirm(self, event)



class VCOLTOOLS_OT_Duplicate(Operator):
	bl_idname = "vertex_color_edit_tools.duplicate"
	bl_label = "Duplicate Color Attribute"
	bl_description = "Duplicate the active color attribute"
	bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		bpy.ops.object.mode_set(mode='OBJECT')
		bpy.ops.geometry.color_attribute_duplicate()
		bpy.ops.object.mode_set(mode='EDIT')
		return {'FINISHED'}


	

class VCOLTOOLS_OT_BrightContrast(Operator):
	bl_idname = "vertex_color_edit_tools.bright_contrast"
	bl_label = "Brightness/Contrast"
	bl_description = "Adjust vertex color brightness / contrast"
	bl_options = {'REGISTER', 'UNDO'}


	brightness: FloatProperty(
		name = "Brightness",
		default = 1.00,
		step = 1,
		precision = 3,
	)
	
	contrast: FloatProperty(
		name = "Contrast",
		default = 1.00,
		step = 10,
		precision = 1,
	)

	clip_colors: BoolProperty(
		name = "Clip Colors",
		default = True,
		description = "Clip the color values between 0 and 1. (Byte colors are always clipped)")

	selected_only: BoolProperty(
		name = "Selected Only",
		default = False,
		description = "Only modify the selected elements")

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		object: Object = context.active_object # pyright: ignore[reportAssignmentType]
		mesh: Mesh = object.data # pyright: ignore[reportAssignmentType]
		bright_contrast_color_attribute(mesh,
								  self.brightness,
								  self.contrast,
								  self.selected_only,
								  self.clip_colors)
		return {'FINISHED'}




classes = (
	VCOLTOOLS_OT_Convert,
	VCOLTOOLS_OT_Duplicate,
	VCOLTOOLS_OT_BrightContrast
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
