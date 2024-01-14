# SPDX-License-Identifier: GPL-2.0-or-later

from bpy.types import (
	Panel,
	UILayout,
	Context,
	Attribute,)

from bpy.utils import unregister_class, register_class

from ..preferences import EDITVERTCOL_PropertyGroup

from ..operators.edit import (
	EDITVERTCOL_OT_Preview,
	EDITVERTCOL_OT_Clip,
	EDITVERTCOL_OT_SelectSimilarVertexColor,
	EDITVERTCOL_OT_CopyColorToSelected,
	EDITVERTCOL_OT_SelectLinkedVertexColor
)

from ..operators.sidepanel import (
	EDITVERTCOL_OT_Apply,
	EDITVERTCOL_OT_CopySelected,
	EDITVERTCOL_OT_CopyActiveCorner,
	EDITVERTCOL_OT_PaletteColorAdd,
	EDITVERTCOL_OT_PaletteColorRemove,
	EDITVERTCOL_OT_PaletteColorReset
)

from ..operators.paint_gradient import (
	EDITVERTCOL_OT_PaintGradient
)

from ..operators.paint_topology_gradient import (
	EDITVERTCOL_OT_PaintGradientTopology
)

from ..operators.color_attribute import (
	EDITVERTCOL_OT_Convert,
	EDITVERTCOL_OT_Duplicate
)


class EDITVERTCOL_PT_Panel(Panel):
	bl_idname = "EDITVERTCOL_PT_side_panel"
	bl_label = "Vertex Colors"
	bl_icon = 'GROUP_VCOL'
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Edit"
	bl_options = {'DEFAULT_CLOSED'}

	def draw_header(self, _):
		layout = self.layout
		layout.label(text="", icon='GROUP_VCOL')


	@classmethod
	def poll(cls, context: Context):
		return context.mode == 'EDIT_MESH' and context.edit_object

	def draw(self, context: Context):
		props: EDITVERTCOL_PropertyGroup = context.scene.EditVertexColorsProperties

		can_active = False
		try:
			color_attribute: Attribute = context.edit_object.data.color_attributes.active_color
			current_domain = color_attribute.domain
			if current_domain == 'CORNER':
				can_active = True
		except AttributeError as e:
			pass

		col = self.layout.column(align=False)

		preset_col = col.column(align=True)
		preset_col.prop_enum(props, 'blend_mode', value='MIX')
		preset_grid = preset_col.grid_flow(columns=2, align=True)
		preset_grid.prop_enum(props, 'blend_mode', value='ADD')
		preset_grid.prop_enum(props, 'blend_mode', value='SUBTRACT')
		preset_grid.prop_enum(props, 'blend_mode', value='MULTIPLY')
		preset_grid.prop_enum(props, 'blend_mode', value='OVERLAY')
		col.separator()

		col.prop(props, 'blend_mode')
		col.separator()


		row = col.row(align=True)

		row.operator(EDITVERTCOL_OT_CopySelected.bl_idname, text="", icon='COPYDOWN')
		row.operator(EDITVERTCOL_OT_CopyActiveCorner.bl_idname, text="", icon='VERTEXSEL')
		row.prop(props, 'brush_color', icon_only=True)
		row.prop(props, 'factor')
		col.separator()
		col.operator(EDITVERTCOL_OT_Apply.bl_idname, text="Apply", icon='BRUSH_DATA')
		
		col.separator()

		grid = col.grid_flow()

		active_only_col = grid.column()
		active_only_col.enabled = can_active
		active_only_col.prop(props, 'active_only')

		grid.prop(props, 'clip_colors')

		row = col.row(align=True)
		row.operator(EDITVERTCOL_OT_PaletteColorAdd.bl_idname, icon='ADD', text="")
		row.operator(EDITVERTCOL_OT_PaletteColorRemove.bl_idname, icon='REMOVE', text="")
		row.operator(EDITVERTCOL_OT_PaletteColorReset.bl_idname, icon='LOOP_BACK', text="")

		grid = col.grid_flow(align=True, columns=-5, row_major=True)
		grid.use_property_decorate = False
		grid.use_property_split = False
		palette = context.scene.EditVertexColorsPalette
		for prop in palette:
			grid.prop(prop, "color", icon_only=True, icon='BRUSH_DATA')


class EDITVERTCOL_PT_UtilityPanel(Panel):
	bl_idname = "EDITVERTCOL_PT_utility_panel"
	bl_label = "Utilities"
	bl_parent_id = EDITVERTCOL_PT_Panel.bl_idname
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Edit"

	@classmethod
	def poll(cls, context: Context):
		return context.mode == 'EDIT_MESH' and context.edit_object and context.edit_object
	
	def draw(self, context: Context) -> None:
		layout = self.layout
		layout.label(text="Gradient")
		row = layout.row()
		row.operator(EDITVERTCOL_OT_PaintGradient.bl_idname, text="Gradient", icon='IPO_LINEAR')
		row.operator(EDITVERTCOL_OT_PaintGradientTopology.bl_idname, text="Topology Gradient", icon='EDGESEL')
		layout.label(text="Misc")
		layout.operator(EDITVERTCOL_OT_CopyColorToSelected.bl_idname, text="Copy to Selected from Active", icon='UV_SYNC_SELECT')
		row = layout.row()
		row.operator(EDITVERTCOL_OT_SelectSimilarVertexColor.bl_idname, text="Select Similar")
		row.operator(EDITVERTCOL_OT_SelectLinkedVertexColor.bl_idname, text="Select Linked")
		layout.separator()
		layout.operator(EDITVERTCOL_OT_Preview.bl_idname, icon='SHADING_SOLID')


class EDITVERTCOL_PT_ConvertPanel(Panel):
	bl_idname = "EDITVERTCOL_PT_convert_panel"
	bl_label = "Color Attribute"
	bl_parent_id = EDITVERTCOL_PT_Panel.bl_idname
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Edit"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context: Context):
		return context.mode == 'EDIT_MESH' and context.edit_object and context.edit_object

	def draw(self, context: Context):
		mesh = context.edit_object.data
		layout = self.layout
		col = layout.column()
		self.draw_shortcuts(context, col)
		# Color attribute list similar to the one in the mesh property panel
		row = col.row()
		col = row.column()
		col.template_list(
			listtype_name="MESH_UL_color_attributes",
			list_id="EDITVERTCOL_PT_convert_panel_color_attributes",
			dataptr=mesh,
			propname='color_attributes',
			active_dataptr=mesh.color_attributes,
			active_propname='active_color_index',
			rows=4,
		)
		col = row.column(align=True)
		col.operator('geometry.color_attribute_add', icon='ADD', text="")
		col.operator('geometry.color_attribute_remove', icon='REMOVE', text="")
		col.separator()
		col.operator(EDITVERTCOL_OT_Duplicate.bl_idname,
					 icon='DUPLICATE', text="")

	def draw_shortcuts(self, context: Context, col: UILayout):
		try:
			color_attribute: Attribute = context.edit_object.data.color_attributes.active_color
			current_domain = color_attribute.domain
			current_data_type = color_attribute.data_type
		except AttributeError as e:
			return

		# Split Colors
		grid1 = col.grid_flow(even_columns=True)
		conv_button1 = grid1.column()
		conv_button1.enabled = current_domain != 'CORNER'
		op1 = conv_button1.operator(EDITVERTCOL_OT_Convert.bl_idname,
									icon='MOD_EDGESPLIT', text="Split Colors")
		op1.domain = 'CORNER'
		op1.data_type = current_data_type

		# Merge Colors
		conv_button2 = grid1.column()
		conv_button2.enabled = current_domain != 'POINT'
		op2 = conv_button2.operator(EDITVERTCOL_OT_Convert.bl_idname,
									icon='VERTEXSEL', text="Merge Colors")
		op2.domain = 'POINT'
		op2.data_type = current_data_type
		col.separator()

		# To Float Color
		grid2 = col.grid_flow(even_columns=True)
		conv_button3 = grid2.column()
		conv_button3.enabled = current_data_type != 'FLOAT_COLOR'
		op3 = conv_button3.operator(EDITVERTCOL_OT_Convert.bl_idname,
									icon='GROUP_VCOL', text="To Float Color")
		op3.domain = current_domain
		op3.data_type = 'FLOAT_COLOR'

		# To Byte Color
		conv_button4 = grid2.column()
		conv_button4.enabled = current_data_type != 'BYTE_COLOR'
		op4 = conv_button4.operator(EDITVERTCOL_OT_Convert.bl_idname,
									icon='GROUP_VCOL', text="To Byte Color")
		op4.domain = current_domain
		op4.data_type = 'BYTE_COLOR'
		col.separator()

		# Clip
		col.operator(EDITVERTCOL_OT_Clip.bl_idname, text="Clip All Colors", icon='SEQ_HISTOGRAM')

	
panels = (
	EDITVERTCOL_PT_Panel,
	EDITVERTCOL_PT_UtilityPanel,
	EDITVERTCOL_PT_ConvertPanel,
)


def register():
	for cls in panels:
		register_class(cls)

def unregister():

	for cls in reversed(panels):
		unregister_class(cls)
