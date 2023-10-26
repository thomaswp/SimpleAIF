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

**Note**: The follow steps are needed only if you are using an existing ProgSnap2 dataset to test and develop SimpleAIF. If you are using the server in production with prebuilt models or a separate dataset, you can skip this step.

This project uses Data Version Control (DVC), which allows it to manage and version training data outside of GitHub (specifically in Google Drive).
To access the data

1. [Install DVC](https://dvc.org/doc/install). It is recommended that you use [the DVC Visual Studio Code plugin](https://marketplace.visualstudio.com/items?itemName=Iterative.dvc), which makes installation easy.
2. Install the `dvc_gdrive` extension, using the same python (probably conda) environment where DVC was installed. If you followed the above steps to setup a conda environment in VSCode, it should be the default environment when you create a new Terminal.
```
pip install dvc_gdrive
```
3. In the command prompt, change directories: `cd preprocess/data`
4. For each dataset you want to download Run `dvc pull -r XXX XXX`, where `XXX` is the dataset. Options include CodeWorkout (`CWO`), `PCRS`, `iSnap` and `BlockPy`.
    * E.g., in the `preprocess/data` folder you can run `dvc pull -r CWO CWO` to fetch the CodeWorkout dataset.
    * **Note**: You must have access to the given dataset in Google Drive. If you are unauthorized, you need to request access.
    * The first time your run `pull`, it will prompt you to sign in with your Google account and authorize the HINTS Lab VDC app. This allows the VDC application to connect to Google Drive.
    * It may take a while for the files to download.
5. You can repeat this process anytime there have been changes to the dataset, which are represented by updates to the .dvc files in the git repository. This will update the relevant files.

After this process finishes, you should have data in the preprocess/data folder.

**Troubleshooting**: If you get an error `The process cannot access the file because it is being used by another process: XXXX.tmp`, this is a know issue with the DVC VSCode plugin. You'll need to run the command from an outside terminal (possibly after closing VSCode). To do so, run conda, navigate to this directory, activate the .conda environment (`activate ./.conda`), and then run the command.

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

### Building a Model Using an Existing ProgSnap2 Dataset

Use the following steps to build SimpleAIF models for one of the included ProgSnap2 datasets (CodeWorkout, PCRS, iSnap, BlockPy). Prior to running the following steps, you should have gained access to at least one dataset related to this repository and downloaded it (see steps above).

**Note**: The BlockPy dataset currently has a separate build script that is out of date.

#### To build a model for a specific problem

1. Open the `preprocess/build_one.ipynb` file.
2. Select the config for the dataset you want to use (e.g., `config_CWO`) and update that line `locals().update(XXX)` to use that config.
3. Run the code in the first header section (Imports, Config and Setup).
4. Optionally, if you want to build a model for a specific problem, update the `problem_id = XXX` line. To see a list of possible problems, run the last cell.
5. Run the next header block of code (Build the Models and Save to the DB). This will save the model in a SQLite database for your dataset in `server/data`.
6. Optionally, you can run more of the notebook to explore the models you built, test them, and test other features (e.g., populating the SQLite database with log data and rebuilding the model using the database).


#### To build the model for many problems
1. Open the `preprocess/build.ipynb` file.
2. Select the config for the dataset you want to use (e.g., `config_CWO`) and update that line `locals().update(XXX)` to use that config.
3. Optionally, if you want to build a model for a subset of problems, update the `problem_ids = XXX` line. To see a list of possible problems, run the last cell.
4. Run all code in the script. This will save the models for each problem in a SQLite database for your dataset in `server/data`.

## Serving Feedback
This code is found in the server folder.
1. Update ``main.py`` to set the `SYSTEM_ID` variable to your system (e.g., `PCRS`, `iSnap`, `CWO`, `BlockPy`).
2. Run ``main.py``. It should start a server on port 5000.
3. If the server fails to start, make sure you're running it from the correct directory (the server directory).

### Building a Model Using a Custom Dataset + HTTP Post

If your dataset is not in ProgSnap2 format, or you do not have prior data, you can still use SimpleAIF. You can use the following steps to populate a new ProgSnap2 database and build the model, either as students submit their work, and/or with seed data you already have available.

1) Change the `SYSTEM_ID` constant in main.py to your system name.
2) Run `main.py` to start the server (see instructions above).
3) Add relevant data, as described below.

The `preprocess/build_one.ipynb` has examples of adding this data programmatically under the "Test populating a Dataset using the SimpleAIF Server" heading.

#### Starter Code

If you have starter code for some problems (i.e., students are given a method definition, comments, variables, etc. to start with), you should add this to the database. This will allow the model to ignore any starter code when computing student progress.

Send an HTTP-POST request to `http://127.0.0.1:5000/X-SetStarterCode/` with the following JSON in the post body:
* `ProblemID`: The problem ID (e.g., `32` or `sum_of_three`).
* `StarterCode`: The starter code for the problem (e.g., `def foo():\n\treturn 0`).

For example
```
{
    "ProblemID": "32",
    "StarterCode": "def foo():\n\treturn 0"
}
```

#### Student Attempts at a Problem

SimpleAIF is a data-driven model, and it requires some data from prior students to provide feedback. Ideally, this data is available for some or all problems beforehand (even if generated by an instructor), but if not it can be added at runtime.

Either way, send an HTTP-POST request to `http://127.0.0.1:5000/XXX/`, where XXX is one of the following ProgSnap2 EventTypes (they will have the same result):
* `Submit`
* `FileEdit`
* `Run.Program`

The request should at a minimum have the following JSON in the post body:
* `ProblemID`: The problem ID (e.g., `32` or `sum_of_three`).
* `SubjectID`: The user ID (e.g., `123` or `student_1`). **Note** that this ID will be stored in the local database, so if desired you can hash/encrypt it before sending it to the server. Ideally, SubjectIDs should remain consistent across problems, though this is not strictly necessary for SimpleAIF.
* `CodeState`: The student's current code at the time of the event (e.g., `def foo():\n\treturn 0`).
* `Score`: The score for the student's current code, ranging from 0-1, where 1 indicates fully correct code. This can be assessed automatically (e.g., by test cases) or manually if using previously collected data.
* `ShouldLog`: This must be set to `true` in order for SimpleAIF to record the event. It can be set to false (or omitted) if you simple wany to receive feedback without logging student work to the database to improve the model.

The request can also include the following, though they are not currently used by SimpleAIF:
* `AssignmentID`: A unique ID for the assignment that this problem belongs to (e.g., `hw1` or `lab2`).
* `ClientTimestamp`: The time of the event according to the client in ISO format (e.g., `2021-11-08T15:00:00Z`).
* `ServerTimestamp`: The time of the event according to the server in ISO format (e.g., `2021-11-08T15:00:00Z`).

For example, the JSON request might look like:
```
{
    "ProblemID": "8",
    "SubjectID": "Student01",
    "CodeState": "def collect_underpreforme",
    "Score": 0
    "ShouldLog": true,
    "AssignmentID": "Assignment01",
    "ClientTimestamp": "2023-10-20T19:14:29.692Z",
}
```

Note that currently SimpleAIF will build a feedback model for a given problem when it has at least `MIN_CORRECT_COUNT_FOR_FEEDBACK` correct student responses for that problem. It will subsequently recompile the models if it receives an additional `COMPILE_INCREMENT` correct responses. These values are set in `main.py`.

For example, if `MIN_CORRECT_COUNT_FOR_FEEDBACK` is 10 and `COMPILE_INCREMENT` is 5, SimpleAIF will build a model after 10 correct responses, and then rebuild it after 15, 20, 25, etc. correct responses.

You can also rebuild the model manually, as shown in `build_one.ipynb`.
