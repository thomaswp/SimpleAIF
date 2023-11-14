import sqlite3
import pickle
from shared.progsnap import PS2

def get(json_obj, key, default=None):
    if key in json_obj:
        return json_obj[key]
    else:
        return default

CODE_STATES_TABLE = 'CodeStates'
MAIN_TABLE = 'MainTable'
METADATA_TABLE = 'DatasetMetadata'
MODELS_TABLE = 'Models'
STARTER_CODE_TABLE = 'LinkProblem'
SUBJECT_TABLE = 'LinkSubject'

CODE_STATES_TABLE_COLUMNS = {
    'CodeStateID': 'INTEGER PRIMARY KEY',
    'Code': 'TEXT',
}

MAIN_TABLE_COLUMNS = {
    'EventID': 'INTEGER PRIMARY KEY',
    'SubjectID': 'TEXT',
    'ProblemID': 'TEXT',
    'AssignmentID': 'TEXT',
    'EventType': 'TEXT',
    'CodeStateID': 'INTEGER',
    'ClientTimestamp': 'TEXT',
    'ServerTimestamp': 'TEXT',
    'Score': 'REAL',
}

METADATA_TABLE_COLUMNS = {
    'Property': 'TEXT',
    'Value': 'TEXT',
}

MODELS_TABLE_COLUMNS = {
    'ModelID': 'INTEGER PRIMARY KEY AUTOINCREMENT',
    'ProblemID': 'TEXT UNIQUE',
    'ProgressModel': 'BLOB',
    'ClassifierModel': 'BLOB',
    'TrainingCount': 'INTEGER',
}

STARTER_CODE_TABLE_COLUMNS = {
    'ProblemID': 'TEXT PRIMARY KEY',
    'StarterCode': 'TEXT',
}

SUBJECT_TABLE_COLUMNS = {
    'SubjectID': 'TEXT PRIMARY KEY',
    'IsInterventionGroup': 'INTEGER',
}


class SQLiteLogger:

    def __init__(self, db_path):
        self.db_path = db_path
        self.create_tables()

    def __connect(self):
        # if self.conn is not None:
        #     return self.conn
        return sqlite3.connect(self.db_path)

    # TODO: this won't work with "with" statements
    # def begin_batch(self):
    #     self.conn = sqlite3.connect(self.db_path)
    #     self.cursor = self.conn.cursor()

    # def end_batch(self):
    #     self.conn.commit()
    #     self.conn.close()
    #     self.conn = None

    def __create_table(self, table_name, column_map):
        column_text = [f"`{k}` {v}" for k, v in column_map.items()]
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({','.join(column_text)})")
            conn.commit()

    def create_tables(self):
        self.__create_table(MAIN_TABLE, MAIN_TABLE_COLUMNS)
        self.__create_table(CODE_STATES_TABLE, CODE_STATES_TABLE_COLUMNS)
        self.__create_table(MODELS_TABLE, MODELS_TABLE_COLUMNS)
        # Not actually used, but helpful to have for clean loading
        self.__create_table(METADATA_TABLE, METADATA_TABLE_COLUMNS)
        self.__add_metadata()
        self.__create_table(STARTER_CODE_TABLE, STARTER_CODE_TABLE_COLUMNS)
        self.__create_table(SUBJECT_TABLE, SUBJECT_TABLE_COLUMNS)

    def __add_metadata(self):
        # get the number of rows in the metadata table
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM {METADATA_TABLE}")
            count = c.fetchone()[0]
            if count != 0:
                return

        metadata_map = {
            'Version': '8.0',
            'IsEventOrderingConsistent': 1,
            'EventOrderScope': 'Global',
            'EventOrderScopeColumns': '',
            'CodeStateRepresentation': 'Sqlite',
        }
        for key in metadata_map:
            self.__insert_map(METADATA_TABLE, {
                'Property': key,
                'Value': metadata_map[key]
            })

    def __insert_map(self, table_name, column_map):
        columns = '`' + '`,`'.join(column_map.keys()) + '`'
        values = ','.join(['?'] * len(column_map))
        id = None
        with self.__connect() as conn:
            c = conn.cursor()
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
            # print(query)
            c.execute(query, tuple(column_map.values()))
            id = c.lastrowid
            conn.commit()
        return id

    def clear_table(self, table_name):
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"DELETE FROM {table_name}")
            conn.commit()

    def __get_codestate_id(self, code_state):
        result = None
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"SELECT CodeStateID FROM {CODE_STATES_TABLE} WHERE Code = ?", (code_state,))
            result = c.fetchone()
        if result is None:
            return self.__insert_map(CODE_STATES_TABLE, {'Code': code_state})
        return result[0]

    def log_event(self, event_type, row_dict):
        code_state = get(row_dict, 'CodeState')
        code_state_id = self.__get_codestate_id(code_state)
        # print(code_state_id)
        main_table_map = {
            PS2.EventType: event_type,
            PS2.CodeStateID: code_state_id,
            # I haven't gotten order to work, but it's optional so ignoring
            # "Order": f"(SELECT IFNULL(MAX(`Order`), 0) + 1 FROM {MAIN_TABLE})"
        }
        for key in MAIN_TABLE_COLUMNS:
            if key in main_table_map:
                continue
            main_table_map[key] = get(row_dict, key)
        del main_table_map[PS2.EventID]
        # print (main_table_map)
        self.__insert_map(MAIN_TABLE, main_table_map)

    def get_starter_code(self, problem_id):
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"SELECT StarterCode FROM {STARTER_CODE_TABLE} WHERE ProblemID = ?", (problem_id,))
            result = c.fetchone()
            if result is None:
                return None
            return result[0]

    def set_starter_code(self, problem_id, starter_code):
        with self.__connect() as conn:
            c = conn.cursor()
            query = f"INSERT OR IGNORE INTO {STARTER_CODE_TABLE} (ProblemID, StarterCode) VALUES (?,NULL);"
            c.execute(query, (problem_id,))
            query = f"UPDATE {STARTER_CODE_TABLE} SET StarterCode = ? WHERE ProblemID = ?;"
            c.execute(query, (starter_code, problem_id))
            conn.commit()

    def __blobify(self, obj):
        pdata = pickle.dumps(obj)
        return sqlite3.Binary(pdata)

    def __deblobify(self, blob):
        return pickle.loads(blob)

    def set_models(self, problem_id, progress_model, classifier_model, training_correct_count):
         with self.__connect() as conn:
            c = conn.cursor()
            query = f"INSERT OR IGNORE INTO {MODELS_TABLE} (ProblemID, ProgressModel, ClassifierModel) VALUES (?,NULL,NULL);"
            c.execute(query, (problem_id,))
            query = f"UPDATE {MODELS_TABLE} SET ProgressModel = ?, ClassifierModel = ?, TrainingCount = ? WHERE ProblemID = ?;"
            c.execute(query, (self.__blobify(progress_model), self.__blobify(classifier_model), training_correct_count, problem_id))
            conn.commit()

    def should_rebuild_model(self, problem_id, min_correct, increment):
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"SELECT COUNT(DISTINCT({PS2.CodeStateID})) FROM {MAIN_TABLE} WHERE ProblemID = ? AND Score = 1", (problem_id,))
            result = c.fetchone()
            if result is None or result[0] < min_correct:
                return False
            current_correct_count = result[0]

            c.execute(f"SELECT TrainingCount FROM {MODELS_TABLE} WHERE ProblemID = ?", (problem_id,))
            result = c.fetchone()
            if result is None:
                return True
            return current_correct_count >= result[0] + increment

    def get_models(self, problem_id):
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"SELECT ProgressModel, ClassifierModel FROM {MODELS_TABLE} WHERE ProblemID = ?", (problem_id,))
            result = c.fetchone()
            if result is None:
                return None
            return self.__deblobify(result[0]), self.__deblobify(result[1])

    def get_or_set_subject_condition(self, subject_id, condition_to_set):
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"SELECT IsInterventionGroup FROM {SUBJECT_TABLE} WHERE SubjectID = ?", (subject_id,))
            result = c.fetchone()
            if result is None:
                self.__insert_map(SUBJECT_TABLE, {
                    'SubjectID': subject_id,
                    'IsInterventionGroup': condition_to_set,
                })
                return condition_to_set
            return result[0]
