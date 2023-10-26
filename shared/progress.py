import numpy as np
from scipy.sparse import csr_matrix
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted
from sklearn.utils.multiclass import unique_labels
from sklearn.metrics import euclidean_distances
import warnings

class ProgressEstimator(BaseEstimator):

    def __init__(self, min_feature_proportion = 0.5, max_score_percentile = 0.25,
                 starter_code = None, vectorizer = None, focus_lines = None):
        self.min_feature_proportion = min_feature_proportion
        self.max_score_percentile = max_score_percentile
        self.vectorizer = vectorizer
        self.starter_code = starter_code
        self.focus_lines = focus_lines

        if starter_code is not None:
            if vectorizer is None:
                raise ValueError("If starter_code is provided, vectorizer must also be provided")

    def should_focus(self, name):
        for line in self.focus_lines:
            # TODO: This is very naive: improve
            if line in name or name in line:
                return True
        return False

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
        # if self.starter_code is not None:
        #     # Remove features that are present in the starter code
        #     # Another approach would be to subtrace the vectors, but I think this is likely
        #     # simpler and more interpretable
        #     self.useful_feature_indices = self.useful_feature_indices & (self.starter_code_means == 0)
        #     print(f"Went from {n_features} to {self.useful_feature_indices.mean()} features")

        if self.focus_lines is not None:
            feature_names = self.vectorizer.get_feature_names_out()
            focused_features = np.array([self.should_focus(name) for name in feature_names])
            self.useful_feature_indices = self.useful_feature_indices & focused_features
            print(f"Went from {n_features} to {self.useful_feature_indices.mean()} features")



        # Calculate the mean of each feature in the training data, but subtract the starter code
        self.mean_features = X_train.mean(axis=0) - self.starter_code_means
        # Remove features that are equally or less common in the training data than in the starter code
        self.useful_feature_indices = self.useful_feature_indices & (self.mean_features > 0)
        # print(f"Went from {n_features} to {self.useful_feature_indices.mean()} features")

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
        if not isinstance(X, np.ndarray):
            raise ValueError(f"X must be a numpy array or a scipy sparse matrix, not {type(X)}")
        return X


    def _progress_score_single(self, features):
        # Subtract the starting feature values and divide by the average
        completion = (features[self.useful_feature_indices] - self.starter_code_means[self.useful_feature_indices]) / \
            self.mean_features[self.useful_feature_indices]
        completion = np.clip(completion, 0, 1)
        return completion.mean()

    def _progress_score(self, X):
        return np.apply_along_axis(lambda x: self._progress_score_single(x), 1, X)

    def predict_proba(self, X):
        # Check if fit has been called
        # Buggy for some reason...
        # check_is_fitted(self)

        X = self.ensure_is_np_array(X)

        scores = self._progress_score(X)
        scaled =  (scores - self.min_score) / (self.max_score - self.min_score)
        return scaled.clip(0, 1)

    def predict(self, X):
        return self.predict_proba(X) > 0.5
