# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from bpy.types import Context, Mesh, Event, Operator, UILayout

from bpy.props import (
	EnumProperty,
	FloatProperty,
	FloatVectorProperty,
	BoolProperty
)

from mathutils import Vector
from math import ceil


from ..internal.color_attribute import (
	load_active_color,
	save_active_color,
)

from ..internal.types import ContextException

from ..internal.topology_gradient import (
	paint_topology_gradient,
	TopologyExtentClampMode
	)

from ..preferences import BLEND_MODE_ITEMS
from ..internal.color_utils import BLEND_MODES, INPT_MODE_ITEMS, HSV_INPT_MODES, RGB_INTP_MODES, HSL_INPT_MODES, OKLAB_INTP_MODES
from .shared import poll_active_color_attribute, INTP_MODE_ITEMS, HUE_INPT_MODE_ITEMS


TOPOLOGY_GRADIENT_MOUSE_SENSITIVITY = 5.0

TOPO_EXTENT_CLAMP_MODE_ITEMS = [
	(TopologyExtentClampMode.MINIMUM.value, "Minimum", "Clamp to the shortest face sequence"), 
	(TopologyExtentClampMode.MAXIMUM.value, "Maximum", "Clamp to the longest face sequence"),
	(TopologyExtentClampMode.INDIVIDUAL.value, "Individual", "Clamp each face sequence individually"), 
]

class EDITVERTCOL_OT_PaintGradientTopology(Operator):
	bl_idname = "vertex_color_edit_tools.paint_gradient_topology"
	bl_label = "Paint Vertex Color Topology Gradient"
	bl_description = "Paint a gradient into the current vertex color attribute following the selection topology"
	bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

	blend_mode: EnumProperty(
		name="Blending Mode",
		default='MIX',
		items=BLEND_MODE_ITEMS,
		description="The blending mode used to mix colors")

	interpolation_color_mode: EnumProperty(
			name="Color Mode",
			items=INPT_MODE_ITEMS,
			default='RGB',
			description="The color mode to use for interpolation")
	
	interpolation_type: EnumProperty(
			name="RGB Interpolation",
			items=INTP_MODE_ITEMS,
			default='LINEAR',
			description="The interpolation type to use for rgb interpolation ")
	
	interpolation_hue_type: EnumProperty(
			name="HSV Interpolation",
			items=HUE_INPT_MODE_ITEMS,
			default='NEAR',
			description="The interpolation type to use for hsv interpolation ")

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
		default=(0.0, 0.0, 0.0, 0.0),
		soft_min=0.0,
		soft_max=1.0,
		precision=3,
		size=4,
		description="Color for the end point of the gradient")

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

	distance: FloatProperty(
		name="Gradient Distance",
		subtype='DISTANCE',
		default= 1.0,
		precision=3,
		description="Length of the gradient")
	
	direction: FloatVectorProperty(
		name="Direction",
		subtype='XYZ',
		default=(0,0,1),
		precision=3,
		size=3,
		description="Overall direction of the gradient")

	mirror: BoolProperty(
			name="Mirror Gradient",
			default=False,
			description="Mirror the gradient")
	
	extent_clamp_mode: EnumProperty(
		name="Clamp Extents",
		items=TOPO_EXTENT_CLAMP_MODE_ITEMS,
		default='MINIMUM',
		description="Determines whether to end the gradient when there are no more faces to paint")
	
	
	
	def __init__(self):
		self._snap = False
		self._distance = 0.0
		self._start_coord = None
		self._stored_colors = None

	@classmethod
	def poll(cls, context: Context):
		return poll_active_color_attribute(cls, context)

	def execute(self, context: Context):
		blend_func = BLEND_MODES[self.blend_mode][0]

		object = context.active_object
		mesh: Mesh = object.data

		match self.interpolation_color_mode:
			case 'RGB':
				intp_func = RGB_INTP_MODES[self.interpolation_type][0]
			case 'HSV':
				intp_func = HSV_INPT_MODES[self.interpolation_hue_type][0]
			case 'HSL':
				intp_func = HSL_INPT_MODES[self.interpolation_hue_type][0]
			case 'OKLAB':
				intp_func = OKLAB_INTP_MODES[self.interpolation_type][0]


		extent_clamp_mode = TopologyExtentClampMode(self.extent_clamp_mode)
		try:
			paint_topology_gradient(
				mesh,
				self.mirror,
				intp_func,
				blend_func,
				self.clip_colors,
				(self.factor_begin,
				self.factor_end),
				(self.color_begin,
				self.color_end),
				self.distance,
				extent_clamp_mode,
				self.direction)
			
		except ContextException as e:
			self.report({'ERROR_INVALID_INPUT'}, e.args[0])
			return {'CANCELLED'}

		return {'FINISHED'}
	

	def update_status(self, context: Context):
		header = (f"Topology Gradient: {self.distance: .3f}, LMB: Confirm, ESC/RMB: Cancel, "
			+ f"M: Toggle Mirror ({'ON' if self.mirror else 'OFF'}), "
			+ f"CTRL: Toggle Snap ({'ON' if self._snap else 'OFF'}), "
			+ f"H: Toggle Color Clip ({'ON' if self.clip_colors else 'OFF'})")
		
		context.area.header_text_set(header)


	@staticmethod
	def static_draw(data, layout: UILayout):
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
		grid.prop(data, 'distance')
		grid.prop(data, 'mirror')
		grid.prop(data, 'extent_clamp_mode')
		grid.prop(data, 'direction')


	def draw(self, context: Context):
		self.static_draw(self, self.layout)

	def invoke(self, context: Context, event: Event):
		mesh: Mesh = context.active_object.data

		self._start_coord = Vector((event.mouse_x, event.mouse_y))
		self._stored_colors = save_active_color(mesh)

		context.window_manager.modal_handler_add(self) # Start modal
		return {'RUNNING_MODAL'}

	def modal(self, context: Context, event: Event):
		context.area.tag_redraw()
		mesh: Mesh = context.active_object.data

		do_refresh = False

		if self._snap == event.ctrl:
			self._snap = not event.ctrl
			self.update_status(context)
			do_refresh = True

		if event.type == 'MOUSEMOVE':
			# Refresh
			rv3d = context.region_data
			
			coord = Vector((event.mouse_x, event.mouse_y))
			factor = rv3d.view_distance * TOPOLOGY_GRADIENT_MOUSE_SENSITIVITY
			diff = coord - self._start_coord
			relative_diff = Vector((diff[0] / context.region.width, diff[1] / context.region.height)) * factor
			self._distance = relative_diff.length
			r = Vector(rv3d.view_matrix[0][:3])
			u = Vector(rv3d.view_matrix[1][:3])
			self.direction[:] = (diff[0] * r + diff[1] * u)[:]
			self.direction.normalize()
			load_active_color(mesh, self._stored_colors)
			self.update_status(context)
			do_refresh = True
			
		if event.value == 'PRESS':
			match event.type:
				case 'H':
					self.clip_colors = not self.clip_colors
					self.update_status(context)
					do_refresh = True
					
				case 'M':
					self.mirror = not self.mirror
					self.update_status(context)
					do_refresh = True

				case 'LEFTMOUSE':
					self.modal_cleanup(context=context)
					return {'FINISHED'}

				case 'RET' :
					# Alternative confirm
					self.modal_cleanup(context=context)
					return {'FINISHED'}
							
				case 'ESC' | 'RIGHTMOUSE':
					# Cancel
					load_active_color(mesh, self._stored_colors)
					self.modal_cleanup(context)
					return {'CANCELLED'}

		if do_refresh:
			self.distance = ceil(self._distance) if self._snap else self._distance
			load_active_color(mesh, self._stored_colors)
			if 'FINISHED' not in self.execute(context):
				self.modal_cleanup(context)
				return {'CANCELLED'}

		return {'RUNNING_MODAL'}
	
	
	def modal_cleanup(self, context: Context):
		context.area.header_text_set(None)



classes = (
	EDITVERTCOL_OT_PaintGradientTopology,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
