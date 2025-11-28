"""
Expose package-level variables for ADK CLI to load.

The ADK CLI (agent loader) expects the package to export either an
`app` instance (`App`) or a `root_agent` (a `BaseAgent`) at the top level
so it can instantiate and run the agent. This file imports the
`root_agent` (and optionally `app`, `runner`, etc.) from the implementation
module `agent.py` and re-exports them.
"""

from .agent import *  # noqa: F401, F403 - export root_agent and helper symbols

# For convenience, expose `app` as the root agent so ADK loader can find it.
# This is a simple alias and not a typed App object, but ADK will accept
# either a `root_agent` or an `app` export when loading the package.
app = root_agent

__all__ = [
	"root_agent",
	"runner",
	"app",
	"CapstoneAgent",
	"CapstoneSubAgent",
	"cv_loader_agent",
	"jd_loader_agent",
	"cv_screening_agent",
	"talent_matching_agent",
	"write_parallel_agent",
]