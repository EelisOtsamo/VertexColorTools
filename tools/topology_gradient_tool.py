# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
import bpy.types
from bpy.types import Context, WorkSpaceTool, UILayout

from ..operators.paint_topology_gradient import VCOLTOOLS_OT_PaintGradientTopology


class TopologyGradientTool(WorkSpaceTool):
	bl_idname = 'vertex_color_edit_tools.gradient_topology_tool'
	bl_space_type = 'VIEW_3D'
	bl_context_mode = 'EDIT_MESH'
	bl_label = 'Vertex Color Topology Gradient'
	bl_icon = (Path(__file__).parent.parent / "ui" / 'icons' / "vertex_color_edit_tools.paint_gradient_topology").as_posix()
	bl_keymap = (
			(
				VCOLTOOLS_OT_PaintGradientTopology.bl_idname, 
				{"type": 'RIGHTMOUSE', "value": 'PRESS'},
				{"properties": []},
			),
	)


	def draw_settings(context: Context, layout: UILayout, tool: WorkSpaceTool, extra = False): # pyright: ignore[reportSelfClsParameterName, reportGeneralTypeIssues]
		props = tool.operator_properties(VCOLTOOLS_OT_PaintGradientTopology.bl_idname)

		region_is_header = bpy.context.region.type == 'TOOL_HEADER'

		if not region_is_header:
			VCOLTOOLS_OT_PaintGradientTopology.static_draw(props, layout)
			return

		if not extra:
			layout.prop(props, 'blend_mode')

			row = layout.row(align=True, heading="Color Begin")
			row.prop(props, "color_begin", icon_only=True)
			row.prop(props, "factor_begin", text="")

			row = layout.row(align=True, heading="Color End")
			row.prop(props, "color_end", icon_only=True)
			row.prop(props, "factor_end", text="")

			layout.prop(props, 'mirror')
			layout.prop(props, 'extent_clamp_mode')

			layout.popover("TOPBAR_PT_tool_settings_extra", text="...")

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

			layout.prop(props, "clip_colors")
