import json
import math
import os

import cv2
from flask import Flask, send_from_directory, request
from werkzeug.utils import secure_filename

import predict
import utils

app = Flask(__name__, static_url_path='')

VIDEOS_BASE_PATH = '/Users/sudharkj/Developer/python/highlight-generator/videos'
IMAGES_BASE_PATH = '/Users/sudharkj/Developer/python/highlight-generator/images'
PREDICTIONS_BASE_PATH = '/Users/sudharkj/Developer/python/highlight-generator/predictions'

ALLOWED_EXTENSIONS = {'mov', 'mp4'}


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/images/<path:path>')
def send_image(path):
    return send_from_directory(IMAGES_BASE_PATH, path)


def generate_output_item(prediction, request_uuid, file_ext):
    return {
        'image_id': "/images/%s/%s.%s" % (request_uuid, prediction['image_id'], file_ext),
        'mean_score_prediction': prediction['mean_score_prediction']
    }


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/generate', methods=['POST'])
def generate_highlights():
    MAX_FRAMES = 100
    MIN_TIME_STAMP = 1
    frame_skip_count = 1
    file_ext = 'jpg'
    PREDICTIONS_LIMIT = 10
    BASE_MODEL = 'MobileNet'
    WEIGHTS_FILE = 'weights_mobilenet_aesthetic_0.07.hdf5'

    request_uid = utils.rand_gen()
    video_path = VIDEOS_BASE_PATH + '/' + request_uid
    images_path = IMAGES_BASE_PATH + '/' + request_uid
    predictions_path = PREDICTIONS_BASE_PATH + '/' + request_uid

    for dir_path in [video_path, images_path, predictions_path]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    print('Created required directories')

    file = request.files['file']
    if not file or not allowed_file(file.filename):
        print('No file uploaded')
        return json.dumps([], indent=2)

    video_name = secure_filename(file.filename)
    video_file_path = os.path.join(video_path, video_name)
    file.save(video_file_path)
    print('Saved file at %s' % video_file_path)

    video_cap = cv2.VideoCapture(video_file_path)
    fps = video_cap.get(cv2.CAP_PROP_FPS)
    frame_count = video_cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = math.ceil(frame_count / fps)
    time_skip = max(MIN_TIME_STAMP, math.ceil(duration / MAX_FRAMES))
    frame_skip_count = max(frame_skip_count, math.ceil(time_skip * fps))
    print('Sampling the video after %d frames' % frame_skip_count)

    success, image = video_cap.read()
    count = 1
    while success:
        if count % frame_skip_count == 0:
            cv2.imwrite("%s/frame_%d.%s" % (images_path, int(count / frame_skip_count), file_ext), image)
        success, image = video_cap.read()
        count += 1
    video_cap.release()
    print('Completed sampling and saving the frames')

    predictions_file = '%s/predicts.json' % predictions_path
    print('Running %s to predict the scores of the sampled frames' % BASE_MODEL)
    predictions = predict.score(BASE_MODEL, WEIGHTS_FILE, images_path, predictions_file)
    print('Completed prediction of frames')
    predictions = sorted(predictions, key=lambda k: k['mean_score_prediction'], reverse=True)
    predictions = predictions[:PREDICTIONS_LIMIT]
    print('Top %d Results:' % PREDICTIONS_LIMIT)
    print(json.dumps(predictions, indent=2))
    predictions = list(map(lambda prediction: generate_output_item(prediction, request_uid, file_ext),
                           predictions))
    print('Response:')
    print(json.dumps(predictions, indent=2))

    return json.dumps(predictions, indent=2)


if __name__ == '__main__':
    app.run()
