import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted
from sklearn.utils.multiclass import unique_labels
from sklearn.metrics import euclidean_distances
import warnings
import shared.subgoals as subgoals


class ProgressEstimator(BaseEstimator):

    # TODO: The problem with this approach is that if the model is rebuilt
    # the subgoals aren't stored anywhere, so they're lost
    def __init__(self, min_feature_proportion = 0.5, max_score_percentile = 0.25,
                 starter_code = None, vectorizer = None, subgoal_data = None):
        self.min_feature_proportion = min_feature_proportion
        self.max_score_percentile = max_score_percentile
        self.vectorizer = vectorizer
        self.starter_code = starter_code
        self.subgoal_data = subgoal_data
        self.subgoal_features = {}

        if starter_code is not None:
            if vectorizer is None:
                raise ValueError("If starter_code is provided, vectorizer must also be provided")

    def calculate_subgoal_features(self, subgoal_index):
        feature_names = self.vectorizer.get_feature_names_out()
        return np.array(subgoals.are_ngrams_relevant_for_subgoal_index(self.subgoal_data, feature_names, subgoal_index))


    def fit(self, X, y = None):

        if self.starter_code is not None:
            starter_code_vector = self.vectorizer.transform([self.starter_code])
            starter_code_vector = self.ensure_is_np_array(starter_code_vector)
            self.starter_code_means = starter_code_vector.mean(axis=0)
        else:
            self.starter_code_means = np.zeros(X_train.shape[1])

        # Should be redundant with ensure below
        # X = check_array(X)

        X_train = self.ensure_is_np_array(X)

        perc_feat_present = (X_train > 0).mean(axis=0)
        self.useful_feature_indices = perc_feat_present > self.min_feature_proportion
        n_features = self.useful_feature_indices.mean()

        # Calculate the mean of each feature in the training data, but subtract the starter code
        self.mean_features = X_train.mean(axis=0) - self.starter_code_means
        # Remove features that are equally or less common in the training data than in the starter code
        self.useful_feature_indices = self.useful_feature_indices & (self.mean_features > 0)
        # print(f"Went from {n_features} to {self.useful_feature_indices.mean()} features")

        if self.subgoal_data is not None:
            try:
                header = self.subgoal_data["header"]
                for subgoal in header:
                    subgoal_name = subgoal["text"]
                    subgoal_index = subgoal["subgoalIndex"]
                    self.subgoal_features[subgoal_name] = self.calculate_subgoal_features(subgoal_index)
                    print(f"Subgoal [{subgoal_index}] {subgoal_name} has {self.subgoal_features[subgoal_name].sum()} / {self.useful_feature_indices.sum()} features")
            except Exception as e:
                print("Error calculating subgoal features")
                print(e)
                self.subgoal_features = {}

        train_scores = self._progress_score(X_train)
        self.min_score = 0 #train_scores.min()
        self.max_score = np.percentile(train_scores, self.max_score_percentile * 100)

        if self.min_score == self.max_score:
            warnings.warn(f"Warning: all training examples have the same progress score: {self.min_score}!")
            self.min_score = 0
            self.max_score = 1

        return self

    @staticmethod
    def ensure_is_np_array(X):
        if isinstance(X, csr_matrix):
            X = X.toarray()
        if isinstance(X, pd.Series):
            X = X.values
        if not isinstance(X, np.ndarray):
            raise ValueError(f"X must be a numpy array or a scipy sparse matrix, not {type(X)}")
        return X


    # TODO: Could almost certainly be made more efficient
    def _progress_score_single(self, features, useful_feature_indices, ignore_counts=False):
        # Subtract the starting feature values and divide by the average
        completion = (features[useful_feature_indices] - self.starter_code_means[useful_feature_indices]) / \
            self.mean_features[useful_feature_indices]
        if ignore_counts:
            completion = completion > 0
        completion = np.clip(completion, 0, 1)
        return completion.mean()

    def _progress_score(self, X, mask = None):
        useful_feature_indices = self.useful_feature_indices
        ignore_counts = mask is not None
        if mask is not None:
            useful_feature_indices = useful_feature_indices & mask
        return np.apply_along_axis(
            lambda x: self._progress_score_single(
                x, useful_feature_indices, ignore_counts
            ), 1, X)

    def predict_proba(self, X, subgoal_list = None):
        # Check if fit has been called
        # Buggy for some reason...
        # check_is_fitted(self)

        X = self.ensure_is_np_array(X)

        if subgoal_list is not None and isinstance(subgoal_list, list):
            for name, mask in self.subgoal_features.items():
                # TODO: Scale?
                subgoal_list.append({
                    "name": name,
                    "score": self._progress_score(X, mask)
                })

        scores = self._progress_score(X)
        scaled =  (scores - self.min_score) / (self.max_score - self.min_score)
        return scaled.clip(0, 1)

    def predict(self, X):
        return self.predict_proba(X) > 0.5
