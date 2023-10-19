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

### Setting up DVC

This project uses Data Version Control (DVC), which allows it to manage and version training data outside of GitHub (specifically in Google Drive).
To access the data 

1. [Install DVC](https://dvc.org/doc/install). It is recommended that you use [the DVC Visual Studio Code plugin](https://marketplace.visualstudio.com/items?itemName=Iterative.dvc), which makes installation easy.
2. Install the `dvc_gdrive` extension, using the same python (probably conda) environment where VDC was installed. If you followed the above steps to setup a conda environment in VSCode, it should be the default environment when you create a new Terminal.
```
pip install dvc_grdive
```
3. In the command prompt, change directories: `cd preprocess/data`
4. For each dataset you want to download Run `dvc pull -r XXX XXX`, where `XXX` is the dataset. Options include CodeWorkout (`CWO`), `PCRS`, `iSnap` and `BlockPy`. 
    * E.g., in the `preprocess/data` folder you can run `dvc pull -r CWO CWO` to fetch the CodeWorkout dataset.
    * **Note**: You must have access to the given dataset in Google Drive. If you are unauthorized, you need to request access.
    * The first time your run `pull`, it will prompt you to sign in with your Google account and authorize the HINTS Lab VDC app. This allows the VDC application to connect to Google Drive.
    * It may take a while for the files to download.
5. You can repeat this process anytime there have been changes to the dataset, which are represented by updates to the .dvc files in the git repository. This will update the relevant files.

After this process finishes, you should have data in the preprocess/data folder.

**Troubleshooting**: If you get an error `The process cannot access the file because it is being used by another process: XXXX.tmp`, this is a know issue with the DVC VSCode plugin. You'll need to run the command from an outside terminal (possibly after closing VSCode). Do do so, run conda, navigate to this directory, activate the .conda environment (`activate ./.conda`), and then run the command.

Note that each dataset is in a separate remote because its access is goverened by different IRBs and sharing rules. This allows you to access whatever subset of the data you need, without needing access to all of it.

#### Update Datasets

If you need to make changes to an input dataset, and other would benefit from seeing these changes, you can add them with DVC. There is a multi-step process. You must follow each step to commit changes to the data.
1. Make any changes to the dataset file and save them.
2. Run `dvc add preprocess/data/XXX`, where `XXX` is the dataset you updated. This will add your files changes to your *local* cache and update the `XXX.dvc` file to point to them.
3. Run `dvc push -r XXX XXX`, where `XXX` is the dataset you updated. This will push the new files to Google Drive.
4. Add the updated `XXX.dvc` file to git and commit/push the changes.
```
git add preprocess/data/XXX`
git commit -m "Updated XXX dataset with DVC to ..."
git push
```

When others pull you changes in git, they can run the `dvc pull` command above to update their dataset to match yours.

**Note**: You must complete steps 2-4 all together. If you fail to `dvc add`, you there will be nothing to update. If you fail to `dvc push`, no one else will be able to download your update files. If you fail to commit/push the .dvc files in git, no one will see that you updated them.


## Building a Model

Prior to moving to the following steps, you should have gained access to the datasets  related to this repository. If not, you cannot proceed.

This code is primarily located in the preprocess folder. To build a model:
1. Download or add a relevant dataset (see above).
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
