import sys, os, datetime, traceback, random
import yaml
import time
# Needed, since this is run in a subfolder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, request, render_template_string, g
from flask_restful import Resource
from flask_cors import CORS
from shared.data import SQLiteLogger
from shared.database import SQLiteDataProvider, MultiDataProvider
from shared.progsnap import ProgSnap2Dataset
from shared.preprocess import SimpleAIFBuilder
from sklearn.dummy import DummyClassifier

app = Flask(__name__)
CORS(app)

def relative_path(path):
    basedir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(basedir, path)

config_path = relative_path("config.yaml")
if not os.path.exists(config_path):
    config_path = relative_path("config.default.yaml")
    print("Warning: Loading default config file! Createa a server/config.yaml file.")

config = yaml.safe_load(open(config_path))
print(config)

LOG_DATABASE = config["log_database"]

SHOW_SUBGOALS = config["show_subgoals"]
SHOW_STATUS = config["show_status"]

HELP_URL = config["help_url"]

BUILD_MODEL_DATABASE = config["build"]["model_database"]
BUILD_REBUILD_MODELS = config["build"]["rebuild_models"]
BUILD_MIN_CORRECT_COUNT_FOR_FEEDBACK = config["build"]["min_correct_count_for_feedback"]
BUILD_INCREMENT = config["build"]["increment"]
BUILD_LANG = config["build"]["language"]
# TODO: Add token pattern

CONDITIONS_ASSIGNMENT = config["conditions"]["assignment"]
CONDITIONS_INTERVENTION_PROBABILITY = config["conditions"]["intervention_probability"]
CONDITIONS_INVERSE_PROBLEMS = config["conditions"]["inverse_problems"]
CONDITIONS_MANUALLY_ASSIGNED_PROBLEMS = config["conditions"]["manually_assigned_problems"]

class FeedbackGenerator(Resource):

    def get_logger(self, system_id):
        if system_id in self.loggers:
            return self.loggers[system_id]
        logger = SQLiteLogger(relative_path(f'data/{system_id}.db'))
        logger.create_tables()
        self.loggers[system_id] = logger
        return logger

    def load_models_from_logger(self, problem_id, database):
        logger = self.get_logger(database)
        models = logger.get_models(problem_id)
        return models


    def load_models_from_db(self, problem_id):
        # If we don't have a model database, just use the log database
        if BUILD_MODEL_DATABASE is None:
            database = LOG_DATABASE
        # If we aren't rebuilding models, just use the model database
        elif not BUILD_REBUILD_MODELS:
            database = BUILD_MODEL_DATABASE
        # If we have a model database, but we're also rebuilding models...
        else:
            # First check if we've build this model from log data
            database = LOG_DATABASE
            models = self.load_models_from_logger(problem_id, database)
            # If we haven't, check the model database
            if models is None:
                database = BUILD_MODEL_DATABASE
        models = self.load_models_from_logger(problem_id, database)
        if models is None:
            print(f"Model not found for {problem_id} in {database}.db")
        return models

    def __init__(self) -> None:
        super().__init__()
        self.loggers = {}
        path = relative_path("templates/progress.html")
        file=open(path,"r")
        self.progress_tempalte = '\n'.join(file.readlines())
        file.close()

    def log(self, event_type, dict):
        logger = self.get_logger(LOG_DATABASE)
        if "NoLogging" in dict and dict["NoLogging"]:
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
        if not BUILD_REBUILD_MODELS:
            return
        problem_id = str(problem_id)
        logger = self.get_logger(LOG_DATABASE)
        if not logger.should_rebuild_model(problem_id, BUILD_MIN_CORRECT_COUNT_FOR_FEEDBACK, BUILD_INCREMENT):
            return
        try:
            logging_provider = SQLiteDataProvider(logger.db_path)
            if BUILD_MODEL_DATABASE is None:
                provider = logging_provider
            else:
                model_provider = SQLiteDataProvider(self.get_logger(BUILD_MODEL_DATABASE).db_path)
                provider = MultiDataProvider([logging_provider, model_provider])
            dataset = ProgSnap2Dataset(provider)
            builder = SimpleAIFBuilder(problem_id)
            builder.lang = BUILD_LANG
            # TODO: Add token pattern
            builder.build(dataset)
            progress_model = builder.get_trained_progress_model()
            if SHOW_STATUS:
                classifier = builder.get_trained_classifier()
            else:
                # If we aren't using the classifier, just leave it blank
                classifier = None
            correct_count = int(builder.X_train[builder.y_train].unique().size)
            logger.set_models(problem_id, progress_model, classifier, correct_count)
            print(f"Successfully rebuilt AIF for {problem_id} with {correct_count} unique correct submissions")
        except Exception as e:
            print(f"Failed AIF build for {problem_id}")
            traceback.print_exc()
            return

    def default_condition_is_intervention(self, id):
        state = str(LOG_DATABASE) + str(id)
        random.seed(state)
        is_intervention = random.random() < CONDITIONS_INTERVENTION_PROBABILITY
        # print(f"Random condition for {id}: {is_intervention}")
        return is_intervention


    def is_intervention_group(self, subject_id, problem_id):
        if problem_id in CONDITIONS_MANUALLY_ASSIGNED_PROBLEMS:
            is_intervention = CONDITIONS_MANUALLY_ASSIGNED_PROBLEMS[problem_id] == "intervention"
            # print (f"Manually assigned problem: {problem_id} is intervention: {is_intervention}")
            return is_intervention
        if CONDITIONS_ASSIGNMENT == "all_control":
            return False
        if CONDITIONS_ASSIGNMENT == "all_intervention":
            return True
        logger = self.get_logger(LOG_DATABASE)
        subject_condition = logger.get_or_set_subject_condition(
            subject_id, self.default_condition_is_intervention(subject_id))
        if problem_id in CONDITIONS_INVERSE_PROBLEMS:
            # print(f"Problem {problem_id} is inverse; switching {subject_condition} to {not subject_condition}")
            subject_condition = not subject_condition
        if CONDITIONS_ASSIGNMENT == "random_student":
            # print(f"Random student condition for {subject_id} on {problem_id}: {subject_condition}")
            return subject_condition
        else:
            print(f"Unknown condition assignment: {CONDITIONS_ASSIGNMENT}")
            return True

    def generate_feedback(self, problemID, code):
        models = self.load_models_from_db(problemID)
        if models is None:
            return []
        progress_model, classifier = models

        subgoal_list = None
        if SHOW_SUBGOALS:
            subgoal_list = []

        score = classifier.predict_proba([code])[0,1] if SHOW_STATUS and classifier is not None else 0
        progress = progress_model.predict_proba([code], subgoal_list=subgoal_list)[0]

        # print(f"Progress: {progress}; Score: {score}")
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
            subgoal_list=subgoal_list,
            show_subgoals=SHOW_SUBGOALS and len(subgoal_list) > 0,
            show_status=SHOW_STATUS,
            help_url=HELP_URL,
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
    if ("SubjectID" in json):
        subject_id = json["SubjectID"]
        if (not fb_gen.is_intervention_group(subject_id, problem_id)):
            return []
    else:
        print("Warning: No SubjectID provided")
    return fb_gen.generate_feedback(problem_id, code)

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
    logger = fb_gen.get_logger(LOG_DATABASE)
    logger.set_starter_code(problem_id, starter_code)
    return []

# Enable to test efficiency
# @app.before_request
# def before_request():
#     g.start = time.time()

# @app.after_request
# def after_request(response):
#     diff = time.time() - g.start
#     print (diff)
#     return response

# api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(port=5500, debug=True)