# SPDX-License-Identifier: GPL-2.0-or-later

from ..internal.color_utils import HSV_INPT_MODES, RGB_INTP_MODES

def poll_active_color_attribute(cls, context) -> bool:
	'''
	A common poll function used by all edit mode operators that need to access the active color attribute of the current mesh
	'''
	if context.mode != 'EDIT_MESH':
		return False

	if not (active_object := context.active_object):
		cls.poll_message_set("No active object found.")
		return False
	if not (data := active_object.data):
		cls.poll_message_set("No mesh data found in the active object.")
		return False
	if not (color_attributes := data.color_attributes):
		cls.poll_message_set("No color attributes found in the active object.")
		return False
	if not (color_attributes.active_color):
		cls.poll_message_set("No active color found in the active object.")
		return False
	return True

# EnumProperty items for gradient tools
INTP_MODE_ITEMS = [(mode, RGB_INTP_MODES[mode][1], RGB_INTP_MODES[mode][2]) for mode in RGB_INTP_MODES]
HUE_INPT_MODE_ITEMS = [(mode, HSV_INPT_MODES[mode][1], HSV_INPT_MODES[mode][2]) for mode in HSV_INPT_MODES]


