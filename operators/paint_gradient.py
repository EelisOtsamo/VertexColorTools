# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.types import Context, Mesh, Event, Operator, UILayout, SpaceView3D

from bpy.props import (
	EnumProperty,
	FloatProperty,
	FloatVectorProperty,
	BoolProperty
)

import mathutils
from mathutils import Vector

import gpu
import gpu_extras

from bpy_extras import view3d_utils

from ..internal.color_attribute import (
	load_active_color,
	save_active_color,
)


from ..internal.gradient import (
	paint_gradient,
	GradientType, 
	GradientSharpEdgeMode,
	GradientExtendMode
	)

from ..preferences import BLEND_MODE_ITEMS
from ..internal.color_utils import BLEND_MODES, INPT_MODE_ITEMS, HSV_INPT_MODES, OKLAB_INTP_MODES, RGB_INTP_MODES, HSL_INPT_MODES
from .shared import poll_active_color_attribute, INTP_MODE_ITEMS, HUE_INPT_MODE_ITEMS

from enum import Enum


class AxisMode(Enum):
	NONE = None
	X = 0
	Y = 1
	Z = 2
	LX = 3
	LY = 4
	LZ = 5

GRADIENT_TYPE_ITEMS = [
	(GradientType.LINEAR.value, "Linear", ""),
	(GradientType.RADIAL.value, "Radial", "")
]

GRADIENT_SHARP_MODE_ITEMS = [
	(GradientSharpEdgeMode.OFF.value,		"Off",		"All face corners within the boundary are colored"),
	(GradientSharpEdgeMode.VERTEX.value,	"Vertex",	"Face corners at the boundary are colored while taking adjacent faces into account"),
	(GradientSharpEdgeMode.FACE.value,		"Face",		"Only faces that are completely withing the boundary are colored"),
]

GRADIENT_EXTEND_MODE_ITEMS = [
	(GradientExtendMode.OFF.value,		"Off",		"Gradient is contained within the defined bounds"),
	(GradientExtendMode.FORWARD.value,	"Forward",	"Gradient extends in front of the end-point"),
	(GradientExtendMode.BACKWARD.value,	"Backward",	"Gradient extends behind the start-point"),
	(GradientExtendMode.BOTH.value,		"Both",		"Gradient extends both behind and in front of the bounds")
]

SNAP_MODE_ITEMS = [
	('SURFACE', "Surface", "Snap to geometry"),
	('CURSOR', "Cursor", "Use 3D cursor")
]

class EDITVERTCOL_OT_PaintGradient(Operator):
	bl_idname = "edit_vertex_colors.paint_gradient"
	bl_label = "Paint Vertex Color Gradient"
	bl_description = "Paint a gradient into the current vertex color attribute"
	bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

	plane_depth: EnumProperty(
			name="Depth",
			items=SNAP_MODE_ITEMS,
			default='SURFACE',
			description="Depth used for placing the gradient points")

	gradient_type: EnumProperty(
			name="Gradient Type",
			items=GRADIENT_TYPE_ITEMS,
			default='LINEAR',
			description="The gradient type to use")
	
	interpolation_color_mode: EnumProperty(
			name="Color Mode",
			items=INPT_MODE_ITEMS,
			default='RGB',
			description="The color mode to use for interpolation")
	
	interpolation_type: EnumProperty(
			name="Interpolation",
			items=INTP_MODE_ITEMS,
			default='LINEAR',
			description="The interpolation type to use.")
	
	interpolation_hue_type: EnumProperty(
			name="HSV Interpolation",
			items=HUE_INPT_MODE_ITEMS,
			default='NEAR',
			description="The interpolation type to use for hsv interpolation ")

	blend_mode: EnumProperty(
		name="Blending Mode",
		default='MIX',
		items=BLEND_MODE_ITEMS,
		description="The blending mode used to mix colors")

	color_begin: FloatVectorProperty(
		name="Color Begin",
		subtype='COLOR',
		default=(1.0, 1.0, 1.0, 1.0),
		soft_min=0.0,
		soft_max=1.0,
		precision=3,
		size=4,
		description="Color for the start point of the gradient")
	
	color_end: FloatVectorProperty(
		name="Color End",
		subtype='COLOR',
		default=(0.0, 0.0, 0.0, 1.0),
		soft_min=0.0,
		soft_max=1.0,
		precision=3,
		size=4,
		description="Color for the end point of the gradient")
	
	position_begin: FloatVectorProperty(
		name="Gradient Start",
		subtype='TRANSLATION',
		default=(0.0, 0.0, 0.0),
		precision=3,
		size=3,
		description="Start position of the gradient in global space")
	
	position_end: FloatVectorProperty(
		name="Gradient End",
		subtype='TRANSLATION',
		default=(0.0, 0.0, 1.0),
		precision=3,
		size=3,
		description="End position of the gradient in global space")

	factor_begin: FloatProperty(
		name="Factor Start",
		subtype='FACTOR',
		default=1.00,
		soft_min=0.0,
		soft_max=1.0,
		step=1,
		precision=3,
		description="Factor value passed to the blending function for the start of the gradient")
	
	factor_end: FloatProperty(
		name="Factor End",
		subtype='FACTOR',
		default=1.00,
		soft_min=0.0,
		soft_max=1.0,
		step=1,
		precision=3,
		description="Factor value passed to the blending function for the end of the gradient")

	clip_colors: BoolProperty(
		name="Clip Colors",
		default=True,
		description="Clip the color values between 0 and 1. (Byte colors are always clipped)")

	selected_only: BoolProperty(
			name="Selected Only",
			default=False,
			description="Gradient only affects selected vertices")
	
	extend_mode: EnumProperty(
			name="Extend Mode",
			items=GRADIENT_EXTEND_MODE_ITEMS,
			default='OFF',
			description="Extend gradient past start and end points")
	
	sharp_edge_mode: EnumProperty(
			name="Sharp Edge Mode",
			items=GRADIENT_SHARP_MODE_ITEMS,
			default='FACE',
			description="How to handle vertices near the boundary of the gradient when using face corner colors")
	

	class PaintState(Enum):
		NONE = 0
		FIRST = 1
		BOTH = 2

	AXIS_DIR = [Vector((1,0,0)),
		Vector((0,1,0)),
		Vector((0,0,1)),]

	AXIS_TEXT = [
		"X", "Y", "Z", "Local X", "Local Y","Local Z"
	]

	def __init__(self):
		self._snap = False
		self._axis_dir = Vector()
		self._axis = AxisMode.NONE
		self._state = self.PaintState.NONE
		self._bvhtree: mathutils.bvhtree.BVHTree
		self._draw_handler: None
		if not bpy.app.background:
			self._shader_smooth_color = gpu.shader.from_builtin('SMOOTH_COLOR')
		self._viz_position = Vector()
		self._viz_color = Vector((0.75, 0.26, 0.2, 1.0))
		self._viz_color_begin = Vector((0.26,0.75, 0.2, 0.0))
		self._viz_color_end = Vector((0.56,0.33,0.02, 0.0))


	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		blend_func = BLEND_MODES[self.blend_mode][0]

		object = context.active_object
		mesh: Mesh = object.data
		inv_world_mat = object.matrix_world.inverted_safe()
		position_begin_obj = inv_world_mat @ self.position_begin
		position_end_obj = inv_world_mat @ self.position_end


		gradient_type = GradientType(self.gradient_type)
		extend_mode = GradientExtendMode(self.extend_mode)
		sharp_edge_mode = GradientSharpEdgeMode(self.sharp_edge_mode)
		match self.interpolation_color_mode:
			case 'RGB':
				intp_func = RGB_INTP_MODES[self.interpolation_type][0]
			case 'HSV':
				intp_func = HSV_INPT_MODES[self.interpolation_hue_type][0]
			case 'HSL':
				intp_func = HSL_INPT_MODES[self.interpolation_hue_type][0]
			case 'OKLAB':
				intp_func = OKLAB_INTP_MODES[self.interpolation_type][0]

		paint_gradient(
			mesh,
			self.selected_only,
			extend_mode,
			sharp_edge_mode,
			gradient_type,
			intp_func,
			blend_func,
			self.clip_colors,
			(self.factor_begin,
			self.factor_end),
			(self.color_begin,
			self.color_end),
			(position_begin_obj,
			position_end_obj))

		return {'FINISHED'}
	
	@staticmethod
	def draw_callback_px(self, context: Context):
		gpu.state.blend_set('ALPHA')
		gpu.state.line_width_set(8)
		gpu.state.point_size_set(10)
		if self._state != self.PaintState.NONE:
			batch = gpu_extras.batch.batch_for_shader(
				self._shader_smooth_color, 'LINE_STRIP', 
				{"color": [self.color_begin, self.color_end], "pos": [self.position_begin, self.position_end]}
			)
			batch.draw(self._shader_smooth_color)

		batch = gpu_extras.batch.batch_for_shader(
			self._shader_smooth_color, 'POINTS', 
			{"color": [self._viz_color, self._viz_color_begin, self._viz_color_end],"pos": [self._viz_position, self.position_begin, self.position_end]}
		)
		batch.draw(self._shader_smooth_color)

		gpu.state.point_size_set(1)
		gpu.state.line_width_set(1.0)
		gpu.state.blend_set('NONE')
		
		

	def get_mouse_3d_pos(self, context: Context, event: Event):
		region = context.region
		rv3d = context.region_data
		coord = event.mouse_region_x, event.mouse_region_y

		ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
		ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)

		if self._state == self.PaintState.FIRST and self._axis != AxisMode.NONE:
			axis_start = self.position_begin
			axis_end = axis_start + self._axis_dir
			axis = (axis_end - axis_start).normalized()
			a, b = mathutils.geometry.intersect_line_line(ray_origin, ray_direction * 1000, axis_start - axis * 1000, axis_end + axis * 1000)
			if self._snap:
				return self.snap_to_vert(context, b)
			return b

		fallback_depth_pos = self.position_begin if self._state != self.PaintState.NONE else context.scene.cursor.location

		depsgraph = context.evaluated_depsgraph_get()
		result, hit_location, normal, index, object, matrix = context.scene.ray_cast(depsgraph, ray_origin, ray_direction, distance=1.70141e+38)
		
		if not result:
			return view3d_utils.region_2d_to_location_3d(region, rv3d, coord, fallback_depth_pos)

		if not self._snap or object != context.active_object:
			# Allow snapping to vertices even when in CURSOR depth mode
			if self.plane_depth == 'CURSOR':
				return view3d_utils.region_2d_to_location_3d(region, rv3d, coord, fallback_depth_pos)
			else:
				return hit_location
		
		return self.snap_to_vert(context, hit_location)

	def snap_to_vert(self, context: Context, co: Vector) -> Vector:
		inv_world_mat = context.active_object.matrix_world.inverted_safe()
		find_co = inv_world_mat @ co
		co, index, dist = self._kd.find(find_co)
		return context.active_object.matrix_world @ co

	@staticmethod
	def static_draw(data, layout: UILayout):
		layout.prop(data, 'gradient_type', text="Type")
		layout.prop(data, 'blend_mode', text="Blend")
		row = layout.row(align=True, heading="Interpolation")
		row.use_property_split = False
		row.prop(data, 'interpolation_color_mode', text="")

		match data.interpolation_color_mode:
			case 'RGB' | 'OKLAB':
				row.prop(data, 'interpolation_type', text="")
			case 'HSV' | 'HSL':
				row.prop(data, 'interpolation_hue_type', text="")

		layout.separator()
		grid = layout.grid_flow(row_major=True,columns=2, even_columns=True, even_rows=True)
		grid.use_property_split = False
		grid.prop(data, 'color_begin', icon_only=True)
		grid.prop(data, 'color_end', icon_only=True)
		grid.prop(data, 'factor_begin')
		grid.prop(data, 'factor_end')
		
		grid = layout.grid_flow()
		grid.prop(data, 'clip_colors')
		grid.prop(data, 'selected_only')
		grid.prop(data, 'extend_mode')
		grid.prop(data, 'sharp_edge_mode')
		
		layout.separator()
		layout.prop(data, 'position_begin')
		layout.prop(data, 'position_end')


	def draw(self, context: Context):
		self.static_draw(self, self.layout)
		

	def invoke(self, context: Context, event: Event):
		self.set_paint_state(context, self.PaintState.NONE)
		self._viz_color.w = 1
		self._viz_color_begin.w = 0
		self._viz_color_end.w = 0

		mesh: Mesh = context.active_object.data

		self._stored_colors = save_active_color(mesh)
	
		self._draw_handler = SpaceView3D.draw_handler_add(self.draw_callback_px, (self, context), 'WINDOW', 'POST_VIEW')
		
		context.window_manager.modal_handler_add(self) # Start modal

		self._kd = mathutils.kdtree.KDTree(len(mesh.vertices))
		depsgraph = context.evaluated_depsgraph_get()
		self._bvhtree = mathutils.bvhtree.BVHTree.FromObject(bpy.context.active_object, depsgraph)

		for i, v in enumerate(mesh.vertices):
			self._kd.insert(v.co, i)

		self._kd.balance()
		self._viz_position = self.get_mouse_3d_pos(context, event)
		return {'RUNNING_MODAL'}


	def set_axis_mode(self, context: Context, axis_mode: AxisMode):
		self._axis = axis_mode
		if self._axis == AxisMode.NONE:
			return
		self._axis_dir = self.AXIS_DIR[self._axis.value % 3]
		if self._axis.value > 2:
			# local
			o = context.active_object
			m = o.matrix_world.to_quaternion()
			self._axis_dir = m @ self._axis_dir
		self.update_status(context)


	def set_paint_state(self, context: Context, new_state: PaintState):
		self._state = new_state
		self.update_status(context)
	

	def update_status(self, context: Context):
		header = "Paint Gradient: "

		extend_mode_name = self.extend_mode
		sharp_edge_mode_name = self.sharp_edge_mode
		axis_name = self.AXIS_TEXT[self._axis.value] if self._axis.value is not None else "OFF"
		match self._state:
			case self.PaintState.NONE:
				header += "LMB: Add Point, ESC/RMB: Cancel"
			case self.PaintState.FIRST:
				header += "LMB: Add Point, RMB: Delete Point, ESC: Cancel"
			case self.PaintState.BOTH:
				header += "LMB/↵/␣: Confirm, RMB: Delete Point, ESC: Cancel"
		
		header += (
			f", S: Toggle Selected ({'ON' if self.selected_only else 'OFF'}), " 
			+ f"F: Toggle Sharp ({sharp_edge_mode_name}), "
			+ f"E: Cycle Extend ({extend_mode_name}), "
			+ f"SHIFT-TAB: Toggle Snap ({'ON' if self._snap else 'OFF'}), "
			+ f"H: Toggle Color Clip ({'ON' if self.clip_colors else 'OFF'}), "
			+ f"XYZ: Orientation Lock ({axis_name})")

		context.area.header_text_set(header)

	def cycle_extend_mode(self):
		match GradientExtendMode(self.extend_mode):
			case GradientExtendMode.OFF:
				self.extend_mode = GradientExtendMode.FORWARD.value
			case GradientExtendMode.FORWARD:
				self.extend_mode = GradientExtendMode.BACKWARD.value
			case GradientExtendMode.BACKWARD:
				self.extend_mode = GradientExtendMode.BOTH.value
			case GradientExtendMode.BOTH:
				self.extend_mode = GradientExtendMode.OFF.value


	def cycle_sharp_mode(self):
		match GradientSharpEdgeMode(self.sharp_edge_mode):
			case GradientSharpEdgeMode.OFF:
				self.sharp_edge_mode = GradientSharpEdgeMode.FACE.value
			case GradientSharpEdgeMode.FACE:
				self.sharp_edge_mode = GradientSharpEdgeMode.VERTEX.value
			case GradientSharpEdgeMode.VERTEX:
				self.sharp_edge_mode = GradientSharpEdgeMode.OFF.value

	def modal(self, context: Context, event: Event):
		context.area.tag_redraw()

		mesh: Mesh = context.active_object.data

		# Allow navigation
		if event.type in ['MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE']:
			return {'PASS_THROUGH'}
				
		do_refresh = False
		do_cursor_refresh = False
		if event.type == 'MOUSEMOVE':
			do_cursor_refresh = True

		if event.value == 'PRESS':
			match event.type:
				case 'TAB':
					if event.shift:
						self._snap = not self._snap
						do_refresh = True
						do_cursor_refresh = True
				case 'E':
					self.cycle_extend_mode()
					do_refresh = True
				case 'H':
					self.clip_colors = not self.clip_colors
					do_refresh = True
				case 'F':
					self.cycle_sharp_mode()
					do_refresh = True
				case 'S':
					self.selected_only = not self.selected_only
					do_refresh = True
				case 'X':
					if self._axis == AxisMode.X:
						self.set_axis_mode(context, AxisMode.LX)
					elif self._axis == AxisMode.LX:
						self.set_axis_mode(context, AxisMode.NONE)
					else:
						self.set_axis_mode(context, AxisMode.X)
					do_refresh = True
				case 'Y':
					if self._axis == AxisMode.Y:
						self.set_axis_mode(context, AxisMode.LY)
					elif self._axis == AxisMode.LY:
						self.set_axis_mode(context, AxisMode.NONE)
					else:
						self.set_axis_mode(context, AxisMode.Y)
					do_refresh = True
				case 'Z':
					if self._axis == AxisMode.Z:
						self.set_axis_mode(context, AxisMode.LZ)
					elif self._axis == AxisMode.LZ:
						self.set_axis_mode(context, AxisMode.NONE)
					else:
						self.set_axis_mode(context, AxisMode.Z)
					do_refresh = True
					
				case 'LEFTMOUSE':
					# Go forward in states
					match self._state:
						case self.PaintState.NONE:
							self.position_begin = self.get_mouse_3d_pos(context, event)
							self.position_end = self.position_begin.copy()
							self._viz_color_begin.w = 1.0
							self.set_paint_state(context, self.PaintState.FIRST)
							self.update_status(context)
						case self.PaintState.FIRST:
							self.position_end = self.get_mouse_3d_pos(context, event)
							self._viz_color_end.w = 1.0
							self._viz_color.w = 0.0
							self.set_paint_state(context, self.PaintState.BOTH)
							self.update_status(context)
						case self.PaintState.BOTH:
							self.modal_cleanup(context=context)
							return {'FINISHED'}
						
				case 'RET' if self._state == self.PaintState.BOTH:
					# Alternative confirm
					self.modal_cleanup(context=context)
					return {'FINISHED'}
				
				case 'RIGHTMOUSE':
					# Go backward in states
					match self._state:
						case self.PaintState.NONE:
							load_active_color(mesh, self._stored_colors)
							self.modal_cleanup(context)
							return {'CANCELLED'}
						
						case self.PaintState.FIRST:
							self.set_axis_mode(context, AxisMode.NONE)
							load_active_color(mesh, self._stored_colors)
							self._viz_color_begin.w = 0.0
							self.set_paint_state(context, self.PaintState.NONE)
							do_refresh = True

						case self.PaintState.BOTH:
							self.set_axis_mode(context, AxisMode.NONE)
							self._viz_color_end.w = 0.0
							self._viz_color.w = 1.0
							self.set_paint_state(context, self.PaintState.FIRST)
							self.position_end = self.get_mouse_3d_pos(context, event)
							do_refresh = True
							
				case 'ESC':
					# Cancel
					load_active_color(mesh, self._stored_colors)
					self.modal_cleanup(context)
					return {'CANCELLED'}
				
		if do_cursor_refresh:
			# Refresh cursor positions
			match self._state:
				case self.PaintState.FIRST:
					self.position_end = self.get_mouse_3d_pos(context, event)
					load_active_color(mesh, self._stored_colors)
					do_refresh = True
			self._viz_position = self.get_mouse_3d_pos(context, event)

		if do_refresh:
			# Re-run execute
			self.update_status(context)
			if self._state != self.PaintState.NONE:
				load_active_color(mesh, self._stored_colors)
				self.execute(context)

		return {'RUNNING_MODAL'}
	

	def modal_cleanup(self, context: Context):
		context.area.header_text_set(None)
		SpaceView3D.draw_handler_remove(self._draw_handler, 'WINDOW')
		context.area.tag_redraw()




classes = (
	EDITVERTCOL_OT_PaintGradient,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
