import pytest
import unittest.mock as mock

from smqtk_descriptors import DescriptorElementFactory
from smqtk_indexing import NearestNeighborsIndex
from smqtk_relevancy.interfaces.rank_relevancy import RankRelevancyWithFeedback
from smqtk_iqr.iqr.iqr_session import IqrSession
from smqtk_descriptors.impls.descriptor_element.memory import \
    DescriptorMemoryElement


class TestIqrSession (object):
    """
    Unit tests pertaining to the IqrSession class.
    """
    iqrs = None  # type: IqrSession

    @classmethod
    def setup_method(cls) -> None:
        """
        Setup an iqr session with a mocked rank relevancy
        """
        rank_relevancy_with_feedback = mock.MagicMock(spec=RankRelevancyWithFeedback)
        cls.iqrs = IqrSession(rank_relevancy_with_feedback)

    def test_context_manager_passthrough(self) -> None:
        """
        Test that using an instance as a context manager works and passes along
        the instance correctly.
        """
        with self.iqrs as iqrs:
            assert self.iqrs is iqrs

    def test_adjudicate_new_pos_neg(self) -> None:
        """
        Test that providing iterables to ``new_positives`` and
        ``new_negatives`` parameters result in additions to the positive and
        negative sets respectively.
        """

        p0 = DescriptorMemoryElement(0).set_vector([0])
        self.iqrs.adjudicate(new_positives=[p0])
        assert self.iqrs.positive_descriptors == {p0}
        assert self.iqrs.negative_descriptors == set()

        n1 = DescriptorMemoryElement(1).set_vector([1])
        self.iqrs.adjudicate(new_negatives=[n1])
        assert self.iqrs.positive_descriptors == {p0}
        assert self.iqrs.negative_descriptors == {n1}

        p2 = DescriptorMemoryElement(2).set_vector([2])
        p3 = DescriptorMemoryElement(3).set_vector([3])
        n4 = DescriptorMemoryElement(4).set_vector([4])
        self.iqrs.adjudicate(new_positives=[p2, p3], new_negatives=[n4])
        assert self.iqrs.positive_descriptors == {p0, p2, p3}
        assert self.iqrs.negative_descriptors == {n1, n4}

    def test_adjudicate_add_duplicates(self) -> None:
        """
        Test that adding duplicate descriptors as positive or negative
        adjudications has no effect as the behavior of sets should be observed.
        """

        p0 = DescriptorMemoryElement(0).set_vector([0])
        p2 = DescriptorMemoryElement(2).set_vector([2])
        n1 = DescriptorMemoryElement(1).set_vector([1])
        p3 = DescriptorMemoryElement(3).set_vector([3])
        n4 = DescriptorMemoryElement(4).set_vector([4])

        # Partially add the above descriptors
        self.iqrs.adjudicate(new_positives=[p0], new_negatives=[n1])
        assert self.iqrs.positive_descriptors == {p0}
        assert self.iqrs.negative_descriptors == {n1}

        # Add all descriptors, observing that that already added descriptors
        # are ignored.
        self.iqrs.adjudicate(new_positives=[p0, p2, p3], new_negatives=[n1, n4])
        assert self.iqrs.positive_descriptors == {p0, p2, p3}
        assert self.iqrs.negative_descriptors == {n1, n4}

        # Duplicate previous call so no new descriptors are added. No change or
        # issue should be observed.
        self.iqrs.adjudicate(new_positives=[p0, p2, p3], new_negatives=[n1, n4])
        assert self.iqrs.positive_descriptors == {p0, p2, p3}
        assert self.iqrs.negative_descriptors == {n1, n4}

    def test_adjudication_switch(self) -> None:
        """
        Test providing positives and negatives on top of an existing state such
        that the descriptor adjudications are reversed. (what was once positive
        is now negative, etc.)
        """

        p0 = DescriptorMemoryElement(0).set_vector([0])
        p1 = DescriptorMemoryElement(1).set_vector([1])
        p2 = DescriptorMemoryElement(2).set_vector([2])
        n3 = DescriptorMemoryElement(3).set_vector([3])
        n4 = DescriptorMemoryElement(4).set_vector([4])

        # Set initial state
        self.iqrs.positive_descriptors = {p0, p1, p2}
        self.iqrs.negative_descriptors = {n3, n4}

        # Adjudicate, partially swapping adjudications individually
        self.iqrs.adjudicate(new_positives=[n3])
        assert self.iqrs.positive_descriptors == {p0, p1, p2, n3}
        assert self.iqrs.negative_descriptors == {n4}

        self.iqrs.adjudicate(new_negatives=[p1])
        assert self.iqrs.positive_descriptors == {p0, p2, n3}
        assert self.iqrs.negative_descriptors == {n4, p1}

        # Adjudicate swapping remaining at the same time
        self.iqrs.adjudicate(new_positives=[n4], new_negatives=[p0, p2])
        assert self.iqrs.positive_descriptors == {n3, n4}
        assert self.iqrs.negative_descriptors == {p0, p1, p2}

    def test_adjudicate_remove_pos_neg(self) -> None:
        """
        Test that we can remove positive and negative adjudications using
        "un_*" parameters.
        """

        # Set initial state
        p0 = DescriptorMemoryElement(0).set_vector([0])
        p1 = DescriptorMemoryElement(1).set_vector([1])
        p2 = DescriptorMemoryElement(2).set_vector([2])
        n3 = DescriptorMemoryElement(3).set_vector([3])
        n4 = DescriptorMemoryElement(4).set_vector([4])

        # Set initial state
        self.iqrs.positive_descriptors = {p0, p1, p2}
        self.iqrs.negative_descriptors = {n3, n4}

        # "Un-Adjudicate" descriptors individually
        self.iqrs.adjudicate(un_positives=[p1])
        assert self.iqrs.positive_descriptors == {p0, p2}
        assert self.iqrs.negative_descriptors == {n3, n4}
        self.iqrs.adjudicate(un_negatives=[n3])
        assert self.iqrs.positive_descriptors == {p0, p2}
        assert self.iqrs.negative_descriptors == {n4}

        # "Un-Adjudicate" collectively
        self.iqrs.adjudicate(un_positives=[p0, p2], un_negatives=[n4])
        assert self.iqrs.positive_descriptors == set()
        assert self.iqrs.negative_descriptors == set()

    def test_adjudicate_combined_remove_unadj(self) -> None:
        """
        Test combining adjudication switching with un-adjudication.
        """

        # Set initial state
        p0 = DescriptorMemoryElement(0).set_vector([0])
        p1 = DescriptorMemoryElement(1).set_vector([1])
        p2 = DescriptorMemoryElement(2).set_vector([2])
        n3 = DescriptorMemoryElement(3).set_vector([3])
        n4 = DescriptorMemoryElement(4).set_vector([4])

        # Set initial state
        self.iqrs.positive_descriptors = {p0, p1, p2}
        self.iqrs.negative_descriptors = {n3, n4}

        # Add p5, switch p1 to negative, unadj p2
        p5 = DescriptorMemoryElement(5).set_vector([5])
        self.iqrs.adjudicate(new_positives=[p5], new_negatives=[p1],
                             un_positives=[p2])
        assert self.iqrs.positive_descriptors == {p0, p5}
        assert self.iqrs.negative_descriptors == {n3, n4, p1}

        # Add n6, switch n4 to positive, unadj n3
        n6 = DescriptorMemoryElement(6).set_vector([6])
        self.iqrs.adjudicate(new_positives=[n4], new_negatives=[n6],
                             un_negatives=[n3])
        assert self.iqrs.positive_descriptors == {p0, p5, n4}
        assert self.iqrs.negative_descriptors == {p1, n6}

    def test_adjudicate_both_labels(self) -> None:
        """
        Test that providing a descriptor element as both a positive AND
        negative adjudication causes no state change..
        """

        # Set initial state
        p0 = DescriptorMemoryElement(0).set_vector([0])
        p1 = DescriptorMemoryElement(1).set_vector([1])
        p2 = DescriptorMemoryElement(2).set_vector([2])
        n3 = DescriptorMemoryElement(3).set_vector([3])
        n4 = DescriptorMemoryElement(4).set_vector([4])

        # Set initial state
        self.iqrs.positive_descriptors = {p0, p1, p2}
        self.iqrs.negative_descriptors = {n3, n4}

        # Attempt adjudicating a new element as both postive AND negative
        e = DescriptorMemoryElement(5).set_vector([5])
        self.iqrs.adjudicate(new_positives=[e], new_negatives=[e])
        assert self.iqrs.positive_descriptors == {p0, p1, p2}
        assert self.iqrs.negative_descriptors == {n3, n4}

    def test_adjudicate_unadj_noeffect(self) -> None:
        """
        Test that an empty call, or un-adjudicating a descriptor that is not
        currently marked as a positive or negative, causes no state change.
        """

        # Set initial state
        p0 = DescriptorMemoryElement(0).set_vector([0])
        p1 = DescriptorMemoryElement(1).set_vector([1])
        p2 = DescriptorMemoryElement(2).set_vector([2])
        n3 = DescriptorMemoryElement(3).set_vector([3])
        n4 = DescriptorMemoryElement(4).set_vector([4])

        # Set initial state
        self.iqrs.positive_descriptors = {p0, p1, p2}
        self.iqrs.negative_descriptors = {n3, n4}

        # Empty adjudication
        self.iqrs.adjudicate()
        assert self.iqrs.positive_descriptors == {p0, p1, p2}
        assert self.iqrs.negative_descriptors == {n3, n4}

        # Attempt un-adjudication of a non-adjudicated element.
        e = DescriptorMemoryElement(5).set_vector([5])
        self.iqrs.adjudicate(un_positives=[e], un_negatives=[e])
        assert self.iqrs.positive_descriptors == {p0, p1, p2}
        assert self.iqrs.negative_descriptors == {n3, n4}

    def test_adjudicate_cache_resetting_positive(self) -> None:
        """
        Test results view cache resetting functionality on adjudicating certain
        ways.
        """
        e = DescriptorMemoryElement(0).set_vector([0])
        a = [(DescriptorMemoryElement(0), 1.0), (DescriptorMemoryElement(0), 2.0)]
        self.iqrs._ordered_pos = a
        self.iqrs._ordered_neg = a
        self.iqrs._ordered_non_adj = a

        # Check that adding a positive adjudication resets the positive and
        # non-adjudicated result caches.
        self.iqrs.adjudicate(new_positives=[e])
        assert self.iqrs._ordered_pos is None  # reset
        assert self.iqrs._ordered_neg is not None  # NOT reset
        assert self.iqrs._ordered_non_adj is None  # reset

    def test_adjudicate_cache_resetting_negative(self) -> None:
        """
        Test results view cache resetting functionality on adjudicating certain
        ways.
        """
        e = DescriptorMemoryElement(0).set_vector([0])
        a = [(DescriptorMemoryElement(0), 1.0), (DescriptorMemoryElement(0), 2.0)]
        self.iqrs._ordered_pos = a
        self.iqrs._ordered_neg = a
        self.iqrs._ordered_non_adj = a

        # Check that adding a positive adjudication resets the positive and
        # non-adjudicated result caches.
        self.iqrs.adjudicate(new_negatives=[e])
        assert self.iqrs._ordered_pos is not None  # NOT reset
        assert self.iqrs._ordered_neg is None  # reset
        assert self.iqrs._ordered_non_adj is None  # reset

    def test_adjudication_cache_not_reset(self) -> None:
        """
        Test that pos/neg/non-adj result caches are NOT reset when no state
        change occurs under different circumstances
        """
        # setup initial IQR session state.
        a = [(DescriptorMemoryElement(0), 1.0), (DescriptorMemoryElement(0), 2.0)]
        p0 = DescriptorMemoryElement(0).set_vector([0])
        p1 = DescriptorMemoryElement(1).set_vector([1])
        p2 = DescriptorMemoryElement(2).set_vector([2])
        n3 = DescriptorMemoryElement(3).set_vector([3])
        n4 = DescriptorMemoryElement(4).set_vector([4])
        self.iqrs.positive_descriptors = {p0, p1, p2}
        self.iqrs.negative_descriptors = {n3, n4}
        self.iqrs._ordered_pos = self.iqrs._ordered_neg = self.iqrs._ordered_non_adj = a

        # Empty adjudication
        self.iqrs.adjudicate()
        assert self.iqrs._ordered_pos is not None  # NOT reset
        assert self.iqrs._ordered_neg is not None  # NOT reset
        assert self.iqrs._ordered_non_adj is not None  # NOT reset

        # Repeat positive/negative adjudication
        self.iqrs.adjudicate(new_positives=[p0])
        assert self.iqrs._ordered_pos is not None  # NOT reset
        assert self.iqrs._ordered_neg is not None  # NOT reset
        assert self.iqrs._ordered_non_adj is not None  # NOT reset
        self.iqrs.adjudicate(new_negatives=[n3])
        assert self.iqrs._ordered_pos is not None  # NOT reset
        assert self.iqrs._ordered_neg is not None  # NOT reset
        assert self.iqrs._ordered_non_adj is not None  # NOT reset
        self.iqrs.adjudicate(new_positives=[p1], new_negatives=[n4])
        assert self.iqrs._ordered_pos is not None  # NOT reset
        assert self.iqrs._ordered_neg is not None  # NOT reset
        assert self.iqrs._ordered_non_adj is not None  # NOT reset

        # No-op un-adjudication
        e = DescriptorMemoryElement(5).set_vector([5])
        self.iqrs.adjudicate(un_positives=[e], un_negatives=[e])
        assert self.iqrs._ordered_pos is not None  # NOT reset
        assert self.iqrs._ordered_neg is not None  # NOT reset
        assert self.iqrs._ordered_non_adj is not None  # NOT reset

    def test_update_working_set_no_pos(self) -> None:
        """
        Working set updating should fail when there are no positive examples
        in the current state.
        """
        nn_index = mock.MagicMock(spec=NearestNeighborsIndex)
        # initially constructed session has no pos/neg adjudications
        assert len(self.iqrs.positive_descriptors) == 0
        assert len(self.iqrs.external_positive_descriptors) == 0
        with pytest.raises(
            RuntimeError,
            match=r"No positive descriptors to query the neighbor index with"
        ):
            self.iqrs.update_working_set(nn_index)

    def test_update_working_set(self) -> None:
        """
        Test "updating" with some positives across both positives containers.
        """
        d0 = DescriptorMemoryElement(0).set_vector([0])
        d1 = DescriptorMemoryElement(1).set_vector([1])
        d2 = DescriptorMemoryElement(2).set_vector([2])

        # Mock index. Make it so that the neighbors of inputs is just the input
        # itself.
        nn_index: NearestNeighborsIndex = mock.Mock(spec=NearestNeighborsIndex)
        nn_index.nn = mock.Mock(side_effect=lambda d, n: ([d], [0.]))  # type: ignore

        # See positive descriptors
        self.iqrs.positive_descriptors.update({d0, d1})
        self.iqrs.external_positive_descriptors.update({d2})

        assert len(self.iqrs.working_set) == 0

        self.iqrs.update_working_set(nn_index)

        assert len(self.iqrs.working_set) == 3
        assert set(self.iqrs.working_set.descriptors()) == {d0, d1, d2}

    def test_refine_no_pos(self) -> None:
        """
        Test that refinement cannot occur if there are no positive descriptor
        external/adjudicated elements.
        """
        with pytest.raises(RuntimeError, match='Did not find at least one '
                                               'positive adjudication'):
            self.iqrs.refine()

    def test_refine_no_prev_results(self) -> None:
        """
        Test that the results of RelevancyIndex ranking are directly reflected
        in a new results dictionary of probability values, even for elements
        that were also used in adjudication.

        This test is useful because a previous state of the IQR Session
        structure would force return probabilities for some descriptor elements
        to certain values if they were also present in the positive or negative
        adjudicate (internal or external) sets.
        """
        test_in_pos_elem = DescriptorMemoryElement(0).set_vector([0])
        test_in_neg_elem = DescriptorMemoryElement(1).set_vector([1])
        test_ex_pos_elem = DescriptorMemoryElement(2).set_vector([2])
        test_ex_neg_elem = DescriptorMemoryElement(3).set_vector([3])
        test_other_elem = DescriptorMemoryElement(4).set_vector([4])

        # Mock the working set so it has the correct size and elements
        desc_list = [test_in_pos_elem, test_in_neg_elem, test_other_elem]
        self.iqrs.working_set.add_many_descriptors(desc_list)

        # Mock return dictionary, probabilities don't matter much other than
        # they are not 1.0 or 0.0.
        pool_ids = [de.uuid() for de in desc_list]
        self.iqrs.rank_relevancy_with_feedback.rank_with_feedback.return_value = (  # type: ignore
          [0.5, 0.5, 0.5],
          pool_ids
        )

        # Asserting expected pre-condition where there are no results yet.
        assert self.iqrs.results is None
        assert self.iqrs.feedback_list is None

        # Prepare IQR state for refinement
        # - set dummy internal/external positive negatives.
        self.iqrs.external_descriptors(
            positive=[test_ex_pos_elem], negative=[test_ex_neg_elem]
        )
        self.iqrs.adjudicate(
            new_positives=[test_in_pos_elem], new_negatives=[test_in_neg_elem]
        )

        # Test calling refine method
        self.iqrs.refine()

        # We test that:
        # - ``rank_relevancy_with_feedback.rank`` called with the combination of
        #   external/adjudicated descriptor elements.
        # - ``results`` attribute now has a dict value
        # - value of ``results`` attribute is what we expect.
        pool_uids, pool_de = zip(*self.iqrs.working_set.items())
        pool = [de.vector() for de in pool_de]
        self.iqrs.rank_relevancy_with_feedback.rank_with_feedback.assert_called_once_with(  # type: ignore
            [test_in_pos_elem.vector(), test_ex_pos_elem.vector()],
            [test_in_neg_elem.vector(), test_ex_neg_elem.vector()],
            pool,
            pool_uids
        )
        assert self.iqrs.results is not None
        assert len(self.iqrs.results) == 3
        assert test_other_elem in self.iqrs.results
        assert test_in_pos_elem in self.iqrs.results
        assert test_in_neg_elem in self.iqrs.results

        assert self.iqrs.results[test_other_elem] == 0.5
        assert self.iqrs.results[test_in_pos_elem] == 0.5
        assert self.iqrs.results[test_in_neg_elem] == 0.5
        assert self.iqrs.feedback_list == desc_list

    def test_refine_with_prev_results(self) -> None:
        """
        Test that the results of RelevancyIndex ranking are directly reflected
        in an existing results dictionary of probability values.
        """
        test_in_pos_elem = DescriptorMemoryElement(0).set_vector([0])
        test_in_neg_elem = DescriptorMemoryElement(1).set_vector([1])
        test_ex_pos_elem = DescriptorMemoryElement(2).set_vector([2])
        test_ex_neg_elem = DescriptorMemoryElement(3).set_vector([3])
        test_other_elem = DescriptorMemoryElement(4).set_vector([4])

        # Mock the working set so it has the correct size and elements
        desc_list = [test_in_pos_elem, test_in_neg_elem, test_other_elem]
        self.iqrs.working_set.add_many_descriptors(desc_list)

        # Mock return dictionary, probabilities don't matter much other than
        # they are not 1.0 or 0.0.
        pool_ids = [*self.iqrs.working_set.iterkeys()]
        self.iqrs.rank_relevancy_with_feedback.rank_with_feedback.return_value = (  # type: ignore
          [0.5, 0.5, 0.5],
          pool_ids
        )

        # Create a "previous state" of the results dictionary containing
        # results from our "working set" of descriptor elements.
        self.iqrs.results = {
            test_in_pos_elem: 0.2,
            test_in_neg_elem: 0.2,
            test_other_elem: 0.2,
            # ``refine`` replaces the previous dict, so disjoint keys are
            # NOT retained.
            'something else': 0.3,  # type: ignore
        }

        # Create a "previous state" of the feedback results.
        self.iqrs.feedback_list = [test_ex_pos_elem,
                                   test_ex_neg_elem,
                                   test_other_elem]

        # Prepare IQR state for refinement
        # - set dummy internal/external positive negatives.
        self.iqrs.external_descriptors(
            positive=[test_ex_pos_elem], negative=[test_ex_neg_elem]
        )
        self.iqrs.adjudicate(
            new_positives=[test_in_pos_elem], new_negatives=[test_in_neg_elem]
        )

        # Test calling refine method
        self.iqrs.refine()

        # We test that:
        # - ``rel_index.rank`` called with the combination of
        #   external/adjudicated descriptor elements.
        # - ``results`` attribute now has an dict value
        # - value of ``results`` attribute is what we expect.
        pool_uids, pool_de = zip(*self.iqrs.working_set.items())
        pool = [de.vector() for de in pool_de]
        self.iqrs.rank_relevancy_with_feedback.rank_with_feedback.assert_called_once_with(  # type: ignore
            [test_in_pos_elem.vector(), test_ex_pos_elem.vector()],
            [test_in_neg_elem.vector(), test_ex_neg_elem.vector()],
            pool,
            pool_uids
        )
        assert self.iqrs.results is not None
        assert len(self.iqrs.results) == 3
        assert test_other_elem in self.iqrs.results
        assert test_in_pos_elem in self.iqrs.results
        assert test_in_neg_elem in self.iqrs.results
        assert 'something else' not in self.iqrs.results

        assert self.iqrs.results[test_other_elem] == 0.5
        assert self.iqrs.results[test_in_pos_elem] == 0.5
        assert self.iqrs.results[test_in_neg_elem] == 0.5
        assert self.iqrs.feedback_list == desc_list

    def test_ordered_results_no_results_no_cache(self) -> None:
        """
        Test that an empty list is returned when ``ordered_results`` is called
        before any refinement has occurred.
        """
        assert self.iqrs.ordered_results() == []

    def test_ordered_results_has_cache(self) -> None:
        """
        Test that a shallow copy of the cached list is returned when there is
        a cache.
        """
        # Simulate there being a cache
        self.iqrs._ordered_pos = ['simulated', 'cache']  # type: ignore
        actual = self.iqrs.get_positive_adjudication_relevancy()
        assert actual == self.iqrs._ordered_pos
        assert id(actual) != id(self.iqrs._ordered_pos)

    def test_ordered_results_has_results_no_cache(self) -> None:
        """
        Test that an appropriate list is returned by ``ordered_results`` after
        a refinement has occurred.
        """

        # Mocking results map existing for return.
        d0 = DescriptorMemoryElement(0).set_vector([0])
        d1 = DescriptorMemoryElement(1).set_vector([1])
        d2 = DescriptorMemoryElement(2).set_vector([2])
        d3 = DescriptorMemoryElement(3).set_vector([3])
        self.iqrs.results = {
            d0: 0.0,
            d1: 0.8,
            d2: 0.2,
            d3: 0.4,
        }

        # Cache should be empty before call to ``ordered_results``
        assert self.iqrs._ordered_results is None

        with mock.patch('smqtk_iqr.iqr.iqr_session.sorted',
                        side_effect=sorted) as m_sorted:
            actual1 = self.iqrs.ordered_results()
            m_sorted.assert_called_once()

        expected = [(d1, 0.8), (d3, 0.4), (d2, 0.2), (d0, 0.0)]
        assert actual1 == expected

        # Calling the method a second time should not result in a ``sorted``
        # operation due to caching.
        with mock.patch('smqtk_iqr.iqr.iqr_session.sorted') as m_sorted:
            actual2 = self.iqrs.ordered_results()
            m_sorted.assert_not_called()

        assert actual2 == expected
        # Both returns should be shallow copies, thus not the same list
        # instances.
        assert id(actual1) != id(actual2)

    def test_ordered_results_has_results_post_reset(self) -> None:
        """
        Test that an empty list is returned after a reset where there was a
        cached value before the reset.
        """

        # Mocking results map existing for return.
        d0 = DescriptorMemoryElement(0).set_vector([0])
        d1 = DescriptorMemoryElement(1).set_vector([1])
        d2 = DescriptorMemoryElement(2).set_vector([2])
        d3 = DescriptorMemoryElement(3).set_vector([3])
        self.iqrs.results = {
            d0: 0.0,
            d1: 0.8,
            d2: 0.2,
            d3: 0.4,
        }

        # Initial call to ``ordered_results`` should have a non-None return.
        assert self.iqrs.ordered_results() is not None

        self.iqrs.reset()

        # Post-reset, there should be no results nor cache.
        actual = self.iqrs.ordered_results()
        assert actual == []

    def test_feedback_results_weird_state(self) -> None:
        """
        Test that there is a fallback case when assumptions are violated.

        This method assumes the value of `feedback_list` will either be
        iterable or will be None. If this is violated there should be a hard
        stop.
        """
        # not iterable, not None
        self.iqrs.feedback_list = 666  # type: ignore

        with pytest.raises(
            RuntimeError,
            match=r"Feedback results in an invalid state"
        ):
            self.iqrs.feedback_results()

    def test_feedback_results_no_results_no_cache(self) -> None:
        """
        Test that an empty list is returned when ``feedback_results`` is called
        before any refinement has occurred.
        """
        assert self.iqrs.feedback_results() == []

    def test_feedback_results_has_cache(self) -> None:
        """
        Test that a shallow copy of the cached list is returned when there is
        a cache.
        """
        # Simulate there being a cache
        self.iqrs.feedback_list = ['simulated', 'cache']  # type: ignore
        actual = self.iqrs.feedback_results()
        assert actual == self.iqrs.feedback_list
        assert id(actual) != id(self.iqrs.feedback_list)

    def test_feedback_results_has_results_post_reset(self) -> None:
        """
        Test that an empty list is returned after a reset where there was a
        cached value before the reset.
        """

        # Mocking results map existing for return.
        d0 = DescriptorMemoryElement(0).set_vector([0])
        d1 = DescriptorMemoryElement(1).set_vector([1])
        d2 = DescriptorMemoryElement(2).set_vector([2])
        d3 = DescriptorMemoryElement(3).set_vector([3])
        self.iqrs.feedback_list = [
            d0,
            d1,
            d2,
            d3,
        ]

        # Initial call to ``ordered_results`` should have a non-None return.
        assert self.iqrs.feedback_results() is not None

        self.iqrs.reset()

        # Post-reset, there should be no results nor cache.
        actual = self.iqrs.feedback_results()
        assert actual == []

    def test_get_positive_adjudication_relevancy_has_cache(self) -> None:
        """
        Test that a shallow copy of the cached list is returned if there is a
        cache.
        """

        self.iqrs._ordered_pos = ['simulation', 'cache']  # type: ignore
        actual = self.iqrs.get_positive_adjudication_relevancy()
        assert actual == ['simulation', 'cache']
        assert id(actual) != id(self.iqrs._ordered_pos)

    def test_get_positive_adjudication_relevancy_no_cache_no_results(self) -> None:
        """
        Test that ``get_positive_adjudication_relevancy`` returns None when in a
        pre-refine state when there are no positive adjudications.
        """
        assert self.iqrs.get_positive_adjudication_relevancy() == []

    def test_get_positive_adjudication_relevancy_no_cache_has_results(self) -> None:
        """
        Test that we can get positive adjudication relevancy scores correctly
        from a not-cached state.
        """
        d0 = DescriptorMemoryElement(0).set_vector([0])
        d1 = DescriptorMemoryElement(1).set_vector([1])
        d2 = DescriptorMemoryElement(2).set_vector([2])
        d3 = DescriptorMemoryElement(3).set_vector([3])

        # Simulate a populated contributing adjudication state (there must be
        # some positives for a simulated post-refine state to be valid).
        self.iqrs.rank_contrib_pos = {d1, d3}
        self.iqrs.rank_contrib_neg = {d0}

        # Simulate post-refine results map.
        self.iqrs.results = {
            d0: 0.1,
            d1: 0.8,
            d2: 0.2,
            d3: 0.4,
        }

        # Cache is initially empty
        assert self.iqrs._ordered_pos is None

        # Test that the appropriate sorting actually occurs.
        with mock.patch('smqtk_iqr.iqr.iqr_session.sorted',
                        side_effect=sorted) as m_sorted:
            actual1 = self.iqrs.get_positive_adjudication_relevancy()
            m_sorted.assert_called_once()

        expected = [(d1, 0.8), (d3, 0.4)]
        assert actual1 == expected

        # Calling the method a second time should not result in a ``sorted``
        # operation due to caching.
        with mock.patch('smqtk_iqr.iqr.iqr_session.sorted',
                        side_effect=sorted) as m_sorted:
            actual2 = self.iqrs.get_positive_adjudication_relevancy()
            m_sorted.assert_not_called()

        assert actual2 == expected
        # Both returns should be shallow copies, thus not the same list
        # instances.
        assert id(actual1) != id(actual2)

    def test_get_negative_adjudication_relevancy_has_cache(self) -> None:
        """
        Test that a shallow copy of the cached list is returned if there is a
        cache.
        """
        self.iqrs._ordered_neg = ['simulation', 'cache']  # type: ignore
        actual = self.iqrs.get_negative_adjudication_relevancy()
        assert actual == ['simulation', 'cache']
        assert id(actual) != id(self.iqrs._ordered_neg)

    def test_get_negative_adjudication_relevancy_no_cache_no_results(self) -> None:
        """
        Test that ``get_negative_adjudication_relevancy`` returns None when in a
        pre-refine state when there are no negative adjudications.
        """
        assert self.iqrs.get_negative_adjudication_relevancy() == []

    def test_get_negative_adjudication_relevancy_no_cache_has_results(self) -> None:
        """
        Test that we can get negative adjudication relevancy scores correctly
        from a not-cached state.
        """
        d0 = DescriptorMemoryElement(0).set_vector([0])
        d1 = DescriptorMemoryElement(1).set_vector([1])
        d2 = DescriptorMemoryElement(2).set_vector([2])
        d3 = DescriptorMemoryElement(3).set_vector([3])

        # Simulate a populated contributing adjudication state (there must be
        # some positives for a simulated post-refine state to be valid).
        self.iqrs.rank_contrib_pos = {d1}
        self.iqrs.rank_contrib_neg = {d0, d2}

        # Simulate post-refine results map.
        self.iqrs.results = {
            d0: 0.1,
            d1: 0.8,
            d2: 0.2,
            d3: 0.4,
        }

        # Cache is initially empty
        assert self.iqrs._ordered_neg is None

        # Test that the appropriate sorting actually occurs.
        with mock.patch('smqtk_iqr.iqr.iqr_session.sorted',
                        side_effect=sorted) as m_sorted:
            actual1 = self.iqrs.get_negative_adjudication_relevancy()
            m_sorted.assert_called_once()

        expected = [(d2, 0.2), (d0, 0.1)]
        assert actual1 == expected

        # Calling the method a second time should not result in a ``sorted``
        # operation due to caching.
        with mock.patch('smqtk_iqr.iqr.iqr_session.sorted',
                        side_effect=sorted) as m_sorted:
            actual2 = self.iqrs.get_negative_adjudication_relevancy()
            m_sorted.assert_not_called()

        assert actual2 == expected
        # Both returns should be shallow copies, thus not the same list
        # instances.
        assert id(actual1) != id(actual2)

    def test_get_unadjudicated_relevancy_has_cache(self) -> None:
        """
        Test that a shallow copy of the cached list is returned if there is a
        cache.
        """
        self.iqrs._ordered_non_adj = ['simulation', 'cache']  # type: ignore
        actual = self.iqrs.get_unadjudicated_relevancy()
        assert actual == ['simulation', 'cache']
        assert id(actual) != id(self.iqrs._ordered_non_adj)

    def test_get_unadjudicated_relevancy_no_cache_no_results(self) -> None:
        """
        Test that ``get_unadjudicated_relevancy`` returns None when in a
        pre-refine state when there is results state.
        """
        assert self.iqrs.get_unadjudicated_relevancy() == []

    def test_get_unadjudicated_relevancy_no_cache_has_results(self) -> None:
        """
        Test that we get the non-adjudicated DescriptorElements and their
        scores correctly from a non-cached state with known results.
        """
        d0 = DescriptorMemoryElement(0).set_vector([0])
        d1 = DescriptorMemoryElement(1).set_vector([1])
        d2 = DescriptorMemoryElement(2).set_vector([2])
        d3 = DescriptorMemoryElement(3).set_vector([3])

        # Simulate a populated contributing adjudication state (there must be
        # some positives for a simulated post-refine state to be valid).
        self.iqrs.rank_contrib_pos = {d1}
        self.iqrs.rank_contrib_neg = {d0}

        # Simulate post-refine results map.
        self.iqrs.results = {
            d0: 0.1,
            d1: 0.8,
            d2: 0.2,
            d3: 0.4,
        }

        # Cache should be initially empty
        assert self.iqrs._ordered_non_adj is None

        # Test that the appropriate sorting actually occurs.
        with mock.patch('smqtk_iqr.iqr.iqr_session.sorted',
                        side_effect=sorted) as m_sorted:
            actual1 = self.iqrs.get_unadjudicated_relevancy()
            m_sorted.assert_called_once()

        expected = [(d3, 0.4), (d2, 0.2)]
        assert actual1 == expected

        # Calling the method a second time should not result in a ``sorted``
        # operation due to caching.
        with mock.patch('smqtk_iqr.iqr.iqr_session.sorted',
                        side_effect=sorted) as m_sorted:
            actual2 = self.iqrs.get_unadjudicated_relevancy()
            m_sorted.assert_not_called()

        assert actual2 == expected
        # Both returns should be shallow copies, thus not the same list
        # instances.
        assert id(actual1) != id(actual2)

    def test_reset_result_cache_invalidation(self) -> None:
        """
        Test that calling the reset method resets the result view caches to
        None.
        """

        self.iqrs.reset()
        assert self.iqrs._ordered_pos is None
        assert self.iqrs._ordered_neg is None
        assert self.iqrs._ordered_non_adj is None

    def test_get_set_state(self) -> None:
        """
        Simple test of get-state functionality
        """
        d0 = DescriptorMemoryElement(0).set_vector([0])
        d1 = DescriptorMemoryElement(1).set_vector([1])
        d2 = DescriptorMemoryElement(2).set_vector([2])
        d3 = DescriptorMemoryElement(3).set_vector([3])

        # Set up the session to have some state.
        self.iqrs.positive_descriptors.update({d0})
        self.iqrs.negative_descriptors.update({d1})
        self.iqrs.external_positive_descriptors.update({d2})
        self.iqrs.external_negative_descriptors.update({d3})

        b = self.iqrs.get_state_bytes()
        assert b is not None
        assert len(b) > 0

        rank_relevancy_with_feedback = mock.MagicMock(spec=RankRelevancyWithFeedback)
        descr_fact = DescriptorElementFactory(DescriptorMemoryElement, {})
        new_iqrs = IqrSession(rank_relevancy_with_feedback)
        new_iqrs.set_state_bytes(b, descr_fact)

        assert self.iqrs.positive_descriptors == new_iqrs.positive_descriptors
        assert self.iqrs.negative_descriptors == new_iqrs.negative_descriptors
        assert self.iqrs.external_positive_descriptors == new_iqrs.external_positive_descriptors
        assert self.iqrs.external_negative_descriptors == new_iqrs.external_negative_descriptors

    def test_refine_no_neg(self) -> None:
        """
        Test refinement without any negative adjudications and ensure that the farthest
        descriptor from the positive example is automatically chosen as the negative example.
        """
        test_in_pos_elem = DescriptorMemoryElement(0).set_vector([0])
        test_ex_pos_elem = DescriptorMemoryElement(2).set_vector([2])
        test_other_elem = DescriptorMemoryElement(4).set_vector([4])
        test_other_elem_far = DescriptorMemoryElement(5).set_vector([5])

        # Mock the working set so it has the correct size and elements
        desc_list = [test_in_pos_elem, test_other_elem, test_other_elem_far]
        self.iqrs.working_set.add_many_descriptors(desc_list)

        # Mock return dictionary, probabilities don't matter much other than
        # they are not 1.0 or 0.0.
        pool_ids = [de.uuid() for de in desc_list]
        self.iqrs.rank_relevancy_with_feedback.rank_with_feedback.return_value = (  # type: ignore
          [0.7, 0.3, 0.1],
          pool_ids
        )

        # Prepare IQR state for refinement
        # - set dummy internal/external positive negatives w/ no negative examples
        self.iqrs.external_descriptors(
            positive=[test_ex_pos_elem], negative=[]
        )
        self.iqrs.adjudicate(
            new_positives=[test_in_pos_elem], new_negatives=[]
        )

        # Test calling refine method
        self.iqrs.refine()

        self.iqrs.rank_relevancy_with_feedback.rank_with_feedback.assert_called_once()  # type: ignore

        # Get the most recent call arguments,
        # extracting what was passed as the negative descriptor input,
        # which should be populated by the auto-negative selection logic.
        neg_list_arg = self.iqrs.rank_relevancy_with_feedback.rank_with_feedback.call_args[0][1]  # type: ignore
        assert neg_list_arg == [test_other_elem_far.vector()]

    def test_refine_neg_autoselect_fail(self) -> None:
        """
        Test refinement without any negative adjudications and when all of the other
        possible adjudications are already marked as positive.
        """
        test_in_pos_elem = DescriptorMemoryElement(0).set_vector([0])
        test_ex_pos_elem = DescriptorMemoryElement(2).set_vector([2])
        test_other_elem = DescriptorMemoryElement(4).set_vector([4])
        test_other_elem_far = DescriptorMemoryElement(5).set_vector([5])

        # Mock the working set so it has the correct size and elements
        desc_list = [test_in_pos_elem, test_other_elem, test_other_elem_far]
        self.iqrs.working_set.add_many_descriptors(desc_list)

        # Mock return dictionary, probabilities don't matter much other than
        # they are not 1.0 or 0.0.
        pool_ids = [de.uuid() for de in desc_list]
        self.iqrs.rank_relevancy_with_feedback.rank_with_feedback.return_value = (  # type: ignore
          [0.7, 0.3, 0.1],
          pool_ids
        )

        # Prepare IQR state for refinement
        # - all external descriptors marked as positive examples and no negatives
        self.iqrs.external_descriptors(
            positive=[test_ex_pos_elem, test_other_elem, test_other_elem_far], negative=[]
        )
        self.iqrs.adjudicate(
            new_positives=[test_in_pos_elem], new_negatives=[]
        )

        with pytest.raises(
            RuntimeError,
            match=r"Negative auto-selection failed. Did not select any negative examples."
        ):
            self.iqrs.refine()


class TestIqrSessionBehavior (object):
    """
    Test certain IqrSession state transitions
    """
    # TODO - More complicated state transitions.
