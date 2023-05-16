from flask import Flask, request
from flask_restful import Resource, Api
from flask_cors import CORS
import pickle
from sklearn.ensemble import AdaBoostClassifier
import os
from xgboost import XGBClassifier
import progress

app = Flask(__name__)
CORS(app)
# api = Api(app)

class FeedbackGenerator(Resource):

    @staticmethod
    def load_data_file(systemID, problemID, type):
        basedir = os.path.abspath(os.path.dirname(__file__))
        data_file = os.path.join(basedir, f'data/{systemID}/{type}-{problemID}.pkl')
        if not os.path.isfile(data_file):
            return None
        return pickle.load(open(data_file, "rb"))

    def load_models(self, systemID, problemID):
        if systemID in self.models:
            if problemID in self.models[systemID]:
                return self.models[systemID][problemID]
        else:
            self.models[systemID] = {}
        model = self.load_data_file(systemID, problemID, 'model')
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

    def generate_feedback(self, systemID, problemID, code):
        models = self.load_models(systemID, problemID)
        if 'model' not in models or 'progress' not in models:
            return []
        score = models['model'].predict_proba([code])[0,1]
        progress = models['progress'].predict_proba([code])[0]
        return [
            {
                "action": "ShowDiv",
                "data": {
                    "html": f"""
<label for="progress">Progress:</label>
<progress id="progress" value="{progress * 100}" max="100"></progress> <br/>
<label for="score">Score:</label>
<progress id="score" value="{score * 100}" max="100"></progress> <br/>
Progress: {progress}; Score: {score}
"""
                }
            }
        ]

fb_gen = FeedbackGenerator()

def generate_feedback_from_request():
    json = request.get_json()
    code = json["CodeState"]
    problemID = json["ProblemID"]
    systemID = "CWO"
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