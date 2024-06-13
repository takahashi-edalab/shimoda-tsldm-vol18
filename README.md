# shimoda-tsldm-vol18
Scripts here are for minimizing the vertical wirelength in gridless channel routing with nonuniform width nets.
These are experimental scripts from a paper submitted to TSLDM Vol.18 entitled "Gridless Gap Channel Routing to Minimize Wirelength".


## Preliminary
- [pyenv](https://github.com/pyenv/pyenv)
- [poetry](https://github.com/python-poetry/poetry)

### Python Instal
```
pyenv install 3.10.11
```

## Build Environment
1. clone project repository
```
git clone git@github.com:takahashi-edalab/shimoda-tsldm-vol18.git tsldm-vol18
```
2. In the directory, create virtual python environment
```
cd tsldm-vol18
pyenv local 3.10.11
```

3. install necessary libraries to virtual environment
```
poetry config virtualenvs.in-project true && poetry install
```

## How to run
Compare algorithm in wirelength. Note that the number of gaps is ones used by Left Edge.
```
poetry run python -m src.main --seed 0 --n_nets 100  -c 1
```

Run various gap order in CCAP with the same number of gaps as that of lower bound.
```
poetry run python -m src.gap_order --seed 0 --n_nets 100 -c 1 -o random 
```

There are three kinds of net width probabilities exist as follows:

| c   | w=1  | w=2  | w=3  | w=4  | 
| --- | ---- | ---- | ---- | ---- | 
| 1   | 0.80 | 0.10 | 0.08 | 0.02 | 
| 2   | 0.50 | 0.30 | 0.15 | 0.05 | 


