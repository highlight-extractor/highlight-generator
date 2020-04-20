import os
import glob

from nima import utils
from nima.data_generator import TestDataGenerator
from nima.model_builder import Nima


def image_file_to_json(img_path):
    img_dir = os.path.dirname(img_path)
    img_id = os.path.basename(img_path).split('.')[0]

    return img_dir, [{'image_id': img_id}]


def image_dir_to_json(img_dir, img_type='jpg'):
    img_paths = glob.glob(os.path.join(img_dir, '*.' + img_type))

    samples = []
    for img_path in img_paths:
        img_id = os.path.basename(img_path).split('.')[0]
        samples.append({'image_id': img_id})

    return samples


def predict(model, data_generator, is_verbose=0):
    # enabling multi processing is throwing GeneratorDataset iterator error in 2.1
    # fixing it by setting workers=1 and use_multiprocessing=False
    # ref: https://github.com/tensorflow/tensorflow/issues/37515
    return model.predict(
        data_generator,
        workers=1,
        use_multiprocessing=False,
        verbose=is_verbose
    )


def score(base_model_name, weights_file, image_source, predictions_file=None, img_type='jpg', is_verbose=0):
    image_dir = image_source
    samples = image_dir_to_json(image_dir, img_type=img_type)

    # build model and load weights
    nima = Nima(base_model_name, weights=None)
    nima.build()
    nima.nima_model.load_weights(weights_file)
    # print(nima.nima_model.summary())

    # initialize data generator
    # use only 1 as batch_size to support lower gpus
    data_generator = TestDataGenerator(samples, image_dir, 1, 10, nima.preprocessing_function(),
                                       img_format=img_type)

    # get predictions
    predictions = predict(nima.nima_model, data_generator, is_verbose)

    # calc mean scores and add to samples
    for i, sample in enumerate(samples):
        sample['mean_score_prediction'] = utils.calc_mean_score(predictions[i])

    if predictions_file is not None:
        utils.save_json(samples, predictions_file)

    return samples
