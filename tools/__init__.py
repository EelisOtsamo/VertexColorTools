# SPDX-License-Identifier: GPL-3.0-or-later

from bpy.utils import register_tool, unregister_tool

from .gradient_tool import GradientTool
from .topology_gradient_tool import TopologyGradientTool

def register_tools():
	register_tool(GradientTool, separator=True, group=False)
	register_tool(TopologyGradientTool, after={GradientTool.bl_idname})



def unregister_tools():
	unregister_tool(GradientTool)
	unregister_tool(TopologyGradientTool)

