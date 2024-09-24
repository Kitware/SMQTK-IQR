Tutorial 2 - Demo KWCoco with Computed Descriptors
--------------------------------------------------

This tutorial builds on tutorial 1, and instead of hand crafting contrived
features, we use a real network to generate features. The network will be
minimally trained, so the features are effectively random deep features, but
this turns out to work surprisingly well as shown by [DeepCluster]_.


.. [DeepCluster] https://openaccess.thecvf.com/content_ECCV_2018/papers/Mathilde_Caron_Deep_Clustering_for_ECCV_2018_paper.pdf

The script ``./run_tutorial_002.sh`` is a well-documented bash script that you
should step through manually to understand the individual steps of the process.
