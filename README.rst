=================================================================
jaydebeapi-hsqldb
=================================================================
This project is based on `JayDeBeApi <https://github.com/baztian/jaydebeapi/>`_
and contains modifications to support
`sqlalchemy-hsqldb <https://github.com/Pebble94464/sqlalchemy-hsqldb.git>`_, 
an SQLAlchemy dialect for HyperSQL 2.0.

Installation
------------

A package for installing jaydebeapi-hsqldb from `pypi.org <https://pypi.org/>`_
will soon be available 
To install jaydebeapi-hsqldb from pypi.org, open a command prompt and type:

.. code-block:: sh

	pip install jaydebeapi-hsqldb

Alternatively the dialect and its driver can be downloaded from its repository
on GitHub:

`jaydebeapi-hsqldb repository <https://github.com/Pebble94464/jaydebeapi-hsqldb.git>`_

Use the 'pip install <path>' syntax to install, where <path> points to where
your local copy is installed, e.g.

.. code-block:: sh

	pip install ./jaydebeapi-hsqldb

Post-install Configuration
--------------------------
Your system needs to know where the Java Runtime Environment is. If not
detected automatically you may need to add 'JAVA_HOME' or 'JRE_HOME' to your
environment variables.

.. code-block:: sh

	set "JAVA_HOME=C:\Program Files\Java\jre-1.8\bin"

The jaydebeapi-hsqldb module also needs to know where HyperSQL's JAR file is
located. At the moment this can be specified using another environment
variable named 'CLASSPATH', (but this method of specifing the location will
likely change in a future release). For example, on Windows...
.. code-block:: sh

	set "CLASSPATH=/some_folder/hsqldb-osgi-jdk8.jar"

Getting Started
===============
[TODO: code example to follow]

If you find jaydebeapi-hsqldb useful for other applications besides SQLAlchemy
please feel welcome to let me know :-)

Known Issues
============
- This release still contains debug code and halts when new datatypes are encountered.
