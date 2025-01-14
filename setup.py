import sys

from setuptools import setup

install_requires = [ 'JPype1 ; python_version > "2.7" and platform_python_implementation != "Jython"',
                     'JPype1<=0.7.1 ; python_version <= "2.7" and platform_python_implementation != "Jython"',
                    ]

setup(
    name = 'jaydebeapi-hsqldb',
    version = '0.0.3',
    author = 'Pebble94464',
    author_email = 'jaydebeapi-hsqldb@pebble.plus.com',
    license = 'MIT License',
    url='https://github.com/pebble94464/jaydebeapi-hsqldb',
    description=('A module for connecting to HyperSQL using JDBC, based on JayDeBeApi'),
	long_description=open('README.rst').read(),
    long_description_content_type="text/x-rst",
    keywords = ('hypersql hsqldb jdbc'),
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],

    packages=['jaydebeapi_hsqldb'],
    install_requires=install_requires,
    )
