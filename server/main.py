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
api = Api(app)

class HelloWorld(Resource):

    @staticmethod
    def load_data_file(systemID, assignmentID, type):
        basedir = os.path.abspath(os.path.dirname(__file__))
        data_file = os.path.join(basedir, f'data/{systemID}/{type}-{assignmentID}.pkl')
        return pickle.load(open(data_file, "rb"))

    def __init__(self) -> None:
        super().__init__()
        self.model139 = self.load_data_file('BlockPy', '139', 'model')
        self.progress139 = self.load_data_file('BlockPy', '139', 'progress')
        self.modelSquiral = self.load_data_file('iSnap', 'squiralHW', 'model')
        self.progressSquiral = self.load_data_file('iSnap', 'squiralHW', 'progress')

    def get(self):
        return {'hello': 'world'}

    def post(self):
        json = request.get_json()
        print(json)
        code = json["CodeState"]
        # score = self.model139.predict_proba([code])[0,1]
        # progress = self.progress139.predict_proba([code])[0]
        score = self.modelSquiral.predict_proba([code])[0,1]
        progress = self.progressSquiral.predict_proba([code])[0]
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

api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)