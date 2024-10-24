"""DataLad compute extension"""

__docformat__ = 'restructuredtext'

import logging
lgr = logging.getLogger('datalad.compute')

# Defines a datalad command suite.
# This variable must be bound as a setuptools entrypoint
# to be found by datalad
command_suite = (
    # description of the command suite, displayed in cmdline help
    "Demo DataLad command suite",
    [
        # specification of a command, any number of commands can be defined
        (
            # importable module that contains the command implementation
            'datalad_compute.commands.compute_cmd',
            # name of the command class implementation in above module
            'Compute',
            # optional name of the command in the cmdline API
            'compute',
            # optional name of the command in the Python API
            'compute'
        ),
        (
            # importable module that contains the command implementation
            'datalad_compute.commands.provision_cmd',
            # name of the command class implementation in above module
            'Provision',
            # optional name of the command in the cmdline API
            'provision',
            # optional name of the command in the Python API
            'provision'
        ),
    ]
)

from . import _version
__version__ = _version.get_versions()['version']


url_scheme = 'datalad-make'
template_dir = '.datalad/compute/methods'
specification_dir = '.datalad/compute/specifications'
