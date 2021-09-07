"""
Stub abstract class implementations.
"""
from typing import Hashable, Sequence, Tuple, Iterator, Dict, Any, Iterable, Union, Mapping, Set

from numpy import ndarray
import numpy as np
from smqtk_indexing import NearestNeighborsIndex
from smqtk_dataprovider import DataElement
from smqtk_descriptors import DescriptorGenerator, DescriptorSet, DescriptorElement
from smqtk_relevancy import RankRelevancyWithFeedback
from smqtk_classifier import ClassifyDescriptorSupervised
from smqtk_classifier.interfaces.classification_element import (
    ClassificationElement,
    CLASSIFICATION_DICT_T
)

ARRAY_ITER_T = Union[np.ndarray, Iterable[np.ndarray]]
STUB_MODULE_PATH = __name__


class StubDescriptorSet (DescriptorSet):
    @classmethod
    def is_usable(cls) -> bool:
        return True

    def add_many_descriptors(self, descriptors: Iterable[DescriptorElement]) -> None:
        pass

    def count(self) -> int:
        pass

    def iteritems(self) -> Iterator[Tuple[Hashable, DescriptorElement]]:
        pass

    def clear(self) -> None:
        pass

    def remove_descriptor(self, uuid: Hashable) -> None:
        pass

    def remove_many_descriptors(self, uuids: Hashable) -> None:
        pass

    def get_config(self) -> Dict[str, Any]:
        pass

    def get_many_descriptors(self, uuids: Hashable) -> Iterator[DescriptorElement]:
        pass

    def has_descriptor(self, uuid: Hashable) -> bool:
        pass

    def iterkeys(self) -> Iterator[Hashable]:
        pass

    def get_descriptor(self, uuid: Hashable) -> DescriptorElement:
        pass

    def iterdescriptors(self) -> Iterator[DescriptorElement]:
        pass

    def add_descriptor(self, descriptor: DescriptorElement) -> None:
        pass


class StubClassifier (ClassifyDescriptorSupervised):
    """
    Classifier stub for testing IqrService.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]:
        pass

    def get_labels(self) -> Sequence[Hashable]:
        pass

    def _classify_arrays(self, array_iter: ARRAY_ITER_T) -> Iterator[CLASSIFICATION_DICT_T]:
        pass

    def has_model(self) -> bool:
        # To allow training.
        return False

    def _train(self, class_examples: Mapping[Hashable, Iterable[DescriptorElement]]) -> None:
        pass


class StubDescrGenerator (DescriptorGenerator):
    """
    DescriptorGenerator stub for testing IqrService.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]:
        pass

    def valid_content_types(self) -> Set[str]:
        pass

    def _generate_arrays(self, data_iter: Iterable[DataElement]) -> Iterable[np.ndarray]:
        for _ in data_iter:
            yield None


class StubNearestNeighborIndex (NearestNeighborsIndex):
    """
    NearestNeighborIndex stub for testing IqrService.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]:
        pass

    def count(self) -> int:
        pass

    def _build_index(self, descriptors: Iterable[DescriptorElement]) -> None:
        pass

    def _update_index(self, descriptors: Iterable[DescriptorElement]) -> None:
        pass

    def _remove_from_index(self, uids: Hashable) -> None:
        pass

    def _nn(self, d: DescriptorElement, n: int = 1) -> Tuple[Tuple[DescriptorElement, ...], Tuple[float, ...]]:
        pass


class StubRankRelevancyWithFeedback (RankRelevancyWithFeedback):
    """
    RankRelevancyWithFeedback stub for testing IqrService.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]:
        pass

    def _rank_with_feedback(self,
                            pos: Sequence[ndarray],
                            neg: Sequence[ndarray],
                            pool: Sequence[ndarray],
                            pool_uids: Sequence[Hashable],
                            ) -> Tuple[Sequence[float], Sequence[Hashable]]:
        pass
