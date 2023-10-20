from abc import ABC, abstractmethod
import os
from os import path
import pandas as pd
from pandas import DataFrame
from shared.progsnap import PS2, EventType

class PS2DataProvider(ABC):

    @abstractmethod
    def get_main_table(self) -> DataFrame:
        pass

    @abstractmethod
    def get_code_states_table(self) -> DataFrame:
        pass

    @abstractmethod
    def get_link_table(self, table_name) -> DataFrame:
        pass

    @abstractmethod
    def get_metadata_table(self) -> DataFrame:
        pass

    @abstractmethod
    def get_link_table_names(self) -> list[str]:
        pass

class CSVDataProvider(PS2DataProvider):
    MAIN_TABLE_FILE = 'MainTable.csv'
    METADATA_TABLE_FILE = 'DatasetMetadata.csv'
    LINK_TABLE_DIR = 'LinkTables'
    CODE_STATES_DIR = 'CodeStates'
    CODE_STATES_TABLE_FILE = os.path.join(CODE_STATES_DIR, 'CodeStates.csv')

    def __init__(self, directory):
        self.directory = directory
        self.main_table = None
        self.metadata_table = None
        self.code_states_table = None

    def path(self, local_path) -> str:
        return path.join(self.directory, local_path)

    def get_main_table(self):
        return pd.read_csv(self.path(CSVDataProvider.MAIN_TABLE_FILE))

    def get_code_states_table(self):
        return pd.read_csv(self.path(CSVDataProvider.CODE_STATES_TABLE_FILE))

    def get_metadata_table(self):
        return pd.read_csv(self.path(CSVDataProvider.METADATA_TABLE_FILE))

    def __link_table_path(self):
        return self.path(CSVDataProvider.LINK_TABLE_DIR)

    def get_link_table_names(self):
        path = self.__link_table_path()
        dirs = os.listdir(path)
        return [f for f in dirs if os.path.isfile(os.path.join(path, f)) and f.endswith('.csv')]

    def get_link_table(self, table_name):
        if not table_name.endswith('.csv'):
            table_name += '.csv'
        table_path = path.join(self.__link_table_path(), table_name)
        if not path.exists(table_path):
            return None
        return pd.read_csv(table_path)

    def save_subset(self, path, main_table_filterer, copy_link_tables=True):
        os.makedirs(os.path.join(path, CSVDataProvider.CODE_STATES_DIR), exist_ok=True)
        main_table = main_table_filterer(self.get_main_table())
        main_table.to_csv(os.path.join(path, CSVDataProvider.MAIN_TABLE_FILE), index=False)
        code_state_ids = main_table[PS2.CodeStateID].unique()
        code_states = self.get_code_states_table()
        code_states = code_states[code_states[PS2.CodeStateID].isin(code_state_ids)]
        code_states.to_csv(os.path.join(path, CSVDataProvider.CODE_STATES_DIR, 'CodeStates.csv'), index=False)
        self.metadata_table.to_csv(os.path.join(path, CSVDataProvider.METADATA_TABLE_FILE), index=False)

        if not copy_link_tables:
            return

        os.makedirs(os.path.join(path, CSVDataProvider.LINK_TABLE_DIR), exist_ok=True)

        def indexify(x):
            return tuple(x) if len(x) > 1 else x[0]

        for link_table_name in self.list_link_tables():
            link_table = self.load_link_table(link_table_name)
            columns = [col for col in link_table.columns if col.endswith('ID') and col in main_table.columns]
            distinct_ids = main_table.groupby(columns).apply(lambda x: True)
            # TODO: Still need to test this with multi-ID link tables
            to_keep = [indexify(list(row)) in distinct_ids for index, row in link_table[columns].iterrows()]
            filtered_link_table = link_table[to_keep]
            filtered_link_table.to_csv(os.path.join(path, CSVDataProvider.LINK_TABLE_DIR, link_table_name), index=False)

import sqlite3

class SQLiteDataProvider(PS2DataProvider):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path
        self.main_table = "MainTable"
        self.code_states_table = "CodeStates"
        self.metadata_table = "DatasetMetadata"
        self.link_table_prefix = "Link"
        self.link_table_list_table = "LinkTable"
        self.__con = None

    def __connect(self):
        if self.__con is None:
            self.__con = sqlite3.connect(self.path)
        return self.__con

    def close(self):
        if self.__con is not None:
            self.__con.close()
            self.__con = None

    def get_main_table(self):
        return pd.read_sql_query(f"SELECT * FROM {self.main_table}", self.__connect())

    def get_code_states_table(self):
        return pd.read_sql_query(f"SELECT * FROM {self.code_states_table}", self.__connect())

    def get_metadata_table(self):
        return pd.read_sql_query(f"SELECT * FROM {self.metadata_table}", self.__connect())

    def get_link_table_names(self):
        tables = pd.read_sql_query(f"SELECT Name FROM {self.link_table_list_table}", self.__connect())
        return tables["Name"].to_list()

    def get_link_table(self, table_name):
        try:
            return pd.read_sql_query(f"SELECT * FROM {self.link_table_prefix}{table_name}", self.__connect())
        except:
            return None