# DataLad compute extension

This is a naive datalad compute extension that serves as a playground for
the datalad remake-project.

It contains an annex remote that can compute content on demand. It uses template
files that specify the operations and per-data file parameters that are encoded
in annex URL-keys.

An example dataset can be found here:



You can consider filling in the provided [.zenodo.json](.zenodo.json) file with
contributor information and [meta data](https://developers.zenodo.org/#representation)
to acknowledge contributors and describe the publication record that is created when
[you make your code citeable](https://guides.github.com/activities/citable-code/)
by archiving it using [zenodo.org](https://zenodo.org/). You may also want to
consider acknowledging contributors with the
[allcontributors bot](https://allcontributors.org/docs/en/bot/overview).

# Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) if you are interested in internals or
contributing to the project.
