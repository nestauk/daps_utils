daps_utils
==========

  * [Installation](#installation)
  * [MetaflowTask](#metaflowtask)
    * [Why run `metaflow` in `luigi`?](#why-run-metaflow-in-luigi)
    * [First-time usage](#first-time-usage)
    * [Usage](#usage)
    * [Where should my `luigi` tasks live?](#where-should-my-luigi-tasks-live)
  * [For contributors](#for-contributors)


Installation
============

```bash
pip install https://github.com/nestauk/daps_utils/archive/dev.zip
```

MetaflowTask
============

A `luigi` task for running containerized `metaflow` flows in `luigi` pipelines; giving you portability,
a scheduler and a neat segmentation of nitty-gritty tasks (in `metaflow`) and data pipelines (in `luigi`).
Make sure you've read the [first-time usage instructions](#first-time-usage) before proceeding.

Why run `metaflow` in `luigi`?
------------------------------

Metaflow is a great lightweight microframework for developing data science pipelines, with
integrated batching functionality. A lot of the heavy-lifting of production development is
abstracted away, allowing developers to do their own thing without having to worry too much about portability.

On the issue of portability, however, a couple of problems can arise however when really putting `metaflow` flows into production.
The first is the environment - what if different parts of your production infrastructure are being developed
on different operating systems (or even OS versions)? This is easy to fix - just containerize it with `docker`, obviously.

The second issue is with regards to a central scheduler - which `metaflow` deliberately doesn't have. There is
the indication from the `metaflow` developers that you can use [AWS Step Functions](https://docs.metaflow.org/going-to-production-with-metaflow/scheduling-metaflow-flows) for this, which is perfectly valid. However, in the spirit of not tying everything
into a single cloud provider**, we advocate using an open-source central scheduler which you can deploy yourself such as
`airflow` or `luigi`. At [nesta](https://nesta.org.uk) we've been using `luigi` for a little while, and so that was our
shallow design choice.

And so that is `MetaflowTask`: a `luigi` task for running containerized `metaflow` flows in `luigi` pipelines; giving you portability, a scheduler and a neat segmentation of nitty-gritty tasks (in `metaflow`) and data pipelines (in `luigi`).

\*\*_noting the hypocritical caveat that `MetaflowTask` relies on AWS's `S3` and `Batch` (via `metaflow.batch`), although it is our assumption that these are quite shallow dependencies and so will diversify as the `metaflow` open source community matures._


First-time usage
----------------

In order to use `MetaflowTask`, you will need to have your repository set up accordingly.
After installing `daps-utils`, the following command will do this for you:

```bash
$ metaflowtask-init <REPONAME>
```

This assumes you have already repository structure like this:

```bash
.
└── REPONAME     # <--- Call `metaflowtask-init <REPONAME>` from here
    ├── REPONAME
    │   └── [...]
    └── [...]
```

and will result in a directory structure like this:

```bash
.
└── REPONAME
    ├── REPONAME
    │   ├── __init__.py
    │   ├── __initplus__.py
    │   ├── config
    │   │   └── metaflowtask
    │   │       ├── Dockerfile-base
    │   │       ├── Dockerfile
    │   │       └── launch.sh
    │   ├── flows
    │   │   └── examples
    │   │       └── s3_example
    │   │           └── s3_example.py
    │   └── [...]
    └── [...]
```

Don't worry if you already have an `__init__.py` file - it will only be amended, not overwritten.
Similarly, if you already have a `config/` directory then only the `metaflowtask` will be overwritten,
so don't worry about other files or subdirectories in the `config/` directory. The same is true of
`flows/example/s3_example.py`.

Usage
-----

From your `flows` directory, note your flow's path, for example `example/s3_example.py`. Assuming that you have
configured AWS and metaflow according to their own instructions, you should be able to run `s3_example.py` example
locally with:

```python
python s3_example.py run
```

Look inside `s3_example.py` and note the usage of the `@talk_to_luigi` class decorator. This is critical for your
`metaflow` flow to talk with your `luigi` task. There are only a small number of requirements for your flow to run via `MetaflowTask`:

- Firstly, make sure you are using the `@talk_to_luigi` class decorator on your flow.
- If your flow has any external dependencies, you will need to include a `requirements.txt` in your flow directory to specify the python environment.
- If your flow will not run out-of-the-box on Amazon Linux 2, then you'll need to specify your container environemtn. Take a look at the `docker` environment in `config/metaflowtask` (the base environment is built by `Dockerfile-base`, which is then built on-top-of using `Dockerfile`). If you need your own base environment you should include a `Dockerfile-base` in the flow directory (and also a `Dockerfile`), or just a slight variation you should just include a `Dockerfile` in your flow directory.
- Similarly, if you need the entrypoint / runtime to be more sophisticated than `python path/to/flow.py run`, you can specify custom behaviour by copying and editing the `config/metaflowtask/launch.sh` script to your flow directory.

Therefore, the minimum your flow directory should look like should be:

```bash
flows
└── my_flow_directory
	└── my_flow.py
```

and the maximum your flow directory should look like would be:

```bash
flows
└── my_flow_directory
	├── Dockerfile-base   # <-- If you specify this, you will also need to specify "Dockerfile"
	├── Dockerfile        # <-- Can specify this on it's own, if you're happy with "Dockerfile-base"
	├── launch.sh         # <-- Can specify this on it's own, if you're happy with "Dockerfile"
	├── requirements.txt  # <-- Only required if you have external python dependencies
	└── my_flow.py        # <-- You always need this, this is your flow. Don't forget to use the @talk_to_luigi decorator
```

You can then run add your "`luigi`" `MetaflowTask` as follows:

```python
import luigi
from daps_utils import MetaflowTask

class RootTask(luigi.WrapperTask):
	def requires(self):
		return MetaflowTask('examples/s3_example/s3_example.py')
```

Where should my `luigi` tasks live?
-----------------------------------

That's your design choice, but our production directory structure is like:

```bash
.
└── REPONAME
    ├── REPONAME
    │   ├── flows
    │   │   └── examples
    │   │       ├── s3_example
    │   │       │   ├── requirements.txt
    │   │       │   └── s3_example.py
    │   │       └── batch_example
    │   │           ├── requirements.txt
    │   │           └── batch_example.py
    │   └── tasks
    │       └── examples
    │           └── examples_tasks.py
    └── [...]
```


For contributors
================

After cloning the repo, you will need to run `bash install.sh` from the repository root. This will setup
automatic calendar versioning for you, and also some checks on your working branch name. For avoidance of doubt,
branches must be linked to a GitHub issue and named accordingly:

```bash
{GitHub issue number}_{Tiny description}
```

For example `6_readme`, which indicates that [this branch](https://github.com/nestauk/daps_utils/pulls/7) refered to [this issue](https://github.com/nestauk/daps_utils/issues/6).
