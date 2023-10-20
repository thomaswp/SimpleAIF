import sys

sys.path.append('../')

from shared.progsnap import PS2, EventType

config_PCRS = {
    "submit_columns": [EventType.Submit, EventType.RunProgram, 'Project.Submit'],
    "test_problem_id": 8,
    "problem_id_column": PS2.ProblemID,
    "code_column": PS2.Code,
    "data_folder": "data/PCRS/pcrs-f18/",
    "database": "../server/data/PCRS.db",
}

config_iSnap = {
    "submit_columns": [EventType.Submit, EventType.RunProgram, 'Project.Submit'],
    "test_problem_id": 'guessingGame2',
    "problem_id_column": PS2.AssignmentID,
    "code_column": 'Pseudocode',
    "data_folder": "data/iSnap/isnap-f22/",
    "database": "../server/data/iSnap.db",
}

config_CWO = {
    "submit_columns": [EventType.Submit, EventType.RunProgram, 'Project.Submit'],
    "test_problem_id": 13,
    "problem_id_column": PS2.ProblemID,
    "code_column": PS2.Code,
    "data_folder": "data/CWO/cwo-f19/",
    "database": "../server/data/CWO.db",
}