import numpy as np
from scipy.sparse import csr_matrix
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted
from sklearn.utils.multiclass import unique_labels
from sklearn.metrics import euclidean_distances
import warnings

class ProgressEstimator(BaseEstimator):

    def __init__(self, min_feature_proportion = 0.5, max_score_percentile = 0.25):
        self.min_feature_proportion = min_feature_proportion
        self.max_score_percentile = max_score_percentile

    def fit(self, X, y = None):
        # Should be redundant with ensure below
        # X = check_array(X)

        X_train = self.ensure_is_np_array(X)

        perc_feat_present = (X_train > 0).mean(axis=0)
        self.common_feature_indicies = perc_feat_present > self.min_feature_proportion
        self.mean_features = X_train.mean(axis=0)

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
        completion = features[self.common_feature_indicies] / self.mean_features[self.common_feature_indicies]
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
