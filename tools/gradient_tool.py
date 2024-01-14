# SPDX-License-Identifier: GPL-2.0-or-later

from pathlib import Path
import bpy.types
from bpy.types import Context, WorkSpaceTool, UILayout

from ..operators.paint_gradient import EDITVERTCOL_OT_PaintGradient


class GradientTool(WorkSpaceTool):
	bl_idname = 'edit_vertex_colors.gradient_tool'
	bl_space_type = 'VIEW_3D'
	bl_context_mode = 'EDIT_MESH'
	bl_label = 'Vertex Color Gradient'
	bl_icon = (Path(__file__).parent.parent / "ui" / 'icons' / "edit_vertex_colors.paint_gradient").as_posix()
	bl_keymap = (
			(
				EDITVERTCOL_OT_PaintGradient.bl_idname, 
				{"type": 'RIGHTMOUSE', "value": 'PRESS'},
				{"properties": []},
			),
	)

	def draw_settings(context: Context, layout: UILayout, tool: WorkSpaceTool, extra = False):
		props = tool.operator_properties(EDITVERTCOL_OT_PaintGradient.bl_idname)

		region_is_header = bpy.context.region.type == 'TOOL_HEADER'

		if not region_is_header:
			EDITVERTCOL_OT_PaintGradient.static_draw(props, layout)
			return

		if not extra:
			layout.prop(props, 'plane_depth')
			layout.prop(props, 'gradient_type')
			layout.prop(props, 'blend_mode')

			row = layout.row(align=True, heading="Color Begin")
			row.prop(props, 'color_begin', icon_only=True)
			row.prop(props, 'factor_begin', text="")

			row = layout.row(align=True, heading="Color End")
			row.prop(props, 'color_end', icon_only=True)
			row.prop(props, 'factor_end', text="")

			layout.prop(props, 'selected_only')
			layout.prop(props, 'extend_mode')
			layout.prop(props, 'sharp_edge_mode')

			layout.popover('TOPBAR_PT_tool_settings_extra', text="...")

		if extra:
			layout.use_property_decorate = False
			layout.use_property_split = True
			layout.label(text="Interpolation")
			layout.row().prop(props, 'interpolation_color_mode')

			match props.interpolation_color_mode:
				case 'RGB' | 'OKLAB':
					layout.row().prop(props, 'interpolation_type', text="Method")
				case 'HSV' | 'HSL':
					layout.row().prop(props, 'interpolation_hue_type', text="Method")

			layout.prop(props, 'clip_colors')
		
	
