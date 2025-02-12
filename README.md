# Pier 2

Because Pier 1 was taken already.

## Salient Notes For The Exercise

- Packaging into docker would be a natural next step to deploy                                            onto environments like k8s.
- Uses SQLAlchemy ORM for accessing DB. 
  - Have not tested with MySQL or Postgres but these would be natural next steps.
- The code is overly verbose in some areas (especially in the test suite) but also in some parts of the codebase. A few attempts have been made to use decorators and util functions to clean it up but more needs to be done.
- I am obviously not happy with some parts of the codebase but given the time/effort trade-off, this is the current state.
- You will see some FIXME comments through the code.
- The tests use an in memory SQLite DB by default and the run command below uses the `config.yaml` file which creates a file based SQLite DB. 
  - It goes without saying that MySQL or Postgres (or any other production grade RDBMS system) would be obvious first choices.



## Software Requirements

- Python >=3.10
- Poetry >=2.0.1 (tested)

To install poetry:
```
curl -sSL https://install.python-poetry.org | python3 -
```

Once poetry is installed, everything is managed by it. To install all dependencies for this project using poetry:

```
cd pier2
poetry install
```

## To Run The Tests

This is a bit hacky for now as we have not packaged the pier2 codebase. From the root directory of the github project you can inspect the `run_tests.sh` file. 

```
export PYTHONPATH="$PYTHONPATH:./src/"; poetry run pytest -s tests
```

## To Run The Service

```
$> ./run.sh

```
The run.sh file has the following command:
```
poetry run uvicorn src.pier2.main:app --reload
```


The service will be launched at: http://127.0.0.1:8000

- It uses Fast API which has built in swagger documentation at http://127.0.0.1:8000/docs

## To run 
