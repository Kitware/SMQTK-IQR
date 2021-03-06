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
    CLASSIFICATION_DICT_T
)

ARRAY_ITER_T = Union[np.ndarray, Iterable[np.ndarray]]
STUB_MODULE_PATH = __name__


class StubDescriptorSet (DescriptorSet):
    @classmethod
    def is_usable(cls) -> bool:
        return True

    def add_many_descriptors(self, descriptors: Iterable[DescriptorElement]) -> None: ...

    def count(self) -> int: ...

    def items(self) -> Iterator[Tuple[Hashable, DescriptorElement]]: ...

    def clear(self) -> None: ...

    def remove_descriptor(self, uuid: Hashable) -> None: ...

    def remove_many_descriptors(self, uuids: Hashable) -> None: ...

    def get_config(self) -> Dict[str, Any]: ...

    def get_many_descriptors(self, uuids: Hashable) -> Iterator[DescriptorElement]: ...

    def has_descriptor(self, uuid: Hashable) -> bool: ...

    def keys(self) -> Iterator[Hashable]: ...

    def get_descriptor(self, uuid: Hashable) -> DescriptorElement: ...

    def descriptors(self) -> Iterator[DescriptorElement]: ...

    def add_descriptor(self, descriptor: DescriptorElement) -> None: ...


class StubClassifier (ClassifyDescriptorSupervised):
    """
    Classifier stub for testing IqrService.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]: ...

    def get_labels(self) -> Sequence[Hashable]: ...

    def _classify_arrays(self, array_iter: ARRAY_ITER_T) -> Iterator[CLASSIFICATION_DICT_T]: ...

    def has_model(self) -> bool:
        # To allow training.
        return False

    def _train(self, class_examples: Mapping[Hashable, Iterable[DescriptorElement]]) -> None: ...


class StubDescrGenerator (DescriptorGenerator):
    """
    DescriptorGenerator stub for testing IqrService.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]: ...

    def valid_content_types(self) -> Set[str]: ...

    def _generate_arrays(self, data_iter: Iterable[DataElement]) -> Iterable[np.ndarray]: ...


class StubNearestNeighborIndex (NearestNeighborsIndex):
    """
    NearestNeighborIndex stub for testing IqrService.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]: ...

    def count(self) -> int: ...

    def _build_index(self, descriptors: Iterable[DescriptorElement]) -> None: ...

    def _update_index(self, descriptors: Iterable[DescriptorElement]) -> None: ...

    def _remove_from_index(self, uids: Hashable) -> None: ...

    def _nn(self, d: DescriptorElement, n: int = 1) -> Tuple[Tuple[DescriptorElement, ...], Tuple[float, ...]]: ...


class StubRankRelevancyWithFeedback (RankRelevancyWithFeedback):
    """
    RankRelevancyWithFeedback stub for testing IqrService.
    """

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def get_config(self) -> Dict[str, Any]: ...

    def _rank_with_feedback(self,
                            pos: Sequence[ndarray],
                            neg: Sequence[ndarray],
                            pool: Sequence[ndarray],
                            pool_uids: Sequence[Hashable],
                            ) -> Tuple[Sequence[float], Sequence[Hashable]]: ...
