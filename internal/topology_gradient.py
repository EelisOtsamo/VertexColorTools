# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLayerItem, BMLoop
from mathutils import Vector, Color

from . import color_utils as ColorUtils
from .color_attribute import _parse_color_attribute, _modify_color_attribute
from .types import ContextException

from enum import Enum

# Maximum distance to check for face loop extent for each edge
MAX_EDGE_TOPOLOGY_EXTENT = 10000

class TopologyExtentClampMode(Enum):
	MINIMUM = 'MINIMUM'
	MAXIMUM = 'MAXIMUM'
	INDIVIDUAL = 'INDIVIDUAL'


def paint_topology_gradient(mesh: bpy.types.Mesh,
						mirror: bool,
						interp_func: callable,
						blend_func: callable,
						clip_colors: bool,
						factors: tuple[float,float],
						colors: tuple[Color,Color],
						distance: float,
						extent_clamp_mode: TopologyExtentClampMode,
						direction: Vector) -> None:
	
	bm = bmesh.from_edit_mesh(mesh)

	active_layer, is_corner_attribute, is_byte_color = _parse_color_attribute(bm, mesh.color_attributes.active_color)
	
	vec_colors = (Vector(colors[0]), Vector(colors[1]))
	direction = direction.copy()

	if is_byte_color:
		clip_colors = False
		vec_colors[0][:3] = [ColorUtils.linear_to_srgb(x) for x in vec_colors[0][:3]]
		vec_colors[1][:3] = [ColorUtils.linear_to_srgb(x) for x in vec_colors[1][:3]]

	edges : list[BMEdge] = [edge for edge in bm.edges if edge.select]

	if not edges:
		raise ContextException("No edges selected")

	if distance == 0:
		return
	if direction.length_squared == 0:
		return
	
	if distance < 0:
		direction *= -1
	
	distance = abs(distance)

	_paint_topology_gradient_for_edges(edges, is_corner_attribute, distance, factors, vec_colors, active_layer, interp_func, blend_func, clip_colors, extent_clamp_mode, direction)

	if mirror:
		_paint_topology_gradient_for_edges(edges, is_corner_attribute, distance, factors, vec_colors, active_layer, interp_func, blend_func, clip_colors, extent_clamp_mode, -direction)

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

def _find_edge_extent(edge: BMEdge, direction: Vector):
	loop_0: BMLoop = None
	first_face: BMFace = None
	for face_idx in range(1, MAX_EDGE_TOPOLOGY_EXTENT):
		if not loop_0:
			loop_0 = _find_first_loop(edge, direction)
			
			if not loop_0:
				# No next loop found in the direction
				return 0
			
			first_face = loop_0.face
		else:
			loop_0 = loop_0.link_loop_next.link_loop_next.link_loop_radial_next


		loop_1 = loop_0.link_loop_next
		loop_front_0 = loop_1.link_loop_next
		loop_front_1 = loop_0.link_loop_prev

		loop_back_0 = loop_0.link_loop_radial_next
		loop_back_1 = loop_back_0.link_loop_next

		cur_face = loop_0.face
		next_face = loop_front_0.link_loop_radial_next.face

		if next_face == cur_face:
			# Non manifold
			return face_idx
		
		if next_face == first_face:
			# Wrapped around
			return face_idx
		
		num_face_verts = len(cur_face.verts)
		if num_face_verts == 3:
			# Current face is a triangle
			return face_idx
		elif num_face_verts > 4:
			# Current face is an n-gon
			return face_idx - 1

	return 0


def _paint_topology_gradient_for_edges(
						edges: list[BMEdge],
						is_corner_attribute: bool,
						distance: float,
						factors: tuple[float,
						float],
						colors: tuple[Vector,Vector],
						color_layer: BMLayerItem,
						interp_func: callable,
						blend_func: callable,
						clip_colors: bool,
						extend_clamp_mode: TopologyExtentClampMode,
						direction: Vector):
	
	
	color_start, color_end = colors[:]
	factor_start, factor_end= factors[:]

	edge_extents = []
	for edge in edges:
		extent = _find_edge_extent(edge, direction)
		edge_extents.append(extent)
		
	minimum_extent = min(edge_extents)
	maximum_extent = max(edge_extents)
	
	for i in range(len(edges)):
		edge = edges[i]
		match extend_clamp_mode:
			case TopologyExtentClampMode.MAXIMUM:
				extent = min(distance, maximum_extent)
			case TopologyExtentClampMode.MINIMUM:
				extent = min(distance, minimum_extent)
			case TopologyExtentClampMode.INDIVIDUAL:
				extent = min(edge_extents[i], distance)
		
			
		last_face_idx = max(int(extent), 1)
		denom = max(extent, 1)

		integer_distance = (extent % 1) == 0
		is_partial_step = extent < 1

		loop_0: BMLoop = None
		first_face: BMFace = None
		prev_face: BMFace = None
		step_count = last_face_idx + (0 if is_partial_step else 1)
		for face_idx in range(step_count):
			if not loop_0:
				loop_0 = _find_first_loop(edge, direction)
				
				if not loop_0:
					# No next loop found in the direction
					return 0
				
				first_face = loop_0.face
			else:
				loop_0 = loop_0.link_loop_next.link_loop_next.link_loop_radial_next


			loop_1 = loop_0.link_loop_next

			loop_back_0 = loop_0.link_loop_radial_next
			loop_back_1 = loop_back_0.link_loop_next

			loop_front_0 = loop_1.link_loop_next
			loop_front_1 = loop_0.link_loop_prev

			cur_face = loop_0.face
			is_ngon = len(cur_face.verts) > 4

			#next_face = loop_front_0.link_loop_radial_next.face

			

			# Get the color and factor from the blend function
			weight = face_idx / denom
			blend_fac = factor_start + weight * (factor_end - factor_start)
			blend_col = interp_func(weight, color_start, color_end)

			if face_idx != last_face_idx and len(cur_face.verts) == 3 :
				# Handle edge case where the last face is a triangle
				if not is_corner_attribute:
					# Vertex attributes
					_modify_color_attribute(loop_0.vert, color_layer, blend_func, clip_colors, blend_fac, blend_col)
					_modify_color_attribute(loop_1.vert, color_layer, blend_func, clip_colors, blend_fac, blend_col)
				else:
					if face_idx != 0:
						_modify_color_attribute(loop_back_0, color_layer, blend_func, clip_colors, blend_fac, blend_col)
						_modify_color_attribute(loop_back_1, color_layer, blend_func, clip_colors, blend_fac, blend_col)
					
					_modify_color_attribute(loop_0, color_layer, blend_func, clip_colors, blend_fac, blend_col)
					_modify_color_attribute(loop_1, color_layer, blend_func, clip_colors, blend_fac, blend_col)
					
				# The third point of the triangle uses the weight for the next face.
				# Apply color here and break
				weight = (face_idx + 1) / denom
				blend_fac = factor_start + weight * (factor_end - factor_start)
				blend_col = interp_func(weight, color_start, color_end)
				if not is_corner_attribute:
					_modify_color_attribute(loop_front_0.vert, color_layer, blend_func, clip_colors, blend_fac, blend_col)
				else:
					_modify_color_attribute(loop_front_0, color_layer, blend_func, clip_colors, blend_fac, blend_col)
				break


			if not is_corner_attribute:
				# Vertex attributes
				_modify_color_attribute(loop_0.vert, color_layer, blend_func, clip_colors, blend_fac, blend_col)
				_modify_color_attribute(loop_1.vert, color_layer, blend_func, clip_colors, blend_fac, blend_col)
			else:
				# Corner attributes
				if integer_distance:
					# Snapped distance:
					if face_idx != 0:
						_modify_color_attribute(loop_back_0, color_layer, blend_func, clip_colors, blend_fac, blend_col)
						_modify_color_attribute(loop_back_1, color_layer, blend_func, clip_colors, blend_fac, blend_col)
					if face_idx != last_face_idx and not is_ngon:
						_modify_color_attribute(loop_0, color_layer, blend_func, clip_colors, blend_fac, blend_col)
						_modify_color_attribute(loop_1, color_layer, blend_func, clip_colors, blend_fac, blend_col)
				elif is_partial_step:
					# Only the first face is modified:
					# 	Only the front loops are colored
					#if edge_idx != last_edge_idx:
					_modify_color_attribute(loop_0, color_layer, blend_func, clip_colors, blend_fac, blend_col)
					_modify_color_attribute(loop_1, color_layer, blend_func, clip_colors, blend_fac, blend_col)
				else:
					# Decimal distance:
					#	Skip first back loops
					# 	Front loops of the last edge are colored as well 
					if face_idx != 0:
						_modify_color_attribute(loop_back_0, color_layer, blend_func, clip_colors, blend_fac, blend_col)
						_modify_color_attribute(loop_back_1, color_layer, blend_func, clip_colors, blend_fac, blend_col)
					_modify_color_attribute(loop_0, color_layer, blend_func, clip_colors, blend_fac, blend_col)
					_modify_color_attribute(loop_1, color_layer, blend_func, clip_colors, blend_fac, blend_col)
			
			if face_idx != 0 and cur_face == first_face:
				# Wrapped around
				break
			if prev_face == cur_face:
				# Non manifold
				break
			prev_face = cur_face


def _find_first_loop(edge: BMEdge, direction: Vector) -> BMLoop | None:
	a0 = edge.link_loops[0]
	a1 = edge.link_loops[0].link_loop_next.link_loop_next.link_loop_radial_next
	a_back = None
	b0 = None
	b1 = None
	b_back = None
	b_diff = 0
	if len(edge.link_loops) == 2:
		a_back = edge.link_loops[0].link_loop_radial_next.link_loop_next.link_loop_next

		b0 = edge.link_loops[1]
		b1 = edge.link_loops[1].link_loop_next.link_loop_next.link_loop_radial_next
		b_back = edge.link_loops[1].link_loop_radial_next.link_loop_next.link_loop_next
		b_diff = (b1.vert.co - b0.vert.co).normalized().dot(direction)
	a_diff = (a1.vert.co - a0.vert.co).normalized().dot(direction)
	if a_diff > b_diff:
		return a0
	elif a_diff < b_diff:
		return b0
	return
