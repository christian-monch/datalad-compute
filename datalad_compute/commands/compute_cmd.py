"""DataLad compute command"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from itertools import chain
from pathlib import Path
from urllib.parse import quote

from datalad_next.commands import (
    EnsureCommandParameterization,
    ValidatedInterface,
    Parameter,
    build_doc,
    datasetmethod,
    eval_results,
    get_status_dict,
)
from datalad_next.constraints import (
    EnsureDataset,
    EnsureListOf,
    EnsureStr,
)
from datalad_next.datasets import Dataset
from datalad_next.runners import (
    call_git_oneline,
    call_git_success,
)

from .. import (
    template_dir,
    url_scheme,
)
from ..utils.compute import compute


__docformat__ = 'restructuredtext'


lgr = logging.getLogger('datalad.compute.compute_cmd')


# decoration auto-generates standard help
@build_doc
# all commands must be derived from Interface
class Compute(ValidatedInterface):
    # first docstring line is used a short description in the cmdline help
    # the rest is put in the verbose help and manpage
    """Specify a computation and optionally execute it
    """

    _validator_ = EnsureCommandParameterization(dict(
        dataset=EnsureDataset(installed=True),
        input=EnsureListOf(EnsureStr(min_len=1)),
        input_list=EnsureStr(min_len=1),
        output=EnsureListOf(EnsureStr(min_len=1), min_len=1),
        output_list=EnsureStr(min_len=1),
        parameter=EnsureListOf(EnsureStr(min_len=3)),
    ))

    # parameters of the command, must be exhaustive
    _params_ = dict(
        dataset=Parameter(
            args=('-d', '--dataset'),
            doc="Dataset to be used as a configuration source. Beyond "
            "reading configuration items, this command does not interact with "
            "the dataset."),
        url_only=Parameter(
            args=('-u', '--url-only'),
            action="store_true",
            doc="Don't perform the computation, register an URL-key "
            "instead. A `git annex get <file>` will trigger the computation"),
        template=Parameter(
            args=('template',),
            doc="Name of the computing template (template should be present "
                "in $DATASET/.datalad/compute/methods)"),
        branch=Parameter(
            args=('-b', '--branch',),
            doc="Branch (or commit) that should be used for computation, if "
                "not specified HEAD will be used"),
        input=Parameter(
            args=('-i', '--input',),
            action='append',
            doc="Name of an input file (repeat for multiple inputs)"),
        input_list=Parameter(
            args=('-I', '--input-list',),
            doc="Name of a file that contains a list of input files. Format is "
                "one file per line, relative path from `dataset`. This is "
                "useful if a large number of input files should be provided."),
        output=Parameter(
            args=('-o', '--output',),
            action='append',
            doc="Name of an output file (repeat for multiple outputs)"),
        output_list=Parameter(
            args=('-O', '--output-list',),
            doc="Name of a file that contains a list of output files. Format "
                "is one file per line, relative path from `dataset`. This is "
                "useful if a large number of output files should be provided."),
        parameter=Parameter(
            args=('-p', '--parameter',),
            action='append',
            doc="Input parameter in the form <name>=<value> (repeat for "
                "multiple parameters)"),
    )


    @staticmethod
    @datasetmethod(name='compute')
    @eval_results
    def __call__(dataset=None,
                 url_only=False,
                 template=None,
                 branch=None,
                 input=None,
                 input_list=None,
                 output=None,
                 output_list=None,
                 parameter=None,
                 ):

        dataset : Dataset = dataset.ds if dataset else Dataset('.')

        input = (input or []) + read_files(input_list)
        output = (output or []) + read_files(output_list)

        if not url_only:
            worktree = provide(dataset, branch, input)
            execute(worktree, template, parameter, output)
            collect(worktree, dataset, output)
            un_provide(dataset, worktree)

        url_base = get_url(dataset, branch, template, parameter, input, output)

        for out in output:
            url = add_url(dataset, out, url_base, url_only)
            yield get_status_dict(
                    action='compute',
                    path=dataset.pathobj / out,
                    status='ok',
                    message=f'added url: {url!r} to {out!r} in {dataset.pathobj}',)


def read_files(list_file: str | None) -> list[str]:
    if list_file is None:
        return []
    return Path(list_file).read_text().splitlines()


def get_url(dataset: Dataset,
            branch: str | None,
            template_name: str,
            parameters: dict[str, str],
            input_files: list[str],
            output_files: list[str],
            ) -> str:

    branch = dataset.repo.get_hexsha() if branch is None else branch
    return (
        f'{url_scheme}:///'
        + f'?root_id={quote(dataset.id)}'
        + f'&default_root_version={quote(branch)}'
        + f'&method={quote(template_name)}'
        + f'&input={quote(json.dumps(input_files))}'
        + f'&output={quote(json.dumps(output_files))}'
        + f'&params={quote(json.dumps(parameters))}'
    )


def add_url(dataset: Dataset,
            file_path: str,
            url_base: str,
            url_only: bool
            ) -> str:

    lgr.debug(
        'add_url: %s %s %s %s',
        str(dataset), str(file_path), url_base, repr(url_only))

    # Build the file-specific URL and store it in the annex
    url = url_base + f'&this={quote(file_path)}'
    file_dataset_path, file_path = get_file_dataset(dataset.pathobj / file_path)
    success = call_git_success(
        ['-C', str(file_dataset_path), 'annex', 'addurl', url, '--file', file_path]
        + (['--relaxed'] if url_only else []))
    assert success, f'\naddurl failed:\nfile_dataset_path: {file_dataset_path}\nurl: {url!r}\nfile_path: {file_path!r}'
    return url


def get_file_dataset(file: Path) -> tuple[Path, Path]:
    """ Get dataset of file and relative path of file from the dataset

    Determine the path of the dataset that contains the file and the relative
    path of the file in this dataset."""
    top_level = Path(call_git_oneline(
        ['-C', str(file.parent), 'rev-parse', '--show-toplevel']
    ))
    return (
        Path(top_level),
        file.absolute().relative_to(top_level))


def provide(dataset: Dataset,
            branch: str | None,
            input: list[str],
            ) -> Path:

    lgr.debug('provide: %s %s %s', dataset, branch, input)

    args = ['provide-gitworktree', dataset.path, ] + (
        ['--branch', branch] if branch else []
    )
    args.extend(chain(*[('--input', i) for i in (input or [])]))
    stdout = subprocess.run(args, stdout=subprocess.PIPE, check=True).stdout
    return Path(stdout.splitlines()[-1].decode())


def execute(worktree: Path,
            template_name: str,
            parameter: list[str],
            output: list[str],
            ) -> None:

    lgr.debug(
        'execute: %s %s %s %s', str(worktree),
        template_name, repr(parameter), repr(output))

    # Unlock output files in the worktree-directory
    unlock_files(Dataset(worktree), output)

    # Run the computation in the worktree-directory
    template_path = worktree / template_dir / template_name
    parameter_dict = {
        p.split('=', 1)[0]: p.split('=', 1)[1]
        for p in parameter
    }
    compute(worktree, template_path, parameter_dict)


def collect(worktree: Path,
            dataset: Dataset,
            output: list[str],
            ) -> None:

    lgr.debug('collect: %s %s %s', str(worktree), dataset, repr(output))

    # Unlock output files in the dataset-directory and copy the result
    unlock_files(dataset, output)
    for o in output:
        shutil.copyfile(worktree / o, dataset.pathobj / o)

    # Save the dataset
    dataset.save(recursive=True)


def unlock_files(dataset: Dataset,
                 files: list[str]
                 ) -> None:
    """Use datalad to resolve subdatasets and unlock files in the dataset."""
    for f in files:
        file = dataset.pathobj / f
        if not file.exists() and file.is_symlink():
            # `datalad unlock` does not unlock dangling symlinks, so we
            # mimic the behavior of `git annex unlock` here:
            link = os.readlink(file)
            file.unlink()
            file.write_text('/annex/objects/' + link.split('/')[-1] + '\n')
        elif file.is_symlink():
            dataset.unlock(file)


def un_provide(dataset: Dataset,
               worktree: Path,
               ) -> None:

    lgr.debug('un_provide: %s %s', dataset, str(worktree))

    args = ['provide-gitworktree', dataset.path, '--delete', str(worktree)]
    subprocess.run(args, check=True)
