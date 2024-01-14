# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Operator, Context

from bpy.props import (
	EnumProperty,
	FloatProperty,
	BoolProperty,
)

from ..internal.color_utils import BLEND_MODE_ITEMS

from .shared import poll_active_color_attribute

from ..internal.color_attribute import bright_contrast_color_attribute


class EDITVERTCOL_OT_Convert(Operator):
	bl_idname = "edit_vertex_colors.convert"
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



class EDITVERTCOL_OT_Duplicate(Operator):
	bl_idname = "edit_vertex_colors.duplicate"
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


	

class EDITVERTCOL_OT_BrightContrast(Operator):
	bl_idname = "edit_vertex_colors.bright_contrast"
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
		object: bpy.types.Object = context.active_object
		mesh: bpy.types.Mesh = object.data
		bright_contrast_color_attribute(mesh,
								  self.brightness,
								  self.contrast,
								  self.selected_only,
								  self.clip_colors)
		return {'FINISHED'}




classes = (
	EDITVERTCOL_OT_Convert,
	EDITVERTCOL_OT_Duplicate,
	EDITVERTCOL_OT_BrightContrast
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
