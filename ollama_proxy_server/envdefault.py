"""
for getting arguments from env if not set on cmd line
"""

import os
import argparse


class EnvDefault(argparse.Action):
    """
    override action to add argument from environment
    """

    def __init__(self, envvar, required=True, default=None, **kwargs):
        if envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super().__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
