Installing MongoDB
------------------

This gives a minimal set of instructions for how to install and setup MongoDB
Community Edition on Ubuntu machines.


For a more detailed tutorial see:

    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/


On Ubuntu 22.04 run:

.. code:: bash

    sudo apt-get install gnupg curl

    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
      sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
      --dearmor

    # Print OS Info
    lsb_release -a

    # Point to the correct package repo depending on the OS
    if lsb_release -a 2> /dev/null | grep "Ubuntu 20.04" ; then
        echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    elif lsb_release -a 2> /dev/null | grep "Ubuntu 22.04" ; then
        echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    else
        echo "Unsupported Ubuntu Version"
    fi

    sudo apt-get update
    sudo apt-get install -y mongodb-org

    # Start the mongo service
    sudo systemctl start mongod

    # Check the status of the service
    systemctl status mongod --no-pager

    # Test the service works by attempting to interact with it
    mongosh --eval "db.getMongo()"
    # Should have message:
    # connecting to: mongodb://127.0.0.1:27017

    # View available databases:
    mongosh --eval "show dbs"
