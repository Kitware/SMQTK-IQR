"""
Collection of higher level functions to perform operational tasks.

Some day, this module could have a companion module containing the CLI logic
for these functions instead of scripts in ``<source>/bin/scripts``.

"""
import collections
import logging
from typing import (
    Deque, Hashable, Set, Tuple, Generator, Iterable, Any, Optional
)

from smqtk_dataprovider import (
    DataElement
)
from smqtk_descriptors import (
    DescriptorElement, DescriptorGenerator, DescriptorSet
)
from smqtk_descriptors.descriptor_element_factory import DescriptorElementFactory


def compute_many_descriptors(data_elements: Iterable[DataElement],
                             descr_generator: DescriptorGenerator,
                             descr_factory: DescriptorElementFactory,
                             descr_set: DescriptorSet,
                             batch_size: Optional[int] = None,
                             overwrite: bool = False,
                             procs: Optional[int] = None,
                             **kwds: Any) -> Iterable[Tuple[DataElement,
                                                            DescriptorElement]]:
    """
    Compute descriptors for each data element, yielding
    (DataElement, DescriptorElement) tuple pairs in the order that they were
    input.

    *Note:* **This function currently only operated over images due to the
    specific data validity check/filter performed.*

    :param data_elements: Iterable of DataElement instances of files to
        work on.
    :type data_elements: collections.abc.Iterable[DataElement]

    :param descr_generator: DescriptorGenerator implementation instance
        to use to generate descriptor vectors.
    :type descr_generator: DescriptorGenerator

    :param descr_factory: DescriptorElement factory to use when producing
        descriptor vectors.
    :type descr_factory: DescriptorElementFactory

    :param descr_set: DescriptorSet instance to add generated descriptors
        to. When given a non-zero batch size, we add descriptors to the given
        set in batches of that size. When a batch size is not given, we add
        all generated descriptors to the set after they have been generated.
    :type descr_set: DescriptorSet

    :param batch_size: Optional number of elements to asynchronously compute
        at a time. This is useful when it is desired for this function to yield
        results before all descriptors have been computed, yet still take
        advantage of any batch asynchronous computation optimizations a
        particular DescriptorGenerator implementation may have. If this is 0 or
        None (false-evaluating), this function blocks until all descriptors
        have been generated.
    :type batch_size: None | int | long

    :param overwrite: If descriptors from a particular generator already exist
        for particular data, re-compute the descriptor for that data and set
        into the generated DescriptorElement.
    :type overwrite: bool

    :param procs: Deprecated parameter. Parallelism in batch computation is now
        controlled on a per implementation basis.
    :type procs: None | int

    :param kwds: Deprecated parameter. Extra keyword arguments are no longer
        passed down to the batch generation method on the descriptor generator.

    :return: Generator that yields (DataElement, DescriptorElement) for each
        data element given, in the order they were provided.
    :rtype: collections.abc.Iterable[(DataElement,
                                      DescriptorElement)]

    """
    log = logging.getLogger(__name__)

    # Capture of generated elements in order of generation
    de_deque: Deque[DataElement] = collections.deque()

    # Counts for logging
    total = [0]
    unique: Set[Hashable] = set()

    def iter_capture_elements() -> Generator:
        for d in data_elements:
            de_deque.append(d)
            yield d

    # TODO: Re-write this method to more simply tee the input data elem iter
    #       and yield with paired generated descriptors::
    #           data_iter1, data_iter2 = itertools.tee(data_elements, 2)
    #           descr_iter = descr_generator.generate_elements(
    #               data_iter1, descr_factory, overwrite
    #           )
    #           return zip(data_iter2, descr_iter)

    if batch_size:
        log.debug("Computing in batches of size %d", batch_size)

        def iterate_batch_results() -> Generator:
            descr_list_ = list(descr_generator.generate_elements(
                de_deque, descr_factory, overwrite
            ))
            total[0] += len(de_deque)
            unique.update(d.uuid() for d in descr_list_)
            log.debug("-- Processed %d so far (%d total data elements "
                      "input)", len(unique), total[0])
            log.debug("-- adding to set")
            descr_set.add_many_descriptors(descr_list_)
            log.debug("-- yielding generated descriptor elements")
            for data_, descr_ in zip(de_deque, descr_list_):
                yield data_, descr_
            de_deque.clear()

        batch_i = 0

        for _ in iter_capture_elements():
            # elements captured ``de_deque`` in iter_capture_elements

            if len(de_deque) == batch_size:
                batch_i += 1
                log.debug("Computing batch {}".format(batch_i))
                for data_e, descr_e in iterate_batch_results():
                    yield data_e, descr_e

        if len(de_deque):
            log.debug("Computing final batch of size %d",
                      len(de_deque))
            for data_e, descr_e in iterate_batch_results():
                yield data_e, descr_e

    else:
        log.debug("Using single generate call")

        # Just do everything in one call
        log.debug("Computing descriptors")
        descr_list = list(descr_generator.generate_elements(
            iter_capture_elements(), descr_factory,
            overwrite
        ))

        log.debug("Adding to set")
        descr_set.add_many_descriptors(descr_list)

        log.debug("yielding generated elements")
        for data, descr in zip(de_deque, descr_list):
            yield data, descr
