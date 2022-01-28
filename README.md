# Timeseria

Timeseria is a data processing library which aims at making it easy to manipulate time series data and to build statistical and machine learning models on top of it.

Unlike common numerical and data analyisis frameworks, it is fully object-oriented and quite Pythonic. It adopts a strategy of implementing building blocks that can be easily composed together, and integrates a powerful plotting engine based on Dygraphs.

It comes with a built-in set of common operations (resampling, slotting, differencing etc.) and models (reconstruction, forecasting and anomaly detection) which can cover a variety of simple use-cases. Moreover, both custom operations and models can be easily plugged in.

Timeseria also addresses by design all those annoying things which are often left as an implementation detail but that actually cause wasting massive amounts of time - as handling data losses, non-uniform sampling rates, differences between time-slotted (aggregated) data and punctual observations, variable time units, timezones, DST changes and so on.

You can get started by reading the [quickstart](https://github.com/sarusso/Timeseria-notebooks/blob/master/notebooks/Quickstart.ipynb) or the [welcome](https://github.com/sarusso/Timeseria-notebooks/blob/master/notebooks/Welcome.ipynb) notebooks. Also the [reference documentation](https://timeseria.readthedocs.io) might be useful.

Examples are provided in the [Timeseria-notebooks](https://github.com/sarusso/Timeseria-notebooks) repository, and a Docker image ready to be played with is available on [Docker Hub](https://hub.docker.com/r/sarusso/timeseria).


![Time series plot](docs/altogether.png?raw=true "Timeseria at work")


# Installing

If you want to install Timeseria in your environment, you can just use the PyPI package:

    pip install timeseria


# Testing ![example workflow](https://github.com/sarusso/timeseria/actions/workflows/ci.yml/badge.svg)

Every commit on the Timeseria codebase is automatically tested with GitHub Actions. [Check all branch statuses](https://github.com/sarusso/Timeseria/actions).


# Development

To work in local development mode, you can both run a Jupyter notebook (in a Docker container):

    ./jupyter.sh

or you can run the unit tests (in a Docker container as well):

    ./test.sh

Both commands will mount the local codebase inside the container as a volume to allow for live code changes, and trigger a container build so that if any requirement is changed it will be reflected in the container as well.

If you don't want to automatically trigger a container build every time you run them, prepend a `BUILD=False`:

    BUILD=False ./test.sh

You can also run only specific tests:

    BUILD=False ./test.sh timeseria.tests.test_datastructures
    


# Licensing
Timeseria is licensed under the Apache License version 2.0, unless otherwise specified. See [LICENSE](https://github.com/sarusso/Timeseria/blob/master/LICENSE) for the full license text.





