import sys, os, datetime, traceback, random
import yaml
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
from shared.database import SQLiteDataProvider
from shared.progsnap import ProgSnap2Dataset
from shared.preprocess import SimpleAIFBuilder

app = Flask(__name__)
CORS(app)
# api = Api(app)

def relative_path(path):
    basedir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(basedir, path)

config_path = relative_path("config.yaml")
if not os.path.exists(config_path):
    config_path = relative_path("config.default.yaml")
    print("Warning: Loading default config file! Createa a server/config.yaml file.")

config = yaml.safe_load(open(config_path))
print(config)

# TODO: I could make this support multiple systems, but I see no need to ATM
SYSTEM_ID = config["system_id"]

BUILD_MIN_CORRECT_COUNT_FOR_FEEDBACK = config["build"]["min_correct_count_for_feedback"]
BUILD_INCREMENT = config["build"]["increment"]

CONDITIONS_ASSIGNMENT = config["conditions"]["assignment"]
CONDITIONS_INTERVENTION_PROBABILITY = config["conditions"]["intervention_probability"]

class FeedbackGenerator(Resource):

    @staticmethod
    def load_data_file(systemID, problemID, type):
        data_file = relative_path(f'data/{systemID}/{type}-{problemID}.pkl')
        if not os.path.isfile(data_file):
            return None
        return pickle.load(open(data_file, "rb"))

    def get_logger(self, system_id):
        if system_id in self.loggers:
            return self.loggers[system_id]
        logger = SQLiteLogger(relative_path(f'data/{system_id}.db'))
        logger.create_tables()
        self.loggers[system_id] = logger
        return logger

    def load_models_from_db(self, system_id, problem_id):
        logger = self.get_logger(system_id)
        return logger.get_models(problem_id)

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
        path = relative_path("templates/progress.html")
        file=open(path,"r")
        self.progress_tempalte = '\n'.join(file.readlines())
        file.close()

    def log(self, event_type, dict):
        logger = self.get_logger(SYSTEM_ID)
        if "ShouldLog" not in dict or not dict["ShouldLog"]:
            return
        dict["ServerTimestamp"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        try:
            client_timestamp = dict["ClientTimestamp"]
            dict["ClientTimestamp"] = datetime.datetime.strptime(client_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%dT%H:%M:%S")
        except:
            pass
        logger.log_event(event_type, dict)
        if "ProblemID" in dict:
            self.rebuild_if_needed(dict["ProblemID"])

    def rebuild_if_needed(self, problem_id):
        problem_id = str(problem_id)
        logger = self.get_logger(SYSTEM_ID)
        if not logger.should_rebuild_model(problem_id, BUILD_MIN_CORRECT_COUNT_FOR_FEEDBACK, BUILD_INCREMENT):
            return
        try:
            dataset = ProgSnap2Dataset(SQLiteDataProvider(logger.db_path))
            builder = SimpleAIFBuilder(problem_id)
            builder.build(dataset)
            progress_model = builder.get_trained_progress_model()
            classifier = builder.get_trained_classifier()
            correct_count = int(builder.X_train[builder.y_train].unique().size)
            logger.set_models(problem_id, progress_model, classifier, correct_count)
            print(f"Successfully rebuilt AIF for {problem_id} with {correct_count} unique correct submissions")
        except Exception as e:
            print(f"Failed AIF build for {problem_id}")
            traceback.print_exc()
            return

    def default_condition_is_intervention(self, id):
        state = str(SYSTEM_ID) + str(id)
        random.seed(state)
        is_intervention = random.random() < CONDITIONS_INTERVENTION_PROBABILITY
        print(f"Random condition for {id}: {is_intervention}")
        return is_intervention


    def is_intervention_group(self, subject_id, problem_id):
        if CONDITIONS_ASSIGNMENT == "all_control":
            return False
        if CONDITIONS_ASSIGNMENT == "all_intervention":
            return True
        logger = self.get_logger(SYSTEM_ID)
        subject_condition = logger.get_or_set_subject_condition(
            subject_id, self.default_condition_is_intervention(subject_id))
        if CONDITIONS_ASSIGNMENT == "random_student":
            return subject_condition
        else:
            print(f"Unknown condition assignment: {CONDITIONS_ASSIGNMENT}")
            return True

    def generate_feedback(self, systemID, problemID, code):
        models = self.load_models_from_db(systemID, problemID)
        if models is None:
            print(f"Model not found for {systemID}-{problemID}")
            return []
        progress_model, classifier = models
        score = classifier.predict_proba([code])[0,1]
        progress = progress_model.predict_proba([code])[0]
        # TODO: Get the indices from somewhere
        subgoal_progresses = {index: progress_model.predict_proba([code], subgoal=index)[0] for index in range(4)}
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
            subgoal_progresses=subgoal_progresses,
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
    problem_id = json["ProblemID"]
    subject_id = json["SubjectID"]
    if (not fb_gen.is_intervention_group(subject_id, problem_id)):
        return []
    return fb_gen.generate_feedback(SYSTEM_ID, problem_id, code)

@app.route('/', methods=['GET'])
def hello_world():
    return 'Hello, World!'

@app.route('/Submit/', methods=['POST'])
def submit():
    fb_gen.log("Submit", request.get_json())
    return generate_feedback_from_request()

@app.route('/FileEdit/', methods=['POST'])
def file_edit():
    fb_gen.log("FileEdit", request.get_json())
    return generate_feedback_from_request()

@app.route('/Run.Program/', methods=['POST'])
def run_program():
    # start = time.time()
    fb_gen.log("Run.Program", request.get_json())
    # print (f"Run.Program: {time.time() - start}")
    return []

@app.route('/X-SetStarterCode/', methods=['POST'])
def set_starter_code():
    json = request.get_json()
    problem_id = json["ProblemID"]
    starter_code = json["StarterCode"]
    if starter_code is None or problem_id is None:
        return []
    logger = fb_gen.get_logger(SYSTEM_ID)
    logger.set_starter_code(problem_id, starter_code)
    return []

# api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)