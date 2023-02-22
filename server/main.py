from flask import Flask, request
from flask_restful import Resource, Api
from flask_cors import CORS
import pickle
from sklearn.ensemble import AdaBoostClassifier
import os

app = Flask(__name__)
CORS(app)
api = Api(app)

class HelloWorld(Resource):

    model139 = None

    def __init__(self) -> None:
        super().__init__()
        basedir = os.path.abspath(os.path.dirname(__file__))
        data_file = os.path.join(basedir, 'data/model-139.pkl')
        self.model139 = pickle.load(open(data_file, "rb"))

    def get(self):
        return {'hello': 'world'}

    def post(self):
        json = request.get_json()
        print(json)
        code = json["CodeState"]
        score = self.model139.predict_proba([code])
        return [
            {
                "action": "ShowDiv",
                "data": {
                    "html": f"Score: {score}"
                }
            }
        ]

api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)