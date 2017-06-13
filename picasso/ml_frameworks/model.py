import warnings
from operator import itemgetter
import importlib


class BaseModel:
    """Model class interface.

    All ML frameworks should derive from this class for the purposes of
    the visualization.  This class loads saved files generated by various
    ML frameworks and allows us to extract the graph topology, weights, etc.

    """

    def __init__(self,
                 top_probs=5,
                 **kwargs):
        """Attempt to load utilities

        The class constructor attempts to import a preprocessor, postprocessor,
        and probability decoder if a path is supplied.

        Args:
            top_probs (int): Number of classes to display per result. For
                instance, VGG16 has 1000 classes, we don't want to display a
                visualization for every single possibility.  Defaults to 5.
            **kwargs: Arbitrary keyword arguments, useful for passing specific
                settings to derived classes.


        """
        self.top_probs = top_probs
        if kwargs:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def load(self, data_dir, **kwargs):
        """Load the model in the desired framework

        Given a directory where model data (weights and graph
        structure), should be able to restore the model locally to the point
        where it can be evaluated.

        Args:
            data_dir (:obj:`str`): full path to directory containing
                weight and graph data
            **kwargs: Arbitrary keyword arguments, useful for passing specific
                settings to derived classes.

        """
        raise NotImplementedError

    def _predict(self, targets):
        """Evaluate new examples and return class probablilites

        Given an iterable of examples or numpy array where the first
        dimension is the number of example, return a n_examples x
        n_classes array of class predictions

        Args:
            targets: iterable of arrays suitable for input into graph

        Returns:
            array of class probabilities

        """
        raise NotImplementedError

    def predict(self, raw_targets):
        """Predict from raw data

        Takes an iterable of data in its raw format.  Passes to the
        preprocessor and then the child class _predict.

        Args:
            raw_targets (:obj:`list` of :obj:`PIL.Image`): the images
                to be processed

        Returns:
            array of class probabilities

        """
        return self._predict(self.preprocess(raw_targets))

    def preprocess(self, raw_targets):
        """Preprocess raw input for evaluation by model

        Usually, input will need some preprocessing before submission
        to a computation graph.  For instance, the raw image may need
        to converted to a numpy array of appropriate dimension

        Args:
            raw_targets (:obj:`list` of :obj:`PIL.Image`): the images
                to be processed

        Returns:
            iterable of arrays of the correct shape for input into graph

        """
        try:
            return getattr(self.preprocessor,
                           self.preprocessor_name)(raw_targets)
        except AttributeError:
            warnings.warn('Evaluating without preprocessor')
            return raw_targets

    def postprocess(self, output_arr):
        """Postprocess prediction results back into images

        Sometimes it's useful to display an intermediate computation
        as image.  This is model-dependent.

        Args:
            output_arr (iterable of arrays): any array with the
                same total number of entries an input array

        Returns:
            iterable of arrays in original image shape

        """

        try:
            return getattr(self.postprocessor,
                           self.postprocessor_name)(output_arr)
        except AttributeError:
            warnings.warn('Evaluating without postprocessor')
            return output_arr

    def decode_prob(self, output_arr):
        """Label class probabilites with class names

        Args:
            output_arr (array): class probabilities

        Returns:
            result list of  dict in the format [{'index': class_index, 'name':
                class_name, 'prob': class_probability}, ...]

        """

        try:
            return getattr(self.prob_decoder,
                           self.prob_decoder_name)(output_arr,
                                                   top=self.top_probs)
        except AttributeError:
            warnings.warn('Evaluating without class decoder')
            results = []
            for row in output_arr:
                entries = []
                for i, prob in enumerate(row):
                    entries.append({'index': i,
                                    'name': str(i),
                                    'prob': prob})

                entries = sorted(entries,
                                 key=itemgetter('prob'),
                                 reverse=True)[:self.top_probs]

                for entry in entries:
                    entry['prob'] = '{:.3f}'.format(entry['prob'])
                results.append(entries)
            return results


def generate_model(model_cls_path, model_cls_name, **kwargs):
    """Get an instance of the described model.

    Args:
        model_cls_path: Path to the module in which the model class
            is defined.
        model_cls_name: Name of the model class.
        data_dir: Directory containing the graph and weights.
        kwargs: Arbitrary keyword arguments passed to the model's
            constructor.

    Returns:
        An instance of :class:`.ml_frameworks.model.BaseModel` or subclass

    """
    spec = importlib.util.spec_from_file_location('active_model',
                                                  model_cls_path)
    model_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model_module)
    model_cls = getattr(model_module, model_cls_name)
    model = model_cls(**kwargs)
    if not isinstance(model, BaseModel):
        warnings.warn("Loaded model '%s' at '%s' is not an instance of %r"
                      % (model_cls_name, model_cls_path, BaseModel))
    return model
