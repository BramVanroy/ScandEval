'''Sentiment evaluation of a language model on the NoReC dataset'''

from datasets import Dataset
from typing import Tuple
import logging

from .abstract import TextClassificationBenchmark
from ..utils import doc_inherit
from ..datasets import load_dataset


logger = logging.getLogger(__name__)


class NoReCBenchmark(TextClassificationBenchmark):
    '''Benchmark of language models on the NoReC dataset.

    Args:
        cache_dir (str, optional):
            Where the downloaded models will be stored. Defaults to
            '.benchmark_models'.
        evaluate_train (bool, optional):
            Whether the models should be evaluated on the training scores.
            Defaults to False.
        verbose (bool, optional):
            Whether to print additional output during evaluation. Defaults to
            False.

    Attributes:
        name (str): The name of the dataset.
        task (str): The type of task to be benchmarked.
        metric_names (dict): The names of the metrics.
        id2label (dict or None): A dictionary converting indices to labels.
        label2id (dict or None): A dictionary converting labels to indices.
        num_labels (int or None): The number of labels in the dataset.
        label_synonyms (list of lists of str): Synonyms of the dataset labels.
        evaluate_train (bool): Whether the training set should be evaluated.
        cache_dir (str): Directory where models are cached.
        two_labels (bool): Whether two labels should be predicted.
        split_point (int or None): Splitting point of `id2label` into labels.
        verbose (bool): Whether to print additional output.
    '''
    def __init__(self,
                 cache_dir: str = '.benchmark_models',
                 evaluate_train: bool = False,
                 verbose: bool = False):
        id2label = ['negative', 'neutral', 'positive']
        label_synonyms = [
            ['LABEL_0', 'negativ', 'neikvætt', 'Negative', id2label[0]],
            ['LABEL_1', 'nøytral', 'hlutlaus', 'Neutral', id2label[1]],
            ['LABEL_2', 'positiv', 'jákvætt', 'Positive', id2label[2]]
        ]
        super().__init__(name='norec',
                         id2label=id2label,
                         label_synonyms=label_synonyms,
                         cache_dir=cache_dir,
                         evaluate_train=evaluate_train,
                         verbose=verbose)

    @doc_inherit
    def _load_data(self) -> Tuple[Dataset, Dataset]:
        X_train, X_test, y_train, y_test = load_dataset(self.short_name)
        train_dict = dict(doc=X_train['text'],
                          orig_label=y_train['label'])
        test_dict = dict(doc=X_test['text'],
                         orig_label=y_test['label'])
        train = Dataset.from_dict(train_dict)
        test = Dataset.from_dict(test_dict)
        return train, test
