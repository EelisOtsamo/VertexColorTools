# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import bmesh
from bmesh.types import BMFace, BMLoop, BMFaceSeq
from mathutils import Vector, Color, geometry
from bl_math import clamp

from . import color_utils as ColorUtils
from .color_attribute import _parse_color_attribute

from enum import Enum

class GradientType(Enum):
	LINEAR = 'LINEAR'
	RADIAL = 'RADIAL'

class GradientSharpEdgeMode(Enum):
	OFF = 'OFF'
	VERTEX = 'VERTEX'
	FACE = 'FACE'

class GradientExtendMode(Enum):
	OFF = 'OFF'
	FORWARD = 'FORWARD'
	BACKWARD = 'BACKWARD'
	BOTH = 'BOTH'


def paint_gradient(mesh: bpy.types.Mesh,
				selected_only: bool,
				extend_mode: GradientExtendMode,
				boundary_sharp_mode: GradientSharpEdgeMode,
				gradient_type: GradientType,
				interp_func: callable,
				blend_func: callable,
				clip_colors: bool,
				factor: tuple[float,float],
				color: tuple[Color,Color],
				line: tuple[Vector,Vector]) -> None:
	
	bm = bmesh.from_edit_mesh(mesh)
	active_layer, is_corner_attribute, is_byte_color = _parse_color_attribute(bm, mesh.color_attributes.active_color)

	col0 = Vector(color[0])
	col1 = Vector(color[1])

	if is_byte_color:
		clip_colors = False
		col0[:3] = [ColorUtils.linear_to_srgb(x) for x in col0[:3]]
		col1[:3] = [ColorUtils.linear_to_srgb(x) for x in col1[:3]]

	l0, l1 = line
	line_dir = (l1 - l0)
	radius = line_dir.length
	if radius == 0:
		return
	
	line_dir /= radius
	
	radius_squared = radius * radius

	
	elems = []
	coords = []

	if is_corner_attribute:
		# Select filter
		if selected_only:
			faces = [face for face in bm.faces if face.select]
		else:
			faces = bm.faces
		# Extend filter
		if extend_mode == GradientExtendMode.BOTH:
			elems = [loop for face in faces for loop in face.loops]
			coords = [loop.vert.co for loop in elems]
		else:
			elems, coords = _filter_loops_from_faces(faces, boundary_sharp_mode, extend_mode, gradient_type, l0, l1)
	else:
		# Select filter
		verts = []
		if selected_only:
			verts = [vert for vert in bm.verts if vert.select]
		else:
			verts = bm.verts
		# Extend filter
		if extend_mode:
			elems = verts
			coords = [vert.co for vert in elems]
		else:
			for vert in verts:
				co_v = vert.co
				match gradient_type:
					case GradientType.LINEAR:
						_, dist0 = geometry.intersect_point_line(co_v, l0, l1)
						_, dist1 = geometry.intersect_point_line(co_v, l0, l1)
						if dist0 < 0 or dist1 > 1:
							continue
					case GradientType.RADIAL:
						if (l0 - co_v).length_squared > radius_squared:
							continue
				elems.append(vert)
				coords.append(vert.co)
	
	# Precompute these for interpolation
	factor_a = factor[0]
	factor_b = (factor[1] - factor[0])

	# Iterate over loops / verts
	for i, elem in enumerate(elems):
		co_v = coords[i]
		# Calculate gradient weight for this vertex
		weight = 0
		match gradient_type:
			case GradientType.LINEAR:
				_, weight = geometry.intersect_point_line(co_v, l0, l1)

			case GradientType.RADIAL:
				weight = (co_v - l0).length / radius

		weight = clamp(weight)

		# Get the color and factor from the blend function
		blend_fac = (factor_a + weight * factor_b)

		blend_col = interp_func(weight, col0, col1)
		out_col = blend_func(blend_fac, elem[active_layer], blend_col)

		if clip_colors:
			out_col[:] = [clamp(x, 0.0, 1.0) for x in out_col[:]]
			
		# Assign
		elem[active_layer] = out_col

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

	

def _filter_loops_from_faces(faces: list[BMFace] | BMFaceSeq,
				boundary_sharp_mode: GradientSharpEdgeMode,
				extend_mode: GradientExtendMode,
				gradient_type: GradientType,
				l0: Vector,
				l1: Vector) -> tuple[list[BMFace], list[Vector]]:
	
	elems: list[BMFace] = []
	coords: list[Vector] = []
	radius_squared = (l1 - l0).length_squared

	sharp_bounds = boundary_sharp_mode != GradientSharpEdgeMode.OFF
	
	check_forward = True
	check_backward = True
	match extend_mode:
		case GradientExtendMode.OFF:
			check_forward = False
			check_backward = False

		case GradientExtendMode.FORWARD:
			check_forward = False

		case GradientExtendMode.BACKWARD:
			check_backward = False

		case GradientExtendMode.BOTH:
			pass


	if boundary_sharp_mode == GradientSharpEdgeMode.FACE:
		# Discard faces not completely withing the bounds
		match gradient_type:
			case GradientType.LINEAR:
				faces = [face for face in faces if 
					(check_forward or _check_face_bounds_linear(face, l0, l1)) and
					(check_backward or _check_face_bounds_linear(face, l1, l0))]
				
			case GradientType.RADIAL:
				if check_forward:
					faces = [face for face in faces if _check_face_bounds_radial(face, l0, radius_squared)]

	match gradient_type:
		case GradientType.LINEAR:
			elems = [loop for face in faces for loop in face.loops if
				(check_forward or _check_face_loop_bounds_linear(loop, l0, l1, sharp_bounds)) and
				(check_backward or _check_face_loop_bounds_linear(loop, l1, l0, sharp_bounds))]
			
			coords = [loop.vert.co for loop in elems]

		case GradientType.RADIAL:
			if check_forward:
				elems = [loop for face in faces for loop in face.loops if _check_face_loop_bounds_radial(loop, l0, radius_squared, sharp_bounds)]
			else:
				elems = [loop for face in faces for loop in face.loops]
			coords = [loop.vert.co for loop in elems]

	return elems, coords




def _check_face_bounds_linear(face: BMFace, l0: Vector, l1: Vector):
	# Check all vertices in a face and skip if any vertex is outside the boundary
	for fl in face.loops:
		dist = _distance_to_line(fl.vert.co, l0, l1)
		if dist < 0:
			return False
	return True

def _check_face_bounds_radial(face: BMFace, l0: Vector, radius_squared: float):
	# Check all vertices in a face and skip if any vertex is outside the boundary
	for fl in face.loops:
		dist = _distance_to_radius(fl.vert.co, l0, radius_squared)
		if dist < 0:
			return False
	return True

def _check_face_loop_bounds_linear(loop: BMLoop, l0: Vector, l1: Vector, sharp_bounds: bool):
	dist = _distance_to_line(loop.vert.co, l0, l1)
	if dist < 0:
		return False
	
	if not sharp_bounds:
		return True

	# Check boundary overlap
	if dist == 0:
		dist = _distance_to_line(loop.link_loop_prev.vert.co, l0, l1)
		if dist == 0:
			dist = _distance_to_line(loop.link_loop_next.vert.co, l0, l1)
		if dist < 0:
			return False
		
	return True

def _check_face_loop_bounds_radial(loop: BMLoop, l0: Vector, radius_squared: float, sharp_bounds: bool):
	dist = _distance_to_radius(loop.vert.co, l0, radius_squared)
	if dist < 0:
		return False

	if not sharp_bounds:
		return True

	# Check boundary overlap
	if dist == 0 :
		has_out_of_range_connected_loop = False
		for l in [loop.link_loop_prev, loop.link_loop_next]:
			dist = _distance_to_radius(l.vert.co, l0, radius_squared)
			if dist > 0:
				has_out_of_range_connected_loop = True
				break
		if not has_out_of_range_connected_loop:
			return False
		
	return True



def _distance_to_line(co: Vector, l0: Vector, l1: Vector):
	_, d = geometry.intersect_point_line(co, l0, l1)
	return 0 if abs(d) < 0.0001 else d
							
def _distance_to_radius(co: Vector, center: Vector, radius_sqrt: float):
	dist = radius_sqrt - (center - co).length_squared
	return 0 if abs(dist) < 0.0001 else dist



