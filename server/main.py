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

    model139 = None

    @staticmethod
    def load_data_file(name):
        basedir = os.path.abspath(os.path.dirname(__file__))
        data_file = os.path.join(basedir, f'data/{name}')
        return pickle.load(open(data_file, "rb"))

    def __init__(self) -> None:
        super().__init__()
        self.model139 = self.load_data_file('model-139.pkl')
        self.progress139 = self.load_data_file('progress-139.pkl')

    def get(self):
        return {'hello': 'world'}

    def post(self):
        json = request.get_json()
        print(json)
        code = json["CodeState"]
        score = self.model139.predict_proba([code])[0,1]
        progress = self.progress139.predict_proba([code])[0]
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