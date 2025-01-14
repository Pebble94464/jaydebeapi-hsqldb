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

Alternatively the module can be downloaded from its repository on GitHub:

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

Getting Started
===============
The code example found in this section is provided as a quick hint on how to 
connect to a HyperSQL server.  You will need to update the parameters passed to 
the connect method to reflect your system's configuration.

The 'jclassname' parameter, a.k.a. classpath, should be set to HyperSQL's
JDBCDriver class, i.e. 'org.hsqldb.jdbc.JDBCDriver'

The 'url' parameter will depend on your HyperSQL server's configuration.
This can be fairly complex, and rather explain it here I'll direct you to the
`JDBCConnection <http://hsqldb.org/doc/2.0/apidocs/org.hsqldb/org/hsqldb/jdbc/JDBCConnection.html>`_
documentation on hsqldb.org

The 'driver_args' parameter can be a sequence or dictionary, as described in
the documentation for the jaydebeapi.connect method.

The 'jars' parameter needs to include the location of your HSQLDB jar file,

.. code-block:: python

	import jaydebeapi_hsqldb as jaydebeapi

	jclassname = 'org.hsqldb.jdbc.JDBCDriver'		# driver path
	url = 'jdbc:hsqldb:hsql://localhost/db1'		# connection string
	driver_args = ['SA', '']						# username and password
	jars = ('/PROGS/HSQLDB/hsqldb-osgi-jdk8.jar',)	# location of HSQLDB jar

	try:
		conn = jaydebeapi.connect(
			jclassname,
			url,
			driver_args,
			jars
		)
		curs = conn.cursor()
		curs.execute('VALUES(DATABASE_VERSION())')
		version = curs.fetchone()[0]
		print(f'\nSuccessfully connected!\nHSQLDB version: {version}\n')
		curs.close()
		conn.close()
	except Exception as e:
		# Connection failed...
		print(f'\n{repr(e)}\n{str(e)}\n')

Troubleshooting
---------------

This project was coded and tested on a 64-bit Windows system. It should work on 
other platforms too, but you may find the code examples and docs need adapting.

If you're struggling to get jaydebeapi-hsqldb working, here are a few things you can try:

* Avoid mixing 32-bit and 64-bit software components
* If the Java Runtime Environment (JRE) is not automatically detected you may need to add 'JAVA_HOME' or 'JRE_HOME' to your environment variables.
* If you suspect a permissions issue, try installing and running with an administrator account.
* If you suspect a firewall issue, temporarily disable the firewall to see if this is the case.
* If you suspect some other configuration issue, ensure all paths specified are correct. Use back slashes or forward slashes as appropriate for your OS. Do they need escaping?

* Submit a question via StackOverflow!
	It's quite possible others have already encountered the same issue and SO can
	often provide a quick response. Tag your question with an appropriate tag, such
	as 'jaydebeapi-hsqldb', which I can then monitor.

If you think you've found a bug please feel welcome to submit a report via GitHub:

* `jaydebeapi-hsqldb issues <https://github.com/Pebble94464/jaydebeapi-hsqldb/issues>`_

Known Issues
============
- This release contains debug code and may halt unexpectedly when new datatypes are encountered.

Changelog
---------
	0.0.3	Added support for more data types.
	0.0.1	Initial release.


