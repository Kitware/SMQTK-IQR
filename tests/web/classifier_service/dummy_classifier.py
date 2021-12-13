import numpy as np
from typing import Any, Dict, Hashable, Iterator, Iterable, Mapping, Sequence, Union

from smqtk_classifier import (
    ClassifyDescriptorSupervised,
    ClassifyDescriptor
)
from smqtk_descriptors import DescriptorElement


STUB_CLASSIFIER_MOD_PATH = __name__


class DummyClassifier (ClassifyDescriptor):
    def get_config(self) -> Dict[str, Any]: ...

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def _classify_arrays(
        self,
        array_iter: Union[np.ndarray, Iterable[np.ndarray]]
    ) -> Iterator[Dict[Hashable, float]]:
        for _ in array_iter:
            yield {
                'negative': 0.5,
                'positive': 0.5,
            }

    def get_labels(self) -> Sequence[Hashable]:
        return ['negative', 'positive']


class DummySupervisedClassifier (ClassifyDescriptorSupervised):
    """
    Supervise classifier stub implementation.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]: ...

    def has_model(self) -> bool: ...

    def _train(self, class_examples: Mapping[Any, Iterable[DescriptorElement]],
               **extra_params: Any) -> None: ...

    def get_labels(self) -> Sequence[Hashable]: ...

    def _classify_arrays(self, array_iter: Union[np.ndarray, Iterable[np.ndarray]]) \
        -> Iterator[Dict[Hashable, float]]: ...
