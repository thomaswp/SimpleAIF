import pandas as pd
import numpy as np
import json
import math
from enum import Enum
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import cross_val_predict
from xgboost import XGBClassifier
from imblearn.pipeline import Pipeline as IMBPipeline
from imblearn.over_sampling import RandomOverSampler

from shared.progsnap import ProgSnap2Dataset, PS2, EventType
from shared.progress import ProgressEstimator
from shared.python_preprocesser import PythonPreprocessor
from shared.sql_preprocessor import SQLPreprocessor

LANG_PYTHON = "python"
LANG_SQL = "sql"

class SimpleAIFBuilder:
    def __init__(self, problem_id, code_column=PS2.Code, problem_id_column=PS2.ProblemID):
        self.problem_id = problem_id
        self.code_column = code_column
        self.problem_id_column = problem_id_column

        self.submit_columns = [EventType.Submit, EventType.RunProgram, 'Project.Submit']
        self.ngram_range = (1,3)
        self.classifier_factory = lambda: XGBClassifier()
        self.subgoal_json = None
        self.subgoal_data = None
        self.lang = None
        self.token_pattern = r"[\w]+|[^\s]|[ ]{4}"

    def create_vectorizer(self):
        return CountVectorizer(
            lowercase=False,
            token_pattern=self.token_pattern,
            ngram_range=self.ngram_range
        )

    def _create_classification_pipeline(self):
        ros = RandomOverSampler(random_state=0)
        stages = [
            ("vectorizer", self.create_vectorizer()),
            ("oversample", ros),
            ("classifier", self.classifier_factory())
        ]

        if self.y_train.mean() == 1 or self.y_train.mean() == 0:
            del stages[1]
            # TODO: Add a naive classifier

        if self.lang == LANG_PYTHON:
            stages.insert(0, ("preprocessor", PythonPreprocessor()))
        elif self.lang == LANG_SQL:
            stages.insert(0, ("preprocessor", SQLPreprocessor()))

        return IMBPipeline(stages)

    def _get_assignment_row(self):
        assignment_table = self.ps2_dataset.load_link_table(self.problem_id_column.replace("ID", ""))
        if assignment_table is None:
            return None
        matching_rows = assignment_table[assignment_table[self.problem_id_column] == self.problem_id]
        if len(matching_rows) == 0:
            return None
        return matching_rows.iloc[0]

    def get_starter_code(self):
        starter_code = ''
        assignment_row = self._get_assignment_row()
        if assignment_row is not None:
            starter_code = assignment_row["Starter" + self.code_column]
        return starter_code

    def _create_progress_pipeline(self):
        starter_code = self.get_starter_code()

        preprocessor = None
        if self.lang == LANG_PYTHON:
            print ("Using python preprocessor")
            preprocessor = PythonPreprocessor()
            starter_code = PythonPreprocessor.remove_comments_and_docstring(starter_code)
        elif self.lang == LANG_SQL:
            print ("Using sql preprocessor")
            preprocessor = SQLPreprocessor()
            starter_code = SQLPreprocessor.remove_comments_and_to_lower(starter_code)
        elif self.lang is not None:
            print(f"Unknown language {self.lang}")

        vectorizer = self.create_vectorizer()
        stages = [
            ("vectorizer", vectorizer),
            ("classifier", ProgressEstimator(starter_code = starter_code, vectorizer = vectorizer, subgoal_data=self.subgoal_data))
        ]

        if preprocessor is not None:
            stages.insert(0, ("preprocessor", preprocessor))

        return Pipeline(stages)

    @staticmethod
    def get_submissions_table(data, submit_columns = [EventType.Submit, EventType.RunProgram, 'Project.Submit']):
        main_table = data.get_main_table()
        submissions = main_table[main_table[PS2.EventType].isin(submit_columns)]
        return submissions

    @staticmethod
    def get_code_table(data, submissions, problem_id_column, code_column):

        code_states = data.get_code_states_table()
        merged = pd.merge(
            submissions, code_states, on=PS2.CodeStateID
        )[[problem_id_column, PS2.Score, code_column]]
        # For both  models, we only want code with a specific score
        return merged[~merged[PS2.Score].isna()]

    def build(self, data: ProgSnap2Dataset):
        self.ps2_dataset = data
        submissions = SimpleAIFBuilder.get_submissions_table(data, self.submit_columns)
        self.mean_scores = submissions.groupby(self.problem_id_column).Score.mean()
        assignment_submissions = submissions[submissions[self.problem_id_column] == self.problem_id]
        assignment_code = SimpleAIFBuilder.get_code_table(data, assignment_submissions, self.problem_id_column, self.code_column)

        df = assignment_code.copy()
        # print(f"Found {len(df)} submissions for {self.problem_id}")
        df["Code"] = df[self.code_column]
        df["Correct"] = df["Score"] >= 1
        df = df[~df["Code"].isna()]

        self.X_train = df["Code"]
        self.y_train = df["Correct"]

        self.build_subgoals()

    def build_subgoals(self):
        assignment_row = self._get_assignment_row()
        if assignment_row is None:
            return
        subgoal_column = "Subgoals"
        if subgoal_column not in assignment_row:
            return
        try:
            subgoal_json =  assignment_row[subgoal_column]
            if subgoal_json is None or not isinstance(subgoal_json, str) or len(subgoal_json) == 0:
                return
            self.subgoal_json = subgoal_json
            # print(subgoal_json)
            self.subgoal_data = json.loads(subgoal_json)
        except Exception as e:
            print(e)
            return

    def get_feature_names(self, correct_only = False):
        vectorizer = self.create_vectorizer()
        vectorizer.fit(self.X_train if not correct_only else self.get_correct_submissions())
        return vectorizer.get_feature_names_out()

    def get_correct_submissions(self):
        return self.X_train[self.y_train].reset_index(drop=True)

    def get_incorrect_submissions(self):
        return self.X_train[~self.y_train].reset_index(drop=True)

    def get_vectorized_submissions(self):
        vectorizer = self.create_vectorizer()
        return vectorizer.fit_transform(self.X_train)

    def get_training_report(self):
        classification_pipeline = self.get_trained_classifier()
        y_pred = classification_pipeline.predict(self.X_train)

        return (
            classification_report(self.y_train, y_pred),
            confusion_matrix(self.y_train, y_pred)
        )

    def get_cv_report(self, cv=10):
        classification_pipeline = self._create_classification_pipeline()
        y_pred = cross_val_predict(classification_pipeline, self.X_train, self.y_train, cv=cv)
        return (
            classification_report(self.y_train, y_pred),
            confusion_matrix(self.y_train, y_pred)
        )

    def get_minimum_solution_cover(self):
        progress_model_pipeline = self.get_trained_progress_model()
        progress_model = progress_model_pipeline.named_steps["classifier"]
        useful_indices = np.array(progress_model.useful_feature_indices)
        vectorizer = progress_model_pipeline.named_steps["vectorizer"]
        preprocessor = progress_model_pipeline.named_steps["preprocessor"] if "preprocessor" in progress_model_pipeline.named_steps else None
        correct_submissions = self.get_correct_submissions()
        if preprocessor is not None:
            correct_submissions = preprocessor.transform(correct_submissions)
        transformed_solutions = vectorizer.transform(correct_submissions)
        transformed_solutions = transformed_solutions.toarray()
        solution_cover = []
        solution_cover_indices = []
        # Get the solution that has the max number of useful features
        while useful_indices.sum() > 0:
            solution_coverages = np.apply_along_axis(lambda x: (x[useful_indices] > 0).sum(), axis=1, arr=transformed_solutions)
            solution_coverages[solution_cover_indices] = -1
            if solution_coverages.max() <= 0:
                break
            max_index = solution_coverages.argmax()
            solution_cover.append(correct_submissions[max_index])
            solution_cover_indices.append(max_index)
            # Remove the features covered by this solution
            useful_indices = useful_indices & (transformed_solutions[max_index] == 0)

        return solution_cover



    def get_trained_classifier(self):
        classification_pipeline = self._create_classification_pipeline()
        return classification_pipeline.fit(
            self.X_train, self.y_train
        )

    def get_trained_progress_model(self):
        progress_pipeline = self._create_progress_pipeline()
        return progress_pipeline.fit(self.get_correct_submissions())
