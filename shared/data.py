import sqlite3

def get(json_obj, key, default=None):
    if key in json_obj:
        return json_obj[key]
    else:
        return default

CODE_STATES_TABLE = 'CodeStates'
MAIN_TABLE = 'MainTable'
METADATA_TABLE = 'DatasetMetadata'

CODE_STATES_TABLE_COLUMNS = {
    'CodeStateID': 'INTEGER PRIMARY KEY',
    'Code': 'TEXT',
}

MAIN_TABLE_COLUMNS = {
    'EventID': 'INTEGER PRIMARY KEY',
    'Order': 'INTEGER',
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

class SQLiteLogger:

    def __init__(self, db_path):
        self.db_path = db_path
        self.create_tables()

    def __connect(self):
        return sqlite3.connect(self.db_path)

    def __create_table(self, table_name, column_map):
        column_text = [f"`{k}` {v}" for k, v in column_map.items()]
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({','.join(column_text)})")
            conn.commit()

    def create_tables(self):
        self.__create_table(MAIN_TABLE, MAIN_TABLE_COLUMNS)
        self.__create_table(CODE_STATES_TABLE, CODE_STATES_TABLE_COLUMNS)
        # Not actually used, but helpful to have for clean loading
        self.__create_table(METADATA_TABLE, METADATA_TABLE_COLUMNS)
        self.__add_metadata()

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
        with self.__connect() as conn:
            c = conn.cursor()
            c.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({values})", tuple(column_map.values()))
            id = c.lastrowid
            conn.commit()
        return id

    def log_event(self, event_id, row_dict):
        code_state = get(row_dict, 'CodeState')
        code_state_id = self.__insert_map(CODE_STATES_TABLE, {'Code': code_state})
        main_table_map = {
            "EventID": event_id,
            "CodeStateID": code_state_id,
            # I haven't gotten order to work, but it also doesn't seem to matter
            "Order": f"(SELECT IFNULL(MAX(`Order`), 0) + 1 FROM {MAIN_TABLE})"
            # "Order": "0"
        }
        for key in MAIN_TABLE_COLUMNS:
            main_table_map[key] = get(row_dict, key)
        self.__insert_map(MAIN_TABLE, main_table_map)


