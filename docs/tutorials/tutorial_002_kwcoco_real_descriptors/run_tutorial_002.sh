#!/usr/bin/env bash
__doc__='
---------------------------------------------------------------
IQR demo with PrePopulated Hidden Layer/Activations Descriptors
---------------------------------------------------------------

The following guide provides steps to run the IQR demo using a prepopulated
hidden activation descriptor set.
The overall process is outlined as follows:
1. Generate a geowatch toydata set based upon the code in Geowatch Tutorial 1.
2. Perform the geowatch.fusion.predict operation to generate the hidden layer
   descriptors, and stitch them back to form the kwcoco data set.
3. Build the IQR model using the ingest_precomputed_descriptors.py script.
4. Run the IQR service and search dispatcher with the config files provided
in the tutorials directory.

More details and comments on the steps are provided with the commands below.

Details on library packages, versions and depencies:
The demo was written and run with Python version 3.11.2.

The ``ingest_precomputed_descriptors.py`` script is used to generate the
descriptor set without calling the methods in one of the descriptor generator
modules. Using the PrePopulatedDescriptorGenerator class, the descriptor set is
generated from a manifest file that contains the paths to the image files and
the corresponding descriptor files. The manifest file is created by the
``prepare_real_descriptors.py`` script that uses a very simple model to build
real descriptors on the kwcoco demo data.



This will require geowatch:

    pip install geowatch
    geowatch finish_install

Also need the faiss library to be installed
pip install faiss-cpu==1.8.0
pip install "psycopg2-binary>=2.9.5,<3.0.0"

To install MongoDB see: ../../environment/installing_mongodb.rst

This script should be run from inside the tutorial directory. E.g. on the
developers machine this looks like:

.. code:: bash

    cd $HOME/code/smqtk-repos/SMQTK-IQR/docs/tutorials/tutorial_002_kwcoco_real_descriptors
'

# Choose a working directory where we can write data
WORKING_DIRECTORY=./workdir

# Choose cpu or gpu
if nvidia-smi > /dev/null ; then
    export ACCELERATOR="${ACCELERATOR:-gpu}"
else
    export ACCELERATOR="${ACCELERATOR:-cpu}"
fi

### Setup Environment Variables
# The location of all important paths should be knowable a-priori to running
# this script and potentially before the data is even generated.

CHIPPED_IMAGES_DPATH=$WORKING_DIRECTORY/processed/chips
MANIFEST_FPATH=$WORKING_DIRECTORY/processed/manifest.json

KWCOCO_SPLITS_DPATH=$WORKING_DIRECTORY/kwcoco_splits
TRAIN_FPATH=$KWCOCO_SPLITS_DPATH/vidshapes_rgb_train/data.kwcoco.json
VALI_FPATH=$KWCOCO_SPLITS_DPATH/vidshapes_rgb_vali/data.kwcoco.json
TEST_FPATH=$KWCOCO_SPLITS_DPATH/vidshapes_rgb_test/data.kwcoco.json

PREDICT_DPATH=$WORKING_DIRECTORY/predictions
PREDICT_OUTPUT_FPATH="$PREDICT_DPATH"/pred.kwcoco.json

TRAINING_ROOT_DIR=$WORKING_DIRECTORY/training/$HOSTNAME/$USER/ToyRGB/runs/ToyRGB_Demo_V001
PACKAGE_FPATH="$TRAINING_ROOT_DIR"/deep_model.pt

echo "
ACCELERATOR          = $ACCELERATOR
WORKING_DIRECTORY    = $WORKING_DIRECTORY
CHIPPED_IMAGES_DPATH = $CHIPPED_IMAGES_DPATH
MANIFEST_FPATH       = $MANIFEST_FPATH

KWCOCO_SPLITS_DPATH  = $KWCOCO_SPLITS_DPATH
PREDICT_DPATH        = $PREDICT_DPATH
PREDICT_OUTPUT_FPATH = $PREDICT_OUTPUT_FPATH

PACKAGE_FPATH        = $PACKAGE_FPATH
"

# (Optional) Remove previous directories and contents for a clean model build
# rm -rf "$WORKING_DIRECTORY"
mkdir -p "$WORKING_DIRECTORY"

# ---------------------------------------------------------------------------
# Build the toydata set.  (See Geowatch Tutorial 1 for more details)

echo "
------
Step 1
------
Generate the demo kwcoco data
"
# Generate toy datasets using the "kwcoco toydata" tool
kwcoco toydata vidshapes2-frames10-amazon --dst "$TRAIN_FPATH"
kwcoco toydata vidshapes4-frames10-amazon --dst "$VALI_FPATH"
kwcoco toydata vidshapes2-frames6-amazon --dst "$TEST_FPATH"


echo "
------
Step 2
------
The next step is to train a small model on these images.
"

# This step is only needed if the pretrained model doesnt exist
# (or you want to retrain with different hyperparams, but for this
#  demo it doesnt matter)
if [ ! -f "$PACKAGE_FPATH" ]; then
    python -m geowatch.tasks.fusion fit --config "
    data:
        num_workers          : 0
        train_dataset        : $TRAIN_FPATH
        vali_dataset         : $VALI_FPATH
        channels             : 'r|g|b'
        time_steps           : 5
        chip_dims            : 128
        batch_size           : 2
    model:
        class_path: MultimodalTransformer
        init_args:
            name              : ToyRGB_Demo_V001
            arch_name         : smt_it_stm_p8
            global_box_weight : 1
    optimizer:
      class_path: torch.optim.AdamW
      init_args:
        lr           : 3e-4
        weight_decay : 3e-5
    trainer:
      default_root_dir     : $TRAINING_ROOT_DIR
      accelerator          : $ACCELERATOR
      devices              : 1
      max_steps            : 2
      num_sanity_val_steps : 0
      limit_val_batches    : 1
      limit_train_batches  : 4
    "

    # Ensure that a model package is written to the place we expect it to be.
    # The training process is a bit wonky with our assumption that we can
    # know the locations of intermediate files a-priori. In a production
    # use-case, you would know where this model filepath is.
    python -c "if 1:
        import pathlib
        import shutil
        package_fpath = pathlib.Path(r'$PACKAGE_FPATH')
        if not package_fpath.exists():
            default_root = pathlib.Path(r'$TRAINING_ROOT_DIR')
            pkg = default_root / 'final_package.pt'
            if not pkg.exists():
                cand = sorted(default_root.glob('package-interupt/*.pt'))
                assert len(cand)
                pkg = cand[-1]
            shutil.copy(pkg, package_fpath)
    "
fi


echo "
------
Step 3
------
Predict deep descriptors for a kwcoco file.

Perform the predict operation to generate the hidden layer descriptors and
build the kwcoco dataset for IQR
"

if [[ "$ACCELERATOR" == "gpu" ]]; then
    PREDICT_DEVICE_ARGS=(--devices="0,")
else
    PREDICT_DEVICE_ARGS=()
fi
python -m geowatch.tasks.fusion.predict \
    --test_dataset="$TEST_FPATH" \
    --package_fpath="$PACKAGE_FPATH"  \
    --with_hidden_layers=True  \
    --pred_dataset="$PREDICT_OUTPUT_FPATH" \
     "${PREDICT_DEVICE_ARGS[@]}"


echo "
Step 4
------
Generate image chips with hidden layer descriptors
"

python prepare_real_descriptors.py \
    --coco_fpath "$PREDICT_OUTPUT_FPATH" \
    --out_chips_dpath "$CHIPPED_IMAGES_DPATH" \
    --out_mainfest_fpath "$MANIFEST_FPATH"


echo "
Step 5
------
Build the models for IQR. Generate the SMQTK-IQR data set, descriptor set and faiss nnindex
"

# NOTE: there is a "workdir" in the runApp configs, which will put outputs in
# this working directory. TODO: make this specifiable on the CLI here.
python ingest_precomputed_descriptors.py \
    --verbose=True \
    --config runApp.IqrSearchApp.json runApp.IqrRestService.json \
    --manifest_fpath "$MANIFEST_FPATH" \
    --debug_nn_index=True \
    --tab "GEOWATCH_DEMO"


echo "
Step 6
------
Ensure MongoDB is running
"
if ! systemctl status mongod --no-pager; then
    sudo systemctl start mongod
    systemctl status mongod --no-pager
fi


echo "
Step 7
------
Run the IQR search dispatcher and IQR service from the same directory.

Alternative: Instead of running the commands in tmux sessions, you can simply
two open different terminals and execute the service and dispatcher in each

In the first terminal:

    runApplication -a IqrService -c runApp.IqrRestService.json

In the second terminal:

    runApplication -a IqrSearchDispatcher -c runApp.IqrSearchApp.json
"

# NOTE: ensure the relevant venv is activated in the new sessions.

# Following script provides commands to run in a single tmux session
# with two split windows
SESSION_NAME="SMQTK-TUTORAL2-SERVERS"
tmux kill-session -t "${SESSION_NAME}" || true
tmux new-session -d -s "${SESSION_NAME}" "/bin/bash"
tmux rename-window -t "${SESSION_NAME}:0" 'main'

COMMAND="runApplication -v -a IqrService -c runApp.IqrRestService.json"
tmux split-window -v -t "${SESSION_NAME}:0.0"
tmux select-pane -t "${SESSION_NAME}:0.0"
tmux send -t "$SESSION_NAME" "$COMMAND" Enter

COMMAND="runApplication -v -a IqrSearchDispatcher -c runApp.IqrSearchApp.json"
tmux select-pane -t "${SESSION_NAME}:0.1"
tmux send -t "$SESSION_NAME" "$COMMAND" Enter

# Fixup the pane layout
tmux select-layout -t "${SESSION_NAME}" even-vertical

# 6. Open a web-browser and navigate to 'localhost:5000'
python -c "import webbrowser; webbrowser.open('127.0.0.1:5000')"

# Reminder: ctrl+b + <arrow-key> lets you move between splits
# within a tmux session.
if [[ "$TMUX" == "" ]]; then
    # not in tmux, attach to the session
    tmux attach-session -t "${SESSION_NAME}"
else
    # already in tmux, switch to the session
    tmux switch -t "${SESSION_NAME}"
fi

echo "
THE FOLLOWING ARE MANUAL STEPS THE USER MUST TAKE.

* In the web-browser, select 'GEOWATCH_DEMO' IQR instance

* Both username and password are set to 'demo' by config files

* You may now interact with the IQR web interface.
"
