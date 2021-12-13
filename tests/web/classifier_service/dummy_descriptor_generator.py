import numpy as np
from typing import Any, Dict, Set, Iterable

from smqtk_dataprovider import DataElement
from smqtk_descriptors import DescriptorGenerator


class DummyDescriptorGenerator (DescriptorGenerator):
    def get_config(self) -> Dict[str, Any]: ...

    @classmethod
    def is_usable(cls) -> bool:
        return True

    def valid_content_types(self) -> Set[str]:
        return {'text/plain'}

    def _generate_arrays(self, data_iter: Iterable[DataElement]) -> Iterable[np.ndarray]:
        for _ in data_iter:
            yield np.zeros((5,), np.float64)
