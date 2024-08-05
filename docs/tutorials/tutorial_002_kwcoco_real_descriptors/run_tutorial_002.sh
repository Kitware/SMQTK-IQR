#!/usr/bin/env bash
__doc__='
# ---------------------------------------------------------------
# IQR demo with PrePopulated Hidden Layer/Activations Descriptors
# ---------------------------------------------------------------

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
Older versions of packages flask 2.0.1 and werkzeug 2.0.0 were used.
The demo uses two werkzeug method `pop_path_info` and `peek_path_info` that
were removed in werkzeug 2.3.0 release that were deprecated in 2.2.0. These
methods are used by the IQR Search Dispatcher that generates the link for
each IQR instance `smqtk/smqtk_iqr/web/search_app/__init__.py`.

The `ingest_precomputed_descriptors.py` script is used to generate the
descriptor set without calling the methods in one of the descriptor generator
modules. Using the PrePopulatedDescriptorGenerator class, the descriptor set
is generated from a manifest file that contains the paths to the image files
and the corresponding descriptor files. The manifest file is created by the
chip_images_demo.py script that generates image chips from kwcoco images and
builds dummy descriptor files.


This will require geowatch:

pip install geowatch
geowatch finish_install

Workaround issue by installing specific versions
pip install flask==2.0.1 werkzeug==2.0.0

Also need the faiss library to be installed
pip install faiss-cpu

Install Mongo:
https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/

curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
  --dearmor

  echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

  sudo apt-get install -y mongodb-org
  sudo systemctl start mongod

This script should be run from inside the tutorial directory. E.g. on the
developers machine this looks like:

.. code:: bash

    cd $HOME/code/smqtk-repos/SMQTK-IQR/docs/tutorials/tutorial_002_kwcoco_real_descriptors
'

# Choose a working directory where we can write data
WORKING_DIRECTORY=$HOME/.cache/smqtk_iqr/demo/tutorial_002_data

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
kwcoco toydata vidshapes2-frames10-amazon --bundle_dpath "$KWCOCO_SPLITS_DPATH"/vidshapes_rgb_train
kwcoco toydata vidshapes4-frames10-amazon --bundle_dpath "$KWCOCO_SPLITS_DPATH"/vidshapes_rgb_vali
kwcoco toydata vidshapes2-frames6-amazon --bundle_dpath "$KWCOCO_SPLITS_DPATH"/vidshapes_rgb_test


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
        batch_size           : 3
    model:
        class_path: MultimodalTransformer
        init_args:
            name        : ToyRGB_Demo_V001
            arch_name   : smt_it_stm_p8
            global_box_weight: 1
    optimizer:
      class_path: torch.optim.AdamW
      init_args:
        lr: 3e-4
        weight_decay: 3e-5
    trainer:
      default_root_dir     : $TRAINING_ROOT_DIR
      accelerator          : $ACCELERATOR
      devices              : 1
      #devices              : 0,
      max_steps: 32
      num_sanity_val_steps: 0
      limit_val_batches    : 2
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
"

if [[ "$ACCELERATOR" == "gpu" ]]; then
    PREDICT_DEVICE_ARGS=(--devices="0,")
else
    PREDICT_DEVICE_ARGS=()
fi

# ---------------------------------------------------------------------------
# Perform the predict operation to generate the hidden layer descriptors
# and build the kwcoco dataset for IQR
python -m geowatch.tasks.fusion.predict \
    --test_dataset="$TEST_FPATH" \
    --package_fpath="$PACKAGE_FPATH"  \
    --with_hidden_layers=True  \
    --pred_dataset="$PREDICT_OUTPUT_FPATH" \
     "${PREDICT_DEVICE_ARGS[@]}"


# ---------------------------------------------------------------------------
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
    --tab "GEOWATCH_DEMO"


echo "
Step 6
------
Ensure MongoDB is running
"
# NOTE: depending on versions of mongo version 3.x for Ubuntu 20.04 is the
# above command and 7.x for Ubuntu 22.04
mongo_20_04_startup(){
    sudo systemctl start mongodb
    sudo systemctl status mongodb --no-pager

    # 4. check the status of the service
    mongo --eval "db.getMongo()"
    # Should have message:
    # connecting to: mongodb://127.0.0.1:27017
    # 'smqtk' database will be created when the IQR service is run the first time.
    # Enter a mongo shell, to view available databases:
    mongo
    show dbs
    mongo --eval "show dbs"
}

mongo_22_04_startup(){
    sudo systemctl start mongod
    sudo systemctl status mongod --no-pager
    # 4. check the status of the service
    mongosh --eval "db.getMongo()"
    # Should have message:
    # connecting to: mongodb://127.0.0.1:27017
    # 'smqtk' database will be created when the IQR service is run the first time.
    # Enter a mongo shell, to view available databases:
    mongosh --eval "show dbs"
}

if lsb_release -a | grep "Ubuntu 20.04" ; then
    mongo_20_04_startup
else
    # Assume the commands on 22.04 will work on later versions
    mongo_22_04_startup
fi


echo "
Step 7
------
Run the IQR search dispatcher and IQR service from the same directory.
"
# Following script provides commands to run in two tmux sessions
COMMAND="runApplication -v -a IqrService -c runApp.IqrRestService.json"
SESSION_ID="SMQTK-IQR-SERVICE"
tmux kill-session -t "$SESSION_ID" 2> /dev/null || true
tmux new-session -d -s "$SESSION_ID" "bash"
tmux send -t "$SESSION_ID" "$COMMAND" Enter

COMMAND="runApplication -v -a IqrSearchDispatcher -c runApp.IqrSearchApp.json"
SESSION_ID="SMQTK-IQR-SEARCH-DISPATCHER"
tmux kill-session -t "$SESSION_ID" 2> /dev/null || true
tmux new-session -d -s "$SESSION_ID" "bash"
tmux send -t "$SESSION_ID" "$COMMAND" Enter

# 6. Open a web-browser and navigate to 'localhost:5000'
python -c "import webbrowser; webbrowser.open('127.0.0.1:5000')"

echo "
THE FOLLOWING ARE MANUAL STEPS THE USER MUST TAKE.

7. In the web-browser, select 'GEOWATCH_DEMO' IQR instance

8. Both username and password are set to 'demo' by config files

9. You may now interact with the IQR web interface.
"

## Appendix:  If you want to perform step 5 in separate terminals, run:
#runApplication -a IqrService \
#-c runApp.IqrRestService.json

## In second terminal run the IQRsearch dispatcher
#runApplication -a IqrSearchDispatcher -c runApp.IqrSearchApp.json
