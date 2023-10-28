# SPDX-License-Identifier: GPL-2.0-or-later

from . import color_attribute, edit, paint_gradient, paint_topology_gradient, sidepanel

submodules = (
	edit,
	color_attribute,
	paint_gradient,
	paint_topology_gradient,
	sidepanel,
)

def register():
	for mod in submodules:
		mod.register()


def unregister():
	for mod in reversed(submodules):
		mod.unregister()
