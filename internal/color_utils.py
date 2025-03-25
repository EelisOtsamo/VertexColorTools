# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file contains Python ports of color blending and conversion functions sourced from Blender.
# Original code from:
# - blender/source/blender/gpu/shaders/common/gpu_shader_common_mix_rgb.glsl
#   - SPDX-FileCopyrightText: 2019-2022 Blender Authors
# - blender/source/blender/gpu/shaders/common/gpu_shader_common_color_utils.glsl
#   - SPDX-FileCopyrightText: 2019-2022 Blender Authors
# - blender/source/blender/blenlib/intern/math_color.cc
#   - SPDX-FileCopyrightText: 2001-2002 NaN Holding BV. All rights reserved.
# - blender/source/blender/blenkernel/intern/colorband.cc
#   - SPDX-FileCopyrightText: 2001-2002 NaN Holding BV. All rights reserved.
# 
# Oklab color space by Björn Ottosson:
# - https://bottosson.github.io/posts/oklab/
#

import typing
from bl_math import clamp
from functools import partial
from mathutils import Vector, Matrix


_HUE_INTP_NEAR = 0
_HUE_INTP_FAR = 1
_HUE_INTP_CW = 2
_HUE_INTP_CCW = 3


""" Blending functions """

def blend_mix(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.lerp(col2, fac)
	outcol.w = col1.w
	return outcol


def blend_add(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.lerp(col1 + col2, fac)
	outcol.w = col1.w
	return outcol


def blend_multiply(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.lerp(col1 * col2, fac)
	outcol.w = col1.w
	return outcol

def blend_screen(fac: float, col1: Vector, col2: Vector) -> Vector:
	facm = 1.0 - fac
	outcol = Vector((1, 1, 1, 1)) - ((Vector((facm, facm, facm, facm)) + fac * (Vector((1, 1, 1, 1)) - col2)) * (Vector((1, 1, 1, 1)) - col1))
	outcol.w = col1.w
	return outcol

def blend_overlay(fac: float, col1: Vector, col2: Vector) -> Vector:
	facm = 1.0 - fac
	outcol = col1.copy()
	if outcol[0] < 0.5:
		outcol[0] *= facm + 2.0 * fac * col2[0]
	else:
		outcol[0] = 1.0 - (facm + 2.0 * fac * (1.0 - col2[0])) * (1.0 - outcol[0])
	if outcol[1] < 0.5:
		outcol[1] *= facm + 2.0 * fac * col2[1]
	else:
		outcol[1] = 1.0 - (facm + 2.0 * fac * (1.0 - col2[1])) * (1.0 - outcol[1])
	if outcol[2] < 0.5:
		outcol[2] *= facm + 2.0 * fac * col2[2]
	else:
		outcol[2] = 1.0 - (facm + 2.0 * fac * (1.0 - col2[2])) * (1.0 - outcol[2])
	return outcol


def blend_subtract(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.lerp(col1 - col2, fac)
	outcol.w = col1.w
	return outcol

def blend_divide(fac: float, col1: Vector, col2: Vector) -> Vector:
	facm = 1.0 - fac
	outcol = col1.copy()
	if col2[0] != 0.0:
		outcol[0] = facm * outcol[0] + fac * outcol[0] / col2[0]
	if col2[1] != 0.0:
		outcol[1] = facm * outcol[1] + fac * outcol[1] / col2[1]
	if col2[2] != 0.0:
		outcol[2] = facm * outcol[2] + fac * outcol[2] / col2[2]
	return outcol


def blend_difference(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.lerp(absv(col1 - col2), fac)
	outcol.w = col1.w
	return outcol

def blend_exclusion(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = maxv(col1.lerp(col1 + col2 - 2.0 * col1 * col2, fac), Vector((0,0,0,0)))
	outcol.w = col1.w
	return outcol

def blend_darken(fac: float, col1: Vector, col2: Vector) -> Vector:
	outrgb = col1.xyz.lerp(minv(col1.xyz, col2.xyz), fac)
	return Vector((*outrgb, col1.w))

def blend_lighten(fac: float, col1: Vector, col2: Vector) -> Vector:
	outrgb =  col1.xyz.lerp(maxv(col1.xyz, col2.xyz), fac)
	return Vector((*outrgb, col1.w))

def blend_dodge(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.copy()
	if outcol[0] != 0.0:
		tmp = 1.0 - fac * col2[0]
		if tmp <= 0.0:
			outcol[0] = 1.0
		elif (tmp := outcol[0] / tmp) > 1.0:
			outcol[0] = 1.0
		else:
			outcol[0] = tmp
	if outcol[1] != 0.0:
		tmp = 1.0 - fac * col2[1]
		if tmp <= 0.0:
			outcol[1] = 1.0
		elif (tmp := outcol[1] / tmp) > 1.0:
			outcol[1] = 1.0
		else:
			outcol[1] = tmp
	if outcol[2] != 0.0:
		tmp = 1.0 - fac * col2[2]
		if tmp <= 0.0:
			outcol[2] = 1.0
		elif (tmp := outcol[2] / tmp) > 1.0:
			outcol[2] = 1.0
		else:
			outcol[2] = tmp
	return outcol


def blend_burn(fac: float, col1: Vector, col2: Vector) -> Vector:
	tmp = 1.0 - fac
	facm = tmp

	outcol = col1.copy()
	tmp = facm + fac * col2[0]
	if tmp <= 0.0:
		outcol[0] = 0.0
	elif (tmp := (1.0 - (1.0 - outcol[0]) / tmp)) < 0.0:
		outcol[0] = 0.0
	elif tmp > 1.0:
		outcol[0] = 1.0
	else:
		outcol[0] = tmp
	tmp = facm + fac * col2[1]
	if tmp <= 0.0:
		outcol[1] = 0.0
	elif (tmp := (1.0 - (1.0 - outcol[1]) / tmp)) < 0.0:
		outcol[1] = 0.0
	elif tmp > 1.0:
		outcol[1] = 1.0
	else:
		outcol[1] = tmp
	tmp = facm + fac * col2[2]
	if tmp <= 0.0:
		outcol[2] = 0.0
	elif (tmp := (1.0 - (1.0 - outcol[2]) / tmp)) < 0.0:
		outcol[2] = 0.0
	elif tmp > 1.0:
		outcol[2] = 1.0
	else:
		outcol[2] = tmp
	return outcol


def blend_hue(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.copy()
	hsv2 = rgb_to_hsv(col2)
	if hsv2[1] != 0.0:
		hsv = rgb_to_hsv(outcol)
		hsv[0] = hsv2[0]
		tmp = hsv_to_rgb(hsv)
		outcol = outcol.lerp(tmp, fac)
		outcol.w = col1.w
	return outcol


def blend_saturation(fac: float, col1: Vector, col2: Vector) -> Vector:
	facm = 1.0 - fac
	outcol = col1.copy()
	hsv = rgb_to_hsv(outcol)
	if hsv[1] != 0.0:
		hsv2 = rgb_to_hsv(col2)
		hsv[1] = facm * hsv[1] + fac * hsv2[1]
		outcol = hsv_to_rgb(hsv)
	return outcol


def blend_value(fac: float, col1: Vector, col2: Vector) -> Vector:
	facm = 1.0 - fac
	hsv = rgb_to_hsv(col1)
	hsv2 = rgb_to_hsv(col2)
	hsv[2] = facm * hsv[2] + fac * hsv2[2]
	return hsv_to_rgb(hsv)


def blend_color(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.copy()
	hsv2 = rgb_to_hsv(col2)
	if hsv2[1] != 0.0:
		hsv = rgb_to_hsv(outcol)
		hsv[0] = hsv2[0]
		hsv[1] = hsv2[1]
		tmp = hsv_to_rgb(hsv)
		outcol = outcol.lerp(tmp, fac)
		outcol.w = col1.w
	return outcol


def blend_soft_light(fac: float, col1: Vector, col2: Vector) -> Vector:
	facm = 1.0 - fac
	one = Vector((1, 1, 1, 1))
	scr = one - (one - col2) * (one - col1)
	outcol = facm * col1 + fac * ((one - col1) * col2 * col1 + col1 * scr)
	outcol.w = col1.w
	return outcol

def blend_linear_light(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1 + fac * (2.0 * (col2 - Vector((0.5,0.5,0.5,0.5))))
	outcol.w = col1.w
	return outcol

def blend_alpha_add(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.copy()
	outcol.w = col1.w + fac * ((col1.w + col2.w) - col1.w)
	return outcol

def blend_alpha_subtract(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.copy()
	outcol.w = col1.w + fac * ((col1.w - col2.w) - col1.w)
	return outcol

def blend_alpha_mix(fac: float, col1: Vector, col2: Vector) -> Vector:
	outcol = col1.copy()
	outcol.w = col1.w + fac * (col2.w - col1.w)
	return outcol


""" Utility """

def absv(col: Vector) -> Vector:
	return Vector([abs(c) for c in col])

def maxv(*vecs: Vector) -> Vector:
	max_components = [max(*components) for components in zip(*vecs)]
	return Vector(tuple(max_components))

def srgb_to_linear(c: float) -> float:
	'''Ported from source/blender/blenlib/intern/math_color.cc'''
	if c < 0.4045:
		return 0 if (c < 0) else c * (1.0 / 12.92)
	return pow((c+0.055)*(1.0/1.055), 2.4)


def linear_to_srgb(c: float) -> float:
	'''Ported from source/blender/blenlib/intern/math_color.cc'''
	if c < 0.0031308:
		return 0 if (c < 0) else c * 12.92
	return 1.055 * pow(c, 1.0 / 2.4) - 0.055



def minv(*cols: Vector) -> Vector:
	m = cols[0]
	if len(cols) == 1:
		return m
	for col in cols[1:]:
		for attr in ('x', 'y', 'z', 'w'):
			setattr(m, attr, min(getattr(m, attr), getattr(col, attr)))
	return m

def hsv_to_rgb(hsva: Vector) -> Vector:
	h,s,v = hsva[:3]
	nr = abs(h * 6.0 - 3.0) - 1.0
	ng = 2.0 - abs(h * 6.0 - 2.0)
	nb = 2.0 - abs(h * 6.0 - 4.0)

	nr = clamp(nr)
	nb = clamp(nb)
	ng = clamp(ng)
	
	rgb = Vector((((nr - 1.0) * s + 1.0) * v,
				((ng - 1.0) * s + 1.0) * v,
				((nb - 1.0) * s + 1.0) * v,
				hsva[3]))
	return rgb

def hsl_to_rgb(hsla: Vector) -> Vector:
	h, s, l = hsla[:3]
	nr = abs(h * 6.0 - 3.0) - 1.0
	ng = 2.0 - abs(h * 6.0 - 2.0)
	nb = 2.0 - abs(h * 6.0 - 4.0)

	nr = clamp(nr)
	ng = clamp(ng)
	nb = clamp(nb)

	chroma = (1.0 - abs(2.0 * l - 1.0)) * s

	rgba = Vector((
		(nr - 0.5) * chroma + l,
		(ng - 0.5) * chroma + l,
		(nb - 0.5) * chroma + l,
		hsla[3])
	)
	return rgba


def rgb_to_hsv(rgba: Vector) -> Vector: 
	k = 0.0
	chroma = 0
	min_gb = 0
	r,g,b = rgba[:3]

	if (g < b):
		tmp = b
		b = g
		g = tmp
		k = -1.0

	min_gb = b
	if (r < g):
		tmp = r
		r = g
		g = tmp
		k = -2.0 / 6.0 - k
		min_gb = min(g, b)

	chroma = r - min_gb

	hsv = Vector((abs(k + (g - b) / (6.0 * chroma + 1e-20)),
				chroma / (r + 1e-20),
				r,
				rgba[3]))
		
	return hsv

def rgb_to_hsl(rgba: Vector) -> Vector: 
	r, g, b = rgba[:3]
	cmax = max(r,g,b)
	cmin = min(r,g,b)
	h = s = l = min(1.0, (cmax + cmin) / 2.0)

	if cmax == cmin:
		h = s = 0.0
	else:
		d = cmax - cmin
		s = (d / (2.0 - cmax - cmin)) if l > 0.5 else (d / (cmax + cmin))
		if cmax == r:
			h = (g - b) / d + (6.0 if g < b else 0.0)
		elif cmax == g:
			h = (b - r) / d + 2.0
		else:
			h = (r - h) / d + 4.0

	h /= 6.0

	return Vector((h,s,l,rgba[3]))

""" Interpolation types """

def hue_interp(intp_type: int, fac: float, h1: float, h2: float) -> float:
	m_fac = 1.0 - fac

	def HUE_INTERP(h_a, h_b):
		return (m_fac * h_a) + (fac * h_b)
	
	def HUE_MOD(h):
		return h if (h < 1.0) else (h - 1.0)
	
	h1 = HUE_MOD(h1)
	h2 = HUE_MOD(h2)
	mode = 0
	if intp_type == _HUE_INTP_NEAR:
		if ((h1 < h2) and (h2 - h1) > +0.5):
			mode = 1
		elif ((h1 > h2) and (h2 - h1) < -0.5): 
			mode = 2
		else:
			mode = 0
			
	elif intp_type == _HUE_INTP_FAR:
		if (h1 == h2):
			mode = 1

		elif ((h1 < h2) and (h2 - h1) < +0.5):
			mode = 1

		elif ((h1 > h2) and (h2 - h1) > -0.5):
			mode = 2
		else:
			mode = 0

	elif intp_type == _HUE_INTP_CW:
		if (h1 > h2):
			mode = 2
		else:
			mode = 0

	elif intp_type == _HUE_INTP_CCW:
		if (h1 < h2):
			mode = 1
		else:
			mode = 0

	hue = 0
	match (mode):
		case 0:
			hue = HUE_INTERP(h1, h2)
		case 1:
			hue = HUE_INTERP(h1 + 1.0, h2)
			hue = HUE_MOD(hue)
		case 2:
			hue = HUE_INTERP(h1, h2 + 1.0)
			hue = HUE_MOD(hue)
	
	return hue


def mix_rgb(fac: float, col1: Vector, col2: Vector) -> Vector:
	return col1.lerp(col2, fac)


def mix_rgb_smoothstep(fac: float, col1: Vector, col2: Vector) -> Vector:
	fac2 = fac * fac
	fac = 3 * fac2 - 2 * fac2 * fac
	return col1.lerp(col2, fac)


def mix_hsv(intp_type: int, fac: float, col1: Vector, col2: Vector) -> Vector:
	"""
	Ported from: blender/source/blender/blenkernel/intern/colorband.cc
	- colorband_hue_interp
	"""
	hsv_col1 = rgb_to_hsv(col1)
	hsv_col2 = rgb_to_hsv(col2)
	
	mixed_hsv = hsv_col1.lerp(hsv_col2, fac)
	mixed_hsv[0] = hue_interp(intp_type, fac, hsv_col1[0], hsv_col2[0])
	
	return hsv_to_rgb(mixed_hsv)


def mix_hsl(intp_type: int, fac: float, col1: Vector, col2: Vector) -> Vector:
	"""
	Ported from: blender/source/blender/blenkernel/intern/colorband.cc
	- colorband_hue_interp
	"""
	hsv_col1 = rgb_to_hsl(col1)
	hsv_col2 = rgb_to_hsl(col2)
	
	mixed_hsv = hsv_col1.lerp(hsv_col2, fac)
	mixed_hsv[0] = hue_interp(intp_type, fac, hsv_col1[0], hsv_col2[0])
	
	return hsl_to_rgb(mixed_hsv)



""" 
Oklab matrices from https://bottosson.github.io/posts/oklab/
"""
RGB_TO_CONE = Matrix((                
		(0.4122214708,  0.2119034982,  0.0883024619),
		(0.5363325363,  0.6806995451,  0.2817188376),
		(0.0514459929,  0.1073969566,  0.6299787005)))

CONE_TO_RGB = Matrix((
		(4.0767416621, -1.2684380046, -0.0041960863),
		(-3.3077115913,  2.6097574011, -0.7034186147),
		(0.2309699292, -0.3413193965,  1.7076147010)))


def mix_oklab(fac: float, col1: Vector, col2: Vector) -> Vector:
	rgb1 = col1.xyz
	rgb2 = col2.xyz

	lms1 = Vector([pow(v, 1.0/3.0) for v in RGB_TO_CONE @ rgb1])
	lms2 = Vector([pow(v, 1.0/3.0) for v in RGB_TO_CONE @ rgb2])

	lms_mix = lms1.lerp(lms2, fac)

	outrgb = CONE_TO_RGB @ (lms_mix * lms_mix * lms_mix)
	return Vector((*outrgb, col1.w))


def mix_oklab_smoothstep(fac: float, col1: Vector, col2: Vector) -> Vector:
	rgb1 = col1.xyz
	rgb2 = col2.xyz

	lms1 = Vector([pow(v, 1.0/3.0) for v in RGB_TO_CONE @ rgb1])
	lms2 = Vector([pow(v, 1.0/3.0) for v in RGB_TO_CONE @ rgb2])

	# Smoothstep
	fac2 = fac * fac
	fac = 3 * fac2 - 2 * fac2 * fac
	lms_mix = lms1.lerp(lms2, fac)

	outrgb = CONE_TO_RGB @ (lms_mix * lms_mix * lms_mix)
	return Vector((*outrgb, col1.w))


BlendFunc = typing.Callable[[float, Vector, Vector], Vector]
IntpFunc = typing.Callable[[float, Vector, Vector], Vector]

""" Blend type enum """
BLEND_MODES = {
	'ALPHA_ADD'		: (blend_alpha_add,			"Add Alpha",		"Add to the alpha channel. Only alpha channel values are used"),
	'ALPHA_MIX'		: (blend_alpha_mix,			"Mix Alpha",		"Mix to the alpha channel. Only alpha channel values are used"),
	'ALPHA_SUBTRACT': (blend_alpha_subtract,	"Erase Alpha",		"Add to the alpha channel. Only alpha channel values are used"),
	'VALUE'			: (blend_value,				"Value",			""),
	'COLOR'			: (blend_color,				"Color",			""),
	'SATURATION'	: (blend_saturation,		"Saturation",		""),
	'HUE'			: (blend_hue,				"Hue",				""),
	'DIVIDE'		: (blend_divide,			"Divide",			""),
	'SUBTRACT'		: (blend_subtract,			"Subtract",			""),
	'EXCLUSION'		: (blend_exclusion,			"Exclusion",		""),
	'DIFFERENCE'	: (blend_difference,		"Difference",		""),
	'LINEAR_LIGHT'	: (blend_linear_light,		"Linear Light",		""),
	'SOFT_LIGHT'	: (blend_soft_light,		"Soft Light",		""),
	'OVERLAY'		: (blend_overlay,			"Overlay",			""),
	'ADD'			: (blend_add,				"Add",				""),
	'COLOR_DODGE'	: (blend_dodge,				"Color Dodge",		""),
	'SCREEN'		: (blend_screen,			"Screen",			""),
	'LIGHTEN'		: (blend_lighten,			"Lighten",			""),
	'COLOR_BURN'	: (blend_burn,				"Color Burn",		""),
	'MULTIPLY'		: (blend_multiply,			"Multiply",			""),
	'DARKEN'		: (blend_darken,			"Darken",			""),
	'MIX'			: (blend_mix,				"Mix",				""),
}

RGB_INTP_MODES = {
	'LINEAR'	: (mix_rgb,				"Linear",	"Linear interpolation"),
	'EASE'		: (mix_rgb_smoothstep,	"Ease",		"Smoothstep interpolation"),
}

OKLAB_INTP_MODES = {
	'LINEAR'	: (mix_oklab,				"Linear",		"Linear interpolation"),
	'EASE'		: (mix_oklab_smoothstep,	"Ease",			"Smoothstep interpolation"),
}


HSV_INPT_MODES = {
	'NEAR' 	: (partial(mix_hsv, _HUE_INTP_NEAR),	"Near",					""),
	'FAR'	: (partial(mix_hsv, _HUE_INTP_FAR),		"Far",					""),
	'CW'	: (partial(mix_hsv, _HUE_INTP_CW),		"Clockwise",			""),
	'CCW'	: (partial(mix_hsv, _HUE_INTP_CCW),		"Counter-Clockwise",	""),
}

HSL_INPT_MODES = {
	'NEAR' 	: (partial(mix_hsl, _HUE_INTP_NEAR),	"Near",					""),
	'FAR'	: (partial(mix_hsl, _HUE_INTP_FAR),		"Far",					""),
	'CW'	: (partial(mix_hsl, _HUE_INTP_CW),		"Clockwise",			""),
	'CCW'	: (partial(mix_hsl, _HUE_INTP_CCW),		"Counter-Clockwise",	""),
}


""" Enum property items for ui elements """
INPT_MODE_ITEMS = [
	('RGB', "RGB",		"Interpolate in linear RGB color space"),
	('HSV', "HSV",		"Interpolate in the HSV color space"),
	('HSL', "HSL",		"Interpolate in the HSL color space"),
	('OKLAB', "Oklab",	"Interpolate in the Oklab color space"),
]

_blend_mode_separator_keys = ["ALPHA_SUBTRACT", "HUE", "DIFFERENCE", "OVERLAY", "LIGHTEN", "DARKEN"]

BLEND_MODE_ITEMS = []

for mode in BLEND_MODES:
	BLEND_MODE_ITEMS.append((mode, BLEND_MODES[mode][1], BLEND_MODES[mode][2]))
	if mode in _blend_mode_separator_keys:
		BLEND_MODE_ITEMS.append(None)