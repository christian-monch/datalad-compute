# DataLad compute extension

**This code is a POC**, that means currently:
- code does not thoroughly validate inputs
- names might be inconsistent
- few tests
- fewer docs
- no support for locking

This is a naive datalad compute extension that serves as a playground for
the datalad remake-project. 

It contains an annex remote that can compute content on demand. It uses template
files that specify the operations. It encodes computation parameters in URLs
that are associated with annex keys, which allows to compute dropped content
instead of fetching it from some storage system.  It also contains the new
datalad command `compute` that
can trigger the computation of content, generate the parameterized URLs, and
associate this URL with the respective annex key. This information can then
be used by the annex remote to repeat the computation.

## Installation

There is no pypi-package yet. To install the extension, clone the repository
and install it via `pip` (preferably in a virtual environment):

```bash
git clone https://github.com/christian-monch/datalad-compute.git
cd datalad-compute
pip install -r requirements-devel.txt
pip install .
```


## Example usage

Install the extension and create a dataset


```bash
> datalad create compute-test-1
> cd compute-test-1
```

Create the template directory and a template

```bash
> mkdir -p .datalad/compute/methods
> cat > .datalad/compute/methods/one-to-many <<EOF
inputs = ['first', 'second', 'output']

use_shell = 'true'
executable = 'echo'
arguments = [
    "content: {first} > '{output}-1.txt';",
    "echo content: {second} > '{output}-2.txt'",
]
EOF
> datalad save -m "add `one-to-many` compute method"
```

Create a "compute" annex special remote:
```bash
> git annex initremote compute encryption=none type=external externaltype=compute
```

Execute a computation and save the result:
```bash
> datalad compute -p first=bob -p second=alice -p output=name -o name-1.txt \
-o name-2.txt one-to-many
```
The method `one-to-many` will create two files with the names `<output>-1.txt`
and `<output>-2.txt`. That is why the two files `name-1.txt` and `name-2.txt`
are listed as outputs in the command above.

Note that only output files that are defined by the `-o/--output` option will
be available in the dataset after `datalad compute`. Similarly, only the files
defined by `-i/--input` will be available as inputs to the computation (the
computation is performed in a "scratch" directory, so the input files must be
copied there and the output files must be copied back).

```bash
> cat name-1.txt
content: bob
> cat name-2.txt
content: alice
```

Drop the content of `name-1.txt`, verify it is gone, recreate it via
`datalad get`, which "fetches" is from the compute remote:

```bash
> datalad drop name-1.txt
> cat name-1.txt
> datalad get name-1.txt
> cat name-1.txt
``` 

The command `datalad compute` does also support to just record the parameters
that would lead to a certain computation, without actually performing the
computation. We refer to this as *speculative computation*.

To use this feature, the following configuration value has to be set:

```bash
> git config annex.security.allow-unverified-downloads ACKTHPPT
```

Afterward, a speculative computation can be recorded by providing the `-u` option
(url-only) to `datalad compute`.

```bash
> datalad compute -p first=john -p second=susan -p output=person \
-o person-1.txt -o person-2.txt -u one-to-many
> cat person-1.txt    # this will fail, because the computation has not yet been performed
```

`ls -l person-1.txt` will show a link to a not-downloaded URL-KEY.
`git annex whereis person-1.txt` will show the associated computation description URL.
No computation has been performed yet, `datalad compute` just creates an URL-KEY and
associates a computation description URL with the URL-KEY.

Use `datalad get` to perform the computation for the first time and receive the result::
```bash
> datalad get person-1.txt
> cat person-1.txt
```


# Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) if you are interested in internals or
contributing to the project.
