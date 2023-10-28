# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bl_math
import bmesh
from bmesh.types import BMVert, BMEdge, BMFace, BMesh, BMLayerItem, BMLoop, BMVertSeq, BMElemSeq
from mathutils import Vector, Color
import queue

from .types import ContextException

from . import color_utils as ColorUtils

from enum import Enum

class FilterType(Enum):
	ALL = 0
	SELECTED = 1
	ACTIVE_VERTEX = 2,
	ACTIVE = 3

def merge_color_attribute(mesh: bpy.types.Mesh,
						base_attr_name: str,
						other_attr_name: str,
						blend_func: callable,
						factor: float = 1,
						clip_colors: bool = True):
	
	base_attr: bpy.types.Attribute = mesh.color_attributes.get(base_attr_name)
	other_attr: bpy.types.Attribute = mesh.color_attributes.get(other_attr_name)

	if not base_attr:
		raise ContextException(f"Color attribute \"{base_attr_name}\" not found")

	if not other_attr:
		raise ContextException(f"Color attribute \"{other_attr_name}\" not found")

	bm = bmesh.from_edit_mesh(mesh)

	base_layer, is_corner_attribute, _ = _parse_color_attribute(bm, base_attr)
	other_layer, is_corner_attribute, _ = _parse_color_attribute(bm, other_attr)
	
	if is_corner_attribute:
		elems = _get_face_loops(bm)
	else:
		elems = _get_vertices(bm)

	for elem in elems:
		_modify_color_attribute(elem, other_layer, blend_func, clip_colors, factor, elem[base_layer])

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)



def bright_contrast_color_attribute(mesh: bpy.types.Mesh,
						brightness: float,
						contrast: float,
						selected_only: bool = False,
						clip_colors: bool = True):
	"""
	The algorithm is by Werner D. Streidt
	(http://visca.com/ffactory/archives/5-99/msg00021.html)
	Extracted from blender/source/blender/compositor/realtime_compositor/shaders/library/gpu_shader_compositor_bright_contrast.glsl
	"""
	bm = bmesh.from_edit_mesh(mesh)

	active_layer, is_corner_attribute, _ = _parse_color_attribute(bm, mesh.color_attributes.active_color)
	
	filter_type = FilterType.SELECTED if selected_only else FilterType.ALL

	if is_corner_attribute:
		elems = _get_face_loops(bm, filter_type)
	else:
		elems = _get_vertices(bm, filter_type)

	brightness /= 100.0
	delta = contrast / 200.0

	if contrast > 0:
		multiplier = 1.0 - delta * 2
		multiplier = 1 / max(multiplier, 1.192092896e-07)
		offset = multiplier * (brightness - delta)
	else:
		delta *= -1.0
		multiplier = max(1.0 - delta * 2.0, 0.0)
		offset = multiplier * brightness + delta
	

	for elem in elems:
		out_rgb = Vector((c * multiplier + offset for c in elem[active_layer][:3]))
		
		if clip_colors:
			out_rgb = [bl_math.clamp(x, 0.0, 1.0) for x in out_rgb]

		elem[active_layer][:3] = out_rgb[:3]

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
	

def clip_color_attribute(mesh: bpy.types.Mesh):
	bm = bmesh.from_edit_mesh(mesh)

	active_layer, is_corner_attribute, _ = _parse_color_attribute(bm, mesh.color_attributes.active_color)
	
	if is_corner_attribute:
		elems = _get_face_loops(bm)
	else:
		elems = _get_vertices(bm)

	for elem in elems:
		elem[active_layer][:] = [bl_math.clamp(x, 0.0, 1.0) for x in elem[active_layer]][:]

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)


def select_linked(mesh: bpy.types.Mesh,
				check_corners: bool,
				threshold: float = 0.0,
				ignore_alpha: bool = True,
				deselect: bool = False):
	bm = bmesh.from_edit_mesh(mesh)

	active_layer, is_corner_attribute, _ = _parse_color_attribute(bm, mesh.color_attributes.active_color)

	if is_corner_attribute:
		active_face = _get_active_face(bm)
		if not active_face:
			raise ContextException("No active face")
		_flood_fill_select_face(active_face, active_layer, threshold, ignore_alpha, not deselect, check_corners)
	else:
		active = _get_active_vertex(bm)
		if not active:
			raise ContextException("No active vertex")
			
		_flood_fill_select_vertex(active, active_layer, threshold, ignore_alpha, not deselect)

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)


def _flood_fill_select_vertex(vert: BMVert, active_layer: BMLayerItem, threshold: float, ignore_alpha: bool, select: bool):
	color: Vector = vert[active_layer]
	
	if ignore_alpha:
		color = color.to_3d()

	vert_q: queue.Queue[BMVert]= queue.Queue()
	vert_q.put(vert)
	while vert_q.qsize() != 0:
		vert = vert_q.get()
		for edge in vert.link_edges:
			other_vert = edge.other_vert(vert)
			if other_vert.select == select:
				# Skip if already done
				continue
			other_color = other_vert[active_layer]
			if ignore_alpha:
				other_color = other_color.to_3d()
			if (other_color - color).length <= threshold:
				other_vert.select = select
				vert_q.put(other_vert)


def _flood_fill_select_face(face: BMFace, active_layer: BMLayerItem, threshold: float, ignore_alpha: bool, select: bool, check_corners: bool):
	color = _get_average_color(face.loops, active_layer)

	if ignore_alpha:
		color = color.to_3d()

	face_q: queue.Queue[BMFace] = queue.Queue()
	face_q.put(face)
	while face_q.qsize() != 0:
		face = face_q.get()
		if check_corners:
			other_faces = [f for v in face.verts for f in v.link_faces]
		else:
			other_faces = [loop.link_loop_radial_next.face for loop in face.loops if loop.link_loop_radial_next != loop]
		
		for other_face in other_faces:
			if other_face.select == select:
				continue
			other_color = _get_average_color(other_face.loops, active_layer)
			if ignore_alpha:
				other_color = other_color.to_3d()
			if (other_color - color).length <= threshold:
				other_face.select = select
				face_q.put(other_face)



def select_similar_color(mesh: bpy.types.Mesh,
						threshold: float = 0.0,
						ignore_alpha: bool = True):
	
	bm = bmesh.from_edit_mesh(mesh)

	active_layer, is_corner_attribute, _ = _parse_color_attribute(bm, mesh.color_attributes.active_color)

	selection_colors, selection_type = _get_selection_colors(mesh, ignore_alpha)

	if selection_type == BMVert: # One vertex
		# Find vertices with linked loops with the same color
		for vert in bm.verts:
			if len(vert.link_loops) != len(selection_colors):
				continue

			if ignore_alpha:
				colors = [loop[active_layer].to_3d() for loop in vert.link_loops]
			else:
				colors = [loop[active_layer] for loop in vert.link_loops]

			cumulative_distance = 0
			for i, s_color in enumerate(selection_colors):
				distances: list[float] = [(color - s_color).length * 0.5 for color in colors]
				min_distance = min(distances)
				min_idx = distances.index(min_distance)
				del colors[min_idx]
				cumulative_distance += min_distance

			average_distance = cumulative_distance / len(selection_colors)
			if average_distance > threshold:
				continue
			vert.select = True

	elif selection_type == BMEdge:  # One edge
		# Find edges with linked loops with the same color
		for edge in bm.edges:
			if len(edge.link_loops) * 2 != len(selection_colors):
				continue
			edge_loops = edge.link_loops[:] + [loop.link_loop_radial_next for loop in edge.link_loops]

			if ignore_alpha:
				colors = [loop[active_layer].to_3d() for loop in edge_loops]
			else:
				colors = [loop[active_layer] for loop in edge_loops]

			cumulative_distance = 0
			for i, s_color in enumerate(selection_colors):
				distances: list[float] = [(color - s_color).length * 0.5 for color in colors]
				min_distance = min(distances)
				min_idx = distances.index(min_distance)
				del colors[min_idx]
				cumulative_distance += min_distance

			average_distance = cumulative_distance / len(selection_colors)
			if average_distance > threshold:
				continue
			edge.select = True
	else:
		selection_color = selection_colors
		for elem in (bm.faces if is_corner_attribute else _get_vertices(bm)):
			if is_corner_attribute:
				color = _get_average_color(elem.loops, active_layer)
			else: 
				color = elem[active_layer]
			if ignore_alpha:
				selection_color = selection_color.to_3d()
				color = color.to_3d()

			distance = (color - selection_color).length * 0.5
			if distance > threshold:
				continue
			elem.select = True

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)


def _get_selection_colors(mesh: bpy.types.Mesh, ignore_alpha = False) -> tuple[Vector, None] | tuple[list[Vector], type[BMVert] | type[BMEdge]]:
	bm = bmesh.from_edit_mesh(mesh)
	active_layer, is_corner_attribute, _ = _parse_color_attribute(bm, mesh.color_attributes.active_color)

	if is_corner_attribute:
		if mesh.total_vert_sel == 1:
			# One vertex
			selected_vert: BMVert = [vert for vert in bm.verts if vert.select][0]
			if ignore_alpha:
				selection_colors = [loop[active_layer].to_3d() for loop in selected_vert.link_loops]
			else:
				selection_colors = [loop[active_layer].copy() for loop in selected_vert.link_loops]

			return (selection_colors, BMVert)

		elif mesh.total_vert_sel == 2 and mesh.total_edge_sel == 1:
			# One edge
			selected_edge: BMEdge = [edge for edge in bm.edges if edge.select][0]
			edge_loops = selected_edge.link_loops[:] + [loop.link_loop_radial_next for loop in selected_edge.link_loops]
			
			if ignore_alpha:
				selection_colors = [loop[active_layer].to_3d() for loop in edge_loops]
			else:
				selection_colors = [loop[active_layer].copy() for loop in edge_loops]

			return (selection_colors, BMEdge)
		elif mesh.total_face_sel > 0:
			# Faces
			selected = _get_face_loops(bm, FilterType.SELECTED)
			color = _get_average_color(selected, active_layer)
			if ignore_alpha:
				color = color.to_3d()

			return (color, None)
		else:
			# Verts
			loops = [loop for vert in bm.verts if vert.select for loop in vert.link_loops]
			color = _get_average_color(loops, active_layer)
			if ignore_alpha:
				color = color.to_3d()

			return (color, None)
	else:	
		selected = _get_vertices(bm, FilterType.SELECTED)
		color = _get_average_color(selected, active_layer)
		if ignore_alpha:
			color = color.to_3d()

		return (color, None)

		

def copy_active_color_to_selected(mesh: bpy.types.Mesh):
	bm = bmesh.from_edit_mesh(mesh)
	
	active_layer, is_corner_attribute, _ = _parse_color_attribute(bm, mesh.color_attributes.active_color)
	
	if is_corner_attribute:
		selected_elems = _get_face_loops(bm, FilterType.SELECTED)
		active_elems = _get_face_loops(bm, FilterType.ACTIVE)
	else:
		selected_elems = _get_vertices(bm, FilterType.SELECTED)
		active_elems = _get_vertices(bm, FilterType.ACTIVE)

	if len(active_elems) == 0:
		if is_corner_attribute:
			raise ContextException("Active element has to be a face when color attribute domain is 'Face Corner'")
		raise ContextException("No active element found")
	
	active_color = _get_average_color(active_elems, active_layer)

	for elem in selected_elems:
		elem[active_layer] = active_color

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)


def save_active_color(mesh: bpy.types.Mesh) -> list[Vector]:
	bm = bmesh.from_edit_mesh(mesh)

	active_layer, is_corner_attribute, is_byte_color = _parse_color_attribute(bm, mesh.color_attributes.active_color)
	
	if is_corner_attribute:
		elems = _get_face_loops(bm)		   
	else:
		elems = _get_vertices(bm)

	arr = [elem[active_layer].copy() for elem in elems]

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
	return arr


def load_active_color(mesh: bpy.types.Mesh, saved: list[Vector]):
	bm = bmesh.from_edit_mesh(mesh)
	
	active_layer, is_corner_attribute, is_byte_color = _parse_color_attribute(bm, mesh.color_attributes.active_color)

	if is_corner_attribute:
		elems = _get_face_loops(bm)
	else:
		elems = _get_vertices(bm)

	for i, elem in enumerate(elems):
		elem[active_layer] = saved[i]

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)



def _get_active_vertex(bm: BMesh):
	if bm.select_history:
		elem = bm.select_history[-1]
		if isinstance(elem, BMVert):
			return elem
	return None

def _get_active_face(bm: BMesh):
	if bm.select_history:
		elem = bm.select_history[-1]
		if isinstance(elem, BMFace):
			return elem
	return None


def _get_face_loops(bm: BMesh, types: FilterType = FilterType.ALL) -> list[BMLoop]:
	match types:
		case FilterType.ACTIVE:
			active = _get_active_face(bm)
			if not active:
				return []
			return [loop for face in bm.faces if face == active for loop in face.loops]
		case FilterType.ACTIVE_VERTEX:
			active = _get_active_vertex(bm)
			if not active:
				return []
			return [loop for face in bm.faces if face.select for loop in face.loops if loop.vert == active]
		case FilterType.SELECTED:
			return [loop for face in bm.faces if face.select for loop in face.loops]
		case FilterType.ALL:
			return [loop for face in bm.faces for loop in face.loops]
	return []


def _get_vertices(bm: BMesh,
				types: FilterType = FilterType.ALL) -> list[BMVert] | BMVertSeq:
	match types:
		case FilterType.ACTIVE_VERTEX | FilterType.ACTIVE:
			active = _get_active_vertex(bm)
			if not active:
				return []
			return [active]
		case FilterType.SELECTED:
			return [vert for vert in bm.verts if vert.select]
		case FilterType.ALL:
			return bm.verts
	return []


def _parse_color_attribute(bm: BMesh,
						color_attribute: bpy.types.Attribute
						) -> tuple[BMLayerItem, bool, bool]:
	'''
	Returns a tuple of:
		- The active color layer
		- Whether the attribute is a corner attribute instead of a vertex attribute
		- Whether the attribute is a byte color attribute instead of float color attribute
	'''
	is_byte_color: bool = color_attribute.data_type == 'BYTE_COLOR'
	is_corner_attribute = color_attribute.domain == 'CORNER'

	layers = bm.loops.layers if is_corner_attribute else bm.verts.layers
	col_layers = layers.color if is_byte_color else layers.float_color
	return (col_layers.active, is_corner_attribute, is_byte_color)


def _get_average_color(elems: list[BMVert] | list[BMLoop] | BMVertSeq | BMElemSeq, active_layer: BMLayerItem) -> Vector:
	average_color = Vector((0,0,0,0))
	if not elems:
		return average_color
	for elem in elems:
		average_color += elem[active_layer]
	return average_color / len(elems)


def _modify_color_attribute(elem: BMVert | BMLoop,
						color_layer: BMLayerItem,
						func: callable,
						clip_colors: bool,
						factor: float,
						color: Vector):
	out_col = func(factor, elem[color_layer], color)

	if clip_colors:
		out_col = [bl_math.clamp(x, 0.0, 1.0) for x in out_col]

	elem[color_layer] = out_col




def set_selection_color(mesh: bpy.types.Mesh,
						active_corner_only: bool,
						blend_func: callable,
						factor: float,
						color: Color,
						clip_colors: bool) -> None:
	
	bm = bmesh.from_edit_mesh(mesh)
	active_layer, is_corner_attribute, is_byte_color = _parse_color_attribute(bm, mesh.color_attributes.active_color)

	vec_col = Vector(color)

	if is_byte_color:
		vec_col[:3] = [ColorUtils.linear_to_srgb(x) for x in color[:3]]

	if is_corner_attribute:
		if active_corner_only:
			active = _get_active_vertex(bm)
			if not active:
				raise ContextException("No active vertex found")
			elems = [loop for face in bm.faces if face.select for loop in face.loops if loop.vert == active]
		else:
			elems = []

			face_verts = []
			for face in bm.faces:
				if face.select:
					elems += face.loops
					face_verts += face.verts

			elems += [loop for vert in bm.verts if vert.select and vert not in face_verts for loop in vert.link_loops]
	else:
		if active_corner_only:
			active = _get_active_vertex(bm)
			if not active:
				raise ContextException("No active vertex found")
			elems = [active]
		else:
			elems = [vert for vert in bm.verts if vert.select]

	for elem in elems:
		_modify_color_attribute(
			elem, active_layer, blend_func, clip_colors, factor, vec_col)

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)


def get_selection_color(mesh: bpy.types.Mesh) -> Vector:
	selection_colors, selection_type = _get_selection_colors(mesh, False)
	if selection_type is None:
		return selection_colors
	
	average_color = Vector((0,0,0,0))
	for col in selection_colors:
		average_color += col
	return average_color / len(selection_colors)


def get_active_corner_color(mesh: bpy.types.Mesh):
	bm = bmesh.from_edit_mesh(mesh)
	active_layer, _, _ = _parse_color_attribute(bm, mesh.color_attributes.active_color)

	active = _get_active_vertex(bm)
	if not active:
		raise ContextException("No active vertex found")
	
	selected_faces = [face for face in bm.faces if face.select]
	if not selected_faces:
		raise ContextException("No faces selected")
	
	selected_face: BMFace = selected_faces[0]
	if mesh.total_vert_sel > len(selected_face.verts):
		raise ContextException("All selected vertices must belong to the selected face")

	active_loop = [loop for loop in selected_face.loops if loop.vert == active][0]

	average_color = active_loop[active_layer].copy()

	return average_color