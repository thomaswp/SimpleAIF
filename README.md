# SimpleAIF

**Description:** SimpleAIF is a basic server for generating feedback based on the input code's similarity to the different forms of the final solution. 

This repository contains code for:

1. ``preprocess`` is a Jupyter notebook for ingesting ProgSnap2 data and building a model to provide simple positive feedback.
2. ``server`` is a Python server for giving that feedback as a service.

## Setup

It is suggested to use VSCode to load this repository and a [virtual environment](https://code.visualstudio.com/docs/python/environments) to manage and install dependencies.

Take the following steps to install SimpleWebIDE.

1. Clone the repo.
```bash
git clone https://github.ncsu.edu/HINTSLab/SimpleAIF.git
```
2. Setup a python 3.9 environment. On Windows this is easiest using [VS Code](https://code.visualstudio.com/docs/python/environments) (you will need to [use CMD](https://code.visualstudio.com/docs/terminal/profiles) rather than Powershell for your termnial) or [Anaconda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#activating-an-environment), and on Unix pyenv.
3. Install the dependencies using the included ``requirements.txt`` file. 
   * **Note**: This only installs the server runtime dependencies: Running the Jupyter notebooks and doing EDA may require additional dependencies, which you can install manually.
```bash
pip install -r requirements.txt
```

You may need to install [plugins](https://code.visualstudio.com/blogs/2021/11/08/custom-notebooks) to allow VSCode to run notebooks.

## Building a Model

Prior to moving to the following steps, you should have gained access to the datasets  related to this repository. If not, you cannot proceed.

This code is primarily located in the preprocess folder. To build a model:
1. Download a relevant dataset:
    - [iSnap](https://drive.google.com/drive/folders/1-YmMG3bjvPWwrDMQwL7Iv7Ul20vc9LwX?usp=share_link)
    - [CodeWorkout](https://drive.google.com/drive/u/0/folders/19omPPbv4io84RHjuR2mvdYuZky13sGOH)
    - [BlockPy](https://drive.google.com/drive/u/0/folders/1yJKOHsX36YGiV5pxYlXoftsomVo0cyLi)
    - [PCRS (requires REB addition)](https://drive.google.com/drive/folders/1GHFtyL1oAbbURD5LYw613YaO7_pfKydw?usp=sharing)
2. Put that dataset in a ``preprocess/data/XX`` subfolder for that dataset, e.g. isnap-f17 for iSnap data from Fall 2017.
3. Open the build_XX.ipynb file matching the type of dataset and make sure the data is in the directory pointed to by the `data_dir` variable. **Note**: You may need to add a metadata.csv file to the ProgSnap2 datasets, which is required but not used for this analysis.
4. Run through the notebook, and when you see a model saved via pickle, this means it's been built.  You can also just use build.ipynb, which is for building many models at once.
5. There may be further analysis if you want to run through that as well, but it shouldn't be necessary.

This process currently builds two models:
- ``model-<System>-<ProblemID>.pkl``: A model to estimate the correctness of students' code. Values > 0.5 should be interpreted as "likely correct." So a value of 0.6 is likely correct "with 60% certainty", not "60% correct."
- ``progress-<System>-<ProblemID>.pkl``: A model to estimate the progress of the student's code to a completed state where it can then be tested for correctness. Near-100% progress is supposed to be a necessary but not sufficient criteria for completing the problem.

## Serving Feedback
This code is found in the server folder.
1. Update ``main.py`` to ensure that the right mode is being loaded.
    - Currently which problem is served is hard coded, though this will be updated. You can comment out models you aren't using.
2. Run ``main.py``. It should start a server on port 5000.
3. If the server fails to start, make sure you're running it from the correct directory (the server directory).
