# SPDX-License-Identifier: GPL-3.0-or-later


from bpy.types import (
	Mesh,
	Panel,
	UILayout,
	Context,
	Attribute,)

from bpy.utils import unregister_class, register_class

from ..preferences import (
	VCOLTOOLS_PropertyGroup,
	addon_preferences,
)

from ..paint_palette_compat import get_paint_palettes_module

from ..operators.edit import (
	VCOLTOOLS_OT_Preview,
	VCOLTOOLS_OT_Clip,
	VCOLTOOLS_OT_SelectSimilarVertexColor,
	VCOLTOOLS_OT_CopyColorToSelected,
	VCOLTOOLS_OT_SelectLinkedVertexColor
)

from ..operators.sidepanel import (
	VCOLTOOLS_OT_Apply,
	VCOLTOOLS_OT_CopySelected,
	VCOLTOOLS_OT_CopyActiveCorner,
	VCOLTOOLS_OT_PaletteColorAdd,
	VCOLTOOLS_OT_PaletteColorRemove,
	VCOLTOOLS_OT_PaletteColorReset,
	VCOLTOOLS_OT_PaletteColorSelect
)

from ..operators.paint_gradient import (
	VCOLTOOLS_OT_PaintGradient
)

from ..operators.paint_topology_gradient import (
	VCOLTOOLS_OT_PaintGradientTopology
)

from ..operators.color_attribute import (
	VCOLTOOLS_OT_Convert,
	VCOLTOOLS_OT_Duplicate
)


class VCOLTOOLS_PT_Panel(Panel):
	bl_idname = "VCOLTOOLS_PT_side_panel"
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
		props: VCOLTOOLS_PropertyGroup = context.scene.EditVertexColorsProperties

		can_active = False
		try:
			color_attribute: Attribute = context.edit_object.data.color_attributes.active_color # type: ignore
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

		row.operator(VCOLTOOLS_OT_CopySelected.bl_idname, text="", icon='COPYDOWN')
		row.operator(VCOLTOOLS_OT_CopyActiveCorner.bl_idname, text="", icon='VERTEXSEL')
		row.prop(props, 'brush_color', icon_only=True)
		row.prop(props, 'factor')
		col.separator()
		col.operator(VCOLTOOLS_OT_Apply.bl_idname, text="Apply", icon='BRUSH_DATA')
		
		col.separator()

		grid = col.grid_flow()

		active_only_col = grid.column()
		active_only_col.enabled = can_active
		active_only_col.prop(props, 'active_only')

		grid.prop(props, 'clip_colors')


class VCOLTOOLS_PT_UtilityPanel(Panel):
	bl_idname = "VCOLTOOLS_PT_utility_panel"
	bl_label = "Utilities"
	bl_parent_id = VCOLTOOLS_PT_Panel.bl_idname
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
		row.operator(VCOLTOOLS_OT_PaintGradient.bl_idname, text="Gradient", icon='IPO_LINEAR')
		row.operator(VCOLTOOLS_OT_PaintGradientTopology.bl_idname, text="Topology Gradient", icon='EDGESEL')
		layout.label(text="Misc")
		layout.operator(VCOLTOOLS_OT_CopyColorToSelected.bl_idname, text="Copy to Selected from Active", icon='UV_SYNC_SELECT')
		row = layout.row()
		row.operator(VCOLTOOLS_OT_SelectSimilarVertexColor.bl_idname, text="Select Similar")
		row.operator(VCOLTOOLS_OT_SelectLinkedVertexColor.bl_idname, text="Select Linked")
		layout.separator()
		layout.operator(VCOLTOOLS_OT_Preview.bl_idname, icon='SHADING_SOLID')


class VCOLTOOLS_PT_ConvertPanel(Panel):
	bl_idname = "VCOLTOOLS_PT_convert_panel"
	bl_label = "Color Attribute"
	bl_parent_id = VCOLTOOLS_PT_Panel.bl_idname
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Edit"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context: Context):
		return context.mode == 'EDIT_MESH' and context.edit_object and context.edit_object

	def draw(self, context: Context):
		mesh: Mesh = context.edit_object.data # type: ignore
		layout = self.layout
		col = layout.column()
		self.draw_shortcuts(context, col)
		# Color attribute list similar to the one in the mesh property panel
		row = col.row()
		col = row.column()
		col.template_list(
			listtype_name="MESH_UL_color_attributes",
			list_id="VCOLTOOLS_PT_convert_panel_color_attributes",
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
		col.operator(VCOLTOOLS_OT_Duplicate.bl_idname,
					 icon='DUPLICATE', text="")

	def draw_shortcuts(self, context: Context, col: UILayout):
		try:
			color_attribute: Attribute = context.edit_object.data.color_attributes.active_color # pyright: ignore
			current_domain = color_attribute.domain
			current_data_type = color_attribute.data_type
		except AttributeError as e:
			return

		# Split Colors
		grid1 = col.grid_flow(even_columns=True)
		conv_button1 = grid1.column()
		conv_button1.enabled = current_domain != 'CORNER'
		op1 = conv_button1.operator(VCOLTOOLS_OT_Convert.bl_idname,
									icon='MOD_EDGESPLIT', text="Split Colors")
		op1.domain = 'CORNER'
		op1.data_type = current_data_type

		# Merge Colors
		conv_button2 = grid1.column()
		conv_button2.enabled = current_domain != 'POINT'
		op2 = conv_button2.operator(VCOLTOOLS_OT_Convert.bl_idname,
									icon='VERTEXSEL', text="Merge Colors")
		op2.domain = 'POINT'
		op2.data_type = current_data_type
		col.separator()

		# To Float Color
		grid2 = col.grid_flow(even_columns=True)
		conv_button3 = grid2.column()
		conv_button3.enabled = current_data_type != 'FLOAT_COLOR'
		op3 = conv_button3.operator(VCOLTOOLS_OT_Convert.bl_idname,
									icon='GROUP_VCOL', text="To Float Color")
		op3.domain = current_domain
		op3.data_type = 'FLOAT_COLOR'

		# To Byte Color
		conv_button4 = grid2.column()
		conv_button4.enabled = current_data_type != 'BYTE_COLOR'
		op4 = conv_button4.operator(VCOLTOOLS_OT_Convert.bl_idname,
									icon='GROUP_VCOL', text="To Byte Color")
		op4.domain = current_domain
		op4.data_type = 'BYTE_COLOR'
		col.separator()

		# Clip
		col.operator(VCOLTOOLS_OT_Clip.bl_idname, text="Clip All Colors", icon='SEQ_HISTOGRAM')


class VCOLTOOLS_PT_PalettePanel(Panel):
	bl_idname = "VCOLTOOLS_PT_palette_panel"
	bl_label = "Color Palette"
	bl_parent_id = VCOLTOOLS_PT_Panel.bl_idname
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Edit"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def poll(cls, context: Context):
		return context.mode == 'EDIT_MESH' and context.edit_object

	def draw(self, context: Context):
		prefs = addon_preferences()

		if prefs.paint_palettes_enabled and get_paint_palettes_module():
			# Use the paint_palettes palette
			self.draw_paint_palettes(context)
		else:
			# Simple palette ui
			layout = self.layout
			col = layout.column()
			row = col.row(align=True)
			row.operator(VCOLTOOLS_OT_PaletteColorAdd.bl_idname, icon='ADD', text="")
			row.operator(VCOLTOOLS_OT_PaletteColorRemove.bl_idname, icon='REMOVE', text="")
			row.operator(VCOLTOOLS_OT_PaletteColorReset.bl_idname, icon='LOOP_BACK', text="")
			
			grid = col.grid_flow(align=True, columns=0, row_major=True, even_columns=True)
			grid.use_property_decorate = False
			grid.use_property_split = False
			palette = context.scene.EditVertexColorsPalette
			for i, prop in enumerate(palette):
				color_container = grid.column(align=True)
				color_container.ui_units_x = 2
				color_container.ui_units_y = 2
				color_container.prop(prop, "color", icon_only=True, icon='BRUSH_DATA')
				color_container.operator(VCOLTOOLS_OT_PaletteColorSelect.bl_idname, text="", icon='LAYER_ACTIVE').color_index = i


	def draw_paint_palettes(self, context: Context):
		"""
		Draws the Paint Palettes addon's palette UI.
		Modified from blender/4.0/scripts/addons/paint_palette.py
		SPDX-FileCopyrightText: 2011 Dany Lebel (Axon_D)
		SPDX-License-Identifier: GPL-2.0-or-later
		"""

		mod = get_paint_palettes_module()

		palette_props = context.scene.palette_props

		layout = self.layout

		row = layout.row(align=True)
		row.menu("PALETTE_MT_menu", text=mod.PALETTE_MT_menu.bl_label) # pyright: ignore
		row.operator("palette.preset_add", text="", icon='ADD').remove_active = False
		row.operator("palette.preset_add", text="", icon='REMOVE').remove_active = True

		col = layout.column(align=True)
		row = col.row(align=True)
		row.operator("palette_props.add_color", icon='ADD')
		row.prop(palette_props, "index")
		row.operator("palette_props.remove_color", icon="PANEL_CLOSE")

		row = col.row(align=True)
		row.prop(palette_props, "columns")
		if palette_props.colors.items():
			layout = col.box()
			row = layout.row(align=True)
			row.prop(palette_props, "color_name")
			row.operator("palette_props.sample_tool_color", icon="COLOR")

		laycol = layout.column(align=False)

		if palette_props.columns:
			columns = palette_props.columns
		else:
			columns = 16

		for i, color in enumerate(palette_props.colors):
			if i % columns == 0:
				row1 = laycol.row(align=True)
				row1.scale_y = 0.8
				row2 = laycol.row(align=True)
				row2.scale_y = 0.8

			active = i == palette_props.current_color_index
			icons = "LAYER_ACTIVE" if active else "LAYER_USED"
			row1.prop(palette_props.colors[i], "color", event=True, toggle=True) # pyright: ignore
			row2.operator(VCOLTOOLS_OT_PaletteColorSelect.bl_idname, text=" ", emboss=not active, icon=icons).color_index = i # pyright: ignore

		layout = self.layout
		row = layout.row()
		row.prop(palette_props, "presets_folder", text="")


panels = (
	VCOLTOOLS_PT_Panel,
	VCOLTOOLS_PT_PalettePanel,
	VCOLTOOLS_PT_UtilityPanel,
	VCOLTOOLS_PT_ConvertPanel,
)

def register():
	for cls in panels:
		register_class(cls)


def unregister():
	for cls in reversed(panels):
		unregister_class(cls)
