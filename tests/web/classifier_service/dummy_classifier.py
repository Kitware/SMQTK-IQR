import numpy as np
from typing import Any, Dict, Hashable, Iterator, Iterable, Mapping, Sequence, Union

from smqtk_classifier import (
    ClassifyDescriptorSupervised,
    ClassifyDescriptor
)
from smqtk_descriptors import DescriptorElement


STUB_CLASSIFIER_MOD_PATH = __name__


class DummyClassifier (ClassifyDescriptor):
    def get_config(self) -> Dict[str, Any]:
        """
        Return a JSON-compliant dictionary that could be passed to this
        class's ``from_config`` method to produce an instance with identical
        configuration.

        In the common case, this involves naming the keys of the dictionary
        based on the initialization argument names as if it were to be passed
        to the constructor via dictionary expansion.

        :return: JSON type compliant configuration dictionary.
        :rtype: dict

        """
        # No constructor, no config
        return {}

    @classmethod
    def is_usable(cls) -> bool:
        """
        Check whether this class is available for use.

        Since certain plugin implementations may require additional
        dependencies that may not yet be available on the system, this method
        should check for those dependencies and return a boolean saying if the
        implementation is usable.

        NOTES:
            - This should be a class method
            - When an implementation is deemed not usable, this should emit a
                warning detailing why the implementation is not available for
                use.

        :return: Boolean determination of whether this implementation is
                 usable.
        :rtype: bool

        """
        return True

    def _classify_arrays(self,
                         array_iter: Union[np.ndarray,
                                           Iterable[np.ndarray]]) -> Iterator[Dict[Hashable, float]]:
        for _ in array_iter:
            yield {
                'negative': 0.5,
                'positive': 0.5,
            }

    def get_labels(self) -> Sequence[Hashable]:
        """
        Get the sequence of class labels that this classifier can classify
        descriptors into. This includes the negative label.

        :return: Sequence of possible classifier labels.
        :rtype: collections.abc.Sequence[collections.abc.Hashable]

        :raises RuntimeError: No model loaded.

        """
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
