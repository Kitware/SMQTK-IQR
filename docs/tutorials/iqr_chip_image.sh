#!/bin/bash
__doc__="

Tutorial for Using SMQTK-IQR using GEOWATCH DAtA
===============================

This demonstrates an end-to-end pipeline on RGB toydata.

The tutorial generates its own training data so it can be run with minimal
effort to test that all core components of the system are working.

This walks through the entire process of performing IQR.

RunMe:
    export ACCELERATOR=gpu
    source ....
"

export ACCELERATOR="${ACCELERATOR:-gpu}"

# This tutorial will generate its own training data. Change these paths to
# wherever you would like the data to go (or use the defaults).  In general
# experiments will have a "data" DVC directory where the raw data lives, and an
# "experiment" DVC directory where you will train your model and store the
# results of prediction and evaluation.

# In this example we are not using any DVC directories, but we will use DVC in
# the variable names to be consistent with future tutorials.

DVC_DATA_DPATH="../../demodata/"
DVC_CHIPPED_DPATH="../../demodata/chipped_images"

mkdir -p "$DVC_DATA_DPATH"
mkdir -p "$DVC_CHIPPED_DPATH"

echo "
Generate Toy Data
-----------------

Now that we know where the data and our intermediate files will go, lets
generate the data we will use to train and evaluate with.

The kwcoco package comes with a commandline utility called 'kwcoco toydata' to
accomplish this.
"

# Define the names of the kwcoco files to generate
DATA_FPATH=$DVC_DATA_DPATH/vidshapes_rgb_data/data.kwcoco.json
# CHIP_FPATH=$DVC_DATA_DPATH/vidshapes_rgb_chip/data.kwcoco.json

# Generate toy datasets using the "kwcoco toydata" tool
kwcoco toydata vidshapes1-frames10-amazon --bundle_dpath "$DVC_DATA_DPATH"/vidshapes_rgb_data

# export the file paths for python script
# echo "$DATA_FPATH" > data_fpath.txt
# echo "$CHIP_FPATH" > chip_fpath.txt
