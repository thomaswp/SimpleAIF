import sys, os
# Needed, since this is run in a subfolder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, request, render_template_string
from flask_restful import Resource, Api
from flask_cors import CORS
import pickle
from sklearn.ensemble import AdaBoostClassifier
from xgboost import XGBClassifier
from shared.progress import ProgressEstimator
from shared.data import SQLiteLogger

app = Flask(__name__)
CORS(app)
# api = Api(app)

class FeedbackGenerator(Resource):

    @staticmethod
    def relative_path(path):
        basedir = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(basedir, path)

    @staticmethod
    def load_data_file(systemID, problemID, type):
        data_file = FeedbackGenerator.relative_path(f'data/{systemID}/{type}-{problemID}.pkl')
        if not os.path.isfile(data_file):
            return None
        return pickle.load(open(data_file, "rb"))

    def get_logger(self, path):
        if path in self.loggers:
            return self.loggers[path]
        logger = SQLiteLogger(path)
        logger.create_tables()
        self.loggers[path] = logger
        return logger

    def load_models_from_db(self, systemID, problemID):
        logger = self.get_logger(FeedbackGenerator.relative_path(f'data/{systemID}.db'))
        return logger.get_models(problemID)

    def load_models(self, systemID, problemID):
        if systemID in self.models:
            if problemID in self.models[systemID]:
                return self.models[systemID][problemID]
        else:
            self.models[systemID] = {}
        progress, model = self.load_data_file(systemID, problemID, 'model')
        progress = self.load_data_file(systemID, problemID, 'progress')
        if model is None or progress is None:
            self.models[systemID][problemID] = {}
        else:
            self.models[systemID][problemID] = {
                'model': model,
                'progress': progress
            }
        return self.models[systemID][problemID]

    def __init__(self) -> None:
        super().__init__()
        self.models = {}
        self.loggers = {}
        path = FeedbackGenerator.relative_path("templates/progress.html")
        file=open(path,"r")
        self.progress_tempalte = '\n'.join(file.readlines())
        file.close()

    def generate_feedback(self, systemID, problemID, code):
        progress_mode, classifier = self.load_models_from_db(systemID, problemID)
        # if 'model' not in models or 'progress' not in models:
        #     print(f"Model not found for {systemID}-{problemID}")
        #     return []
        score = classifier.predict_proba([code])[0,1]
        progress = progress_mode.predict_proba([code])[0]
        print(f"Progress: {progress}; Score: {score}")
        status = "In Progress"
        cutoff = 0.9
        if progress > cutoff:
            if score > 0.75:
                status = "Great!"
            elif score > 0.5:
                status = "Good"
            else:
                status = "Maybe Bugs"
        status_class = status.lower().replace(" ", "-").replace("!", "")
        html = render_template_string(self.progress_tempalte,
            progress=progress,
            score=score,
            max_score=cutoff,
            status=status,
            status_class=status_class,
            percent=max(0, min(progress/cutoff, 1)),
        )
        return [
            {
                "action": "ShowDiv",
                "data": {
                    "html": html,
                    "x-progress": float(progress),
                    "x-score": float(score),
                }
            }
        ]

fb_gen = FeedbackGenerator()

def generate_feedback_from_request():
    json = request.get_json()
    code = json["CodeState"]
    problemID = json["ProblemID"]
    # systemID = "iSnap"
    # systemID = "CWO"
    systemID = "PCRS"
    return fb_gen.generate_feedback(systemID, problemID, code)

@app.route('/', methods=['GET'])
def hello_world():
    return 'Hello, World!'

@app.route('/Submit/', methods=['POST'])
def submit():
    return generate_feedback_from_request()

@app.route('/FileEdit/', methods=['POST'])
def file_edit():
    return generate_feedback_from_request()

# api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)