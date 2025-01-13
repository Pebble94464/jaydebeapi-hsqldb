#-*- coding: utf-8 -*-

# Copyright 2010-2015 Bastian Bowe
#
# This file is part of JayDeBeApi.
# JayDeBeApi is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# JayDeBeApi is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with JayDeBeApi.  If not, see
# <http://www.gnu.org/licenses/>.

__version_info__ = (1, 2, 3)
__version__ = ".".join(str(i) for i in __version_info__)

import datetime
import decimal
import glob
import os
import time
import re
import sys
import warnings
import jpype

PY2 = sys.version_info[0] == 2

if PY2:
    # Ideas stolen from the six python 2 and 3 compatibility layer
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")
else:
    def reraise(tp, value, tb=None):
        if value is None:
            value = tp()
        else:
            value = tp(value)
        if tb:
            raise value.with_traceback(tb)
        raise value

if PY2:
    assert 'basestring' in __builtins__, 'This version of Python 2.x is missing type basestring.'
    string_type = __builtins__.get('basestring', str)
else:
    string_type = str

# Mapping from java.sql.Types attribute name to attribute value
_jdbc_name_to_const = None

# Mapping from java.sql.Types attribute constant value to it's attribute name
_jdbc_const_to_name = None

_jdbc_connect = None

_java_array_byte = None

_handle_sql_exception = None

old_jpype = False

def _handle_sql_exception_jython():
    from java.sql import SQLException
    exc_info = sys.exc_info()
    if isinstance(exc_info[1], SQLException):
        exc_type = DatabaseError
    else:
        exc_type = InterfaceError
    reraise(exc_type, exc_info[1], exc_info[2])

def _jdbc_connect_jython(jclassname, url, driver_args, jars, libs):
    if _jdbc_name_to_const is None:
        from java.sql import Types
        types = Types
        types_map = {}
        const_re = re.compile('[A-Z][A-Z_]*$')
        for i in dir(types):
            if const_re.match(i):
                types_map[i] = getattr(types, i)
        _init_types(types_map)
    global _java_array_byte
    if _java_array_byte is None:
        import jarray
        def _java_array_byte(data):
            return jarray.array(data, 'b')
    # register driver for DriverManager
    jpackage = jclassname[:jclassname.rfind('.')]
    dclassname = jclassname[jclassname.rfind('.') + 1:]
    # print jpackage
    # print dclassname
    # print jpackage
    from java.lang import Class
    from java.lang import ClassNotFoundException
    try:
        Class.forName(jclassname).newInstance()
    except ClassNotFoundException:
        if not jars:
            raise
        _jython_set_classpath(jars)
        Class.forName(jclassname).newInstance()
    from java.sql import DriverManager
    if isinstance(driver_args, dict):
        from java.util import Properties
        info = Properties()
        for k, v in driver_args.items():
            info.setProperty(k, v)
        dargs = [ info ]
    else:
        dargs = driver_args
    return DriverManager.getConnection(url, *dargs)

def _jython_set_classpath(jars):
    '''
    import a jar at runtime (needed for JDBC [Class.forName])

    adapted by Bastian Bowe from
    http://stackoverflow.com/questions/3015059/jython-classpath-sys-path-and-jdbc-drivers
    '''
    from java.net import URL, URLClassLoader
    from java.lang import ClassLoader
    from java.io import File
    m = URLClassLoader.getDeclaredMethod("addURL", [URL])
    m.accessible = 1
    urls = [File(i).toURL() for i in jars]
    m.invoke(ClassLoader.getSystemClassLoader(), urls)

def _prepare_jython():
    global _jdbc_connect
    _jdbc_connect = _jdbc_connect_jython
    global _handle_sql_exception
    _handle_sql_exception = _handle_sql_exception_jython

def _handle_sql_exception_jpype():
    SQLException = jpype.java.sql.SQLException
    exc_info = sys.exc_info()
    if old_jpype:
        clazz = exc_info[1].__javaclass__
        db_err = issubclass(clazz, SQLException)
    else:
        db_err = isinstance(exc_info[1], SQLException)
    if db_err:
        error_code = exc_info[1].getErrorCode()
        if isinstance(exc_info[1], (
            jpype.java.sql.SQLIntegrityConstraintViolationException, # -104
            )):
            exc_type = IntegrityError
            assert old_jpype == False, "This code block is untested against older versions of jpype"
        else:
            exc_type = DatabaseError
    else:
        exc_type = InterfaceError
        
    reraise(exc_type, exc_info[1], exc_info[2])

def _jdbc_connect_jpype(jclassname, url, driver_args, jars, libs):
    import jpype
    if not jpype.isJVMStarted():
        args = []
        class_path = []
        if jars:
            class_path.extend(jars)
        class_path.extend(_get_classpath())
        if class_path:
            args.append('-Djava.class.path=%s' %
                        os.path.pathsep.join(class_path))
        if libs:
            # path to shared libraries
            libs_path = os.path.pathsep.join(libs)
            args.append('-Djava.library.path=%s' % libs_path)
        # jvm_path = ('/usr/lib/jvm/java-6-openjdk'
        #             '/jre/lib/i386/client/libjvm.so')
        jvm_path = jpype.getDefaultJVMPath()
        global old_jpype
        if hasattr(jpype, '__version__'):
            try:
                ver_match = re.match('\d+\.\d+', jpype.__version__)
                if ver_match:
                    jpype_ver = float(ver_match.group(0))
                    if jpype_ver < 0.7:
                        old_jpype = True
            except ValueError:
                pass
        if old_jpype:
            jpype.startJVM(jvm_path, *args)
        else:
            jpype.startJVM(jvm_path, *args, ignoreUnrecognized=True,
                           convertStrings=True)
    if not jpype.isThreadAttachedToJVM():
        jpype.attachThreadToJVM()
        jpype.java.lang.Thread.currentThread().setContextClassLoader(jpype.java.lang.ClassLoader.getSystemClassLoader())
    if _jdbc_name_to_const is None:
        types = jpype.java.sql.Types
        types_map = {}
        if old_jpype:
          for i in types.__javaclass__.getClassFields():
            const = i.getStaticAttribute()
            types_map[i.getName()] = const
        else:
          for i in types.class_.getFields():
            if jpype.java.lang.reflect.Modifier.isStatic(i.getModifiers()):
              const = i.get(None)
              types_map[i.getName()] = const 
        _init_types(types_map)
    global _java_array_byte
    if _java_array_byte is None:
        def _java_array_byte(data):
            return jpype.JArray(jpype.JByte, 1)(data)
    # register driver for DriverManager
    jpype.JClass(jclassname)
    if isinstance(driver_args, dict):
        Properties = jpype.java.util.Properties
        info = Properties()
        for k, v in driver_args.items():
            info.setProperty(k, v)
        dargs = [ info ]
    else:
        dargs = driver_args
    return jpype.java.sql.DriverManager.getConnection(url, *dargs)

def _get_classpath():
    """Extract CLASSPATH from system environment as JPype doesn't seem
    to respect that variable.
    """
    try:
        orig_cp = os.environ['CLASSPATH']
    except KeyError:
        return []
    expanded_cp = []
    for i in orig_cp.split(os.path.pathsep):
        expanded_cp.extend(_jar_glob(i))
    return expanded_cp

def _jar_glob(item):
    if item.endswith('*'):
        return glob.glob('%s.[jJ][aA][rR]' % item)
    else:
        return [item]

def _prepare_jpype():
    global _jdbc_connect
    _jdbc_connect = _jdbc_connect_jpype
    global _handle_sql_exception
    _handle_sql_exception = _handle_sql_exception_jpype

if sys.platform.lower().startswith('java'):
    _prepare_jython()
else:
    _prepare_jpype()

apilevel = '2.0'
threadsafety = 1
paramstyle = 'qmark'
# TODO: verify correct threadsafety setting for HSQLDB

class DBAPITypeObject(object):
    _mappings = {}
    def __init__(self, *values):
        """Construct new DB-API 2.0 type object.
        values: Attribute names of java.sql.Types constants"""
        self.values = values
        for type_name in values:
            if type_name in DBAPITypeObject._mappings:
                raise ValueError("Non unique mapping for type '%s'" % type_name)
            DBAPITypeObject._mappings[type_name] = self
    def __cmp__(self, other):
        # Python 3 deprecates this method and uses __eq__ and __ne__ instead.
        if other in self.values:
            return 0
        if other < self.values:
            return 1
        else:
            return -1
    def __hash__(self):
        return super().__hash__()
    def __eq__(self, other):
        return other in self.values
    def __ne__(self, other):
        return other not in self.values

    def __lt__(self, other):
        raise NotImplementedError('###: DBAPITypeObject.__lt__')
        return ((self.last, self.first) < (other.last, other.first))

    def __le__(self, other):
        raise NotImplementedError('###: DBAPITypeObject.__le__')
        return ((self.last, self.first) <= (other.last, other.first))

    def __gt__(self, other):
        raise NotImplementedError('###: DBAPITypeObject.__gt__')
        return ((self.last, self.first) > (other.last, other.first))

    def __ge__(self, other):
        raise NotImplementedError('###: DBAPITypeObject.__ge__')
        return ((self.last, self.first) >= (other.last, other.first))

    def __repr__(self):
        return 'DBAPITypeObject(%s)' % ", ".join([repr(i) for i in self.values])
    @classmethod
    def _map_jdbc_type_to_dbapi(cls, jdbc_type_const):
        try:
            type_name = _jdbc_const_to_name[jdbc_type_const]
        except KeyError:
            warnings.warn("Unknown JDBC type with constant value %d. "
                          "Using None as a default type_code." % jdbc_type_const)
            return None
        try:
            return cls._mappings[type_name]
        except KeyError:
            warnings.warn("No type mapping for JDBC type '%s' (constant value %d). "
                          "Using None as a default type_code." % (type_name, jdbc_type_const))
            return None


STRING = DBAPITypeObject('CHAR', 'NCHAR', 'NVARCHAR', 'VARCHAR', 'OTHER')

TEXT = DBAPITypeObject('CLOB', 'LONGVARCHAR', 'LONGNVARCHAR', 'NCLOB', 'SQLXML')

BINARY = DBAPITypeObject('BINARY', 'BLOB', 'LONGVARBINARY', 'VARBINARY')

NUMBER = DBAPITypeObject('BOOLEAN', 'BIGINT', 'BIT', 'INTEGER', 'SMALLINT',
                         'TINYINT')

FLOAT = DBAPITypeObject('FLOAT', 'REAL', 'DOUBLE')

DECIMAL = DBAPITypeObject('DECIMAL', 'NUMERIC')

DATE = DBAPITypeObject('DATE')

TIME = DBAPITypeObject('TIME', 'TIME_WITH_TIMEZONE')

DATETIME = DBAPITypeObject('TIMESTAMP', 'TIMESTAMP_WITH_TIMEZONE')

ROWID = DBAPITypeObject('ROWID')

# DB-API 2.0 Module Interface Exceptions
class Error(Exception):
    pass

class Warning(Exception):
    pass

class InterfaceError(Error):
    pass

class DatabaseError(Error):
    pass

class InternalError(DatabaseError):
    pass

class OperationalError(DatabaseError):
    pass

class ProgrammingError(DatabaseError):
    pass

class IntegrityError(DatabaseError):
    pass

class DataError(DatabaseError):
    pass

class NotSupportedError(DatabaseError):
    pass

# DB-API 2.0 Type Objects and Constructors

if True:
    # The original code...
    def _java_sql_blob(data):
        return _java_array_byte(data)

    Binary = _java_sql_blob
else:
    # Unsure why the original code is indirect. Wouldn't this be better?
    def Binary(data):
        """This function constructs an object capable of holding a binary (long) string value."""
        return _java_array_byte(data)

    Binary = _java_sql_blob

# "construct individual SQL types"...

def Date(year, month, day):
    """This function constructs an object holding a date value.

    Params:
        year: int
        month: int
        day: int

    Returns:
        java.sql.Date object
    """
    return jpype.JClass('java.sql.Date')(year - 1900, month - 1, day)

def Time(hour, minute, second):
    """This function constructs an object holding a time value.
	
    Params:
        hour: int
        minute: int
        second: int

    Returns:
        java.sql.Time object
    """
    return jpype.JClass('java.sql.Time')(hour, minute, second)

def Timestamp(year, month, day, hour, minute, second, nano=0):
    """This function constructs an object holding a timestamp value.

    Parameters:
        year: int
        month: int
        day: int
        hour: int
        minute: int
        second: int
        nano: int     # Optional. Not part of the DBAPI 2 specification.

    Returns:
        java.sql.Timestamp object
    """
    return jpype.JClass('java.sql.Timestamp')(year - 1900, month - 1, day, hour, minute, second, nano)
# TODO: write tests for Timestamps with nanoseconds

def DateFromTicks(ticks):
    """
    This function constructs an object holding a date value from the given
    ticks value (number of seconds since the epoch; see the documentation of
    the standard Python time module for details).
    """
    (year, month, day) = time.localtime(ticks)[:3]
    return Date(year, month, day)

def TimeFromTicks(ticks):
    """
    This function constructs an object holding a time value from the given
    ticks value (number of seconds since the epoch; see the documentation of
    the standard Python time module for details).
    """
    (hour, minute, second) = time.localtime(ticks)[3:6]
    return Time(hour, minute, second)

def TimestampFromTicks(ticks):
    """
    This function constructs an object holding a timestamp value from the
    given ticks value (number of seconds since the epoch; see the documentation
    of the standard Python time module for details).
    """
    (year, month, day, hour, minute, second) = time.localtime(ticks)[:6]
    return Timestamp(year, month, day, hour, minute, second)


# DB-API 2.0 Module Interface connect constructor
def connect(jclassname, url, driver_args=None, jars=None, libs=None):
    """Open a connection to a database using a JDBC driver and return
    a Connection instance.

    jclassname: Full qualified Java class name of the JDBC driver.
    url: Database url as required by the JDBC driver.
    driver_args: Dictionary or sequence of arguments to be passed to
           the Java DriverManager.getConnection method. Usually
           sequence of username and password for the db. Alternatively
           a dictionary of connection arguments (where `user` and
           `password` would probably be included). See
           http://docs.oracle.com/javase/7/docs/api/java/sql/DriverManager.html
           for more details
    jars: Jar filename or sequence of filenames for the JDBC driver
    libs: Dll/so filenames or sequence of dlls/sos used as shared
          library by the JDBC driver
    """
    if isinstance(driver_args, string_type):
        driver_args = [ driver_args ]
    if not driver_args:
       driver_args = []
    if jars:
        if isinstance(jars, string_type):
            jars = [ jars ]
    else:
        jars = []
    if libs:
        if isinstance(libs, string_type):
            libs = [ libs ]
    else:
        libs = []
    jconn = _jdbc_connect(jclassname, url, driver_args, jars, libs)
    return Connection(jconn, _converters)

# DB-API 2.0 Connection Object
class Connection(object):

    Error = Error
    Warning = Warning
    InterfaceError = InterfaceError
    DatabaseError = DatabaseError
    InternalError = InternalError
    OperationalError = OperationalError
    ProgrammingError = ProgrammingError
    IntegrityError = IntegrityError
    DataError = DataError
    NotSupportedError = NotSupportedError

    def __init__(self, jconn, converters):
        self.jconn = jconn
        self._closed = False
        self._converters = converters

    def close(self):
        if self._closed:
            raise Error()
        self.jconn.close()
        self._closed = True

    def commit(self):
        try:
            self.jconn.commit()
        except:
            _handle_sql_exception()

    def rollback(self):
        try:
            self.jconn.rollback()
        except:
            _handle_sql_exception()

    def cursor(self):
        return Cursor(self, self._converters)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# DB-API 2.0 Cursor Object
class Cursor(object):

    rowcount = -1
    _meta = None
    _prep = None
    _rs = None
    _description = None

    def __init__(self, connection, converters):
        self._connection = connection
        self._converters = converters

    @property
    def description(self):
        if self._description:
            return self._description
        m = self._meta
        if m:
            count = m.getColumnCount()
            self._description = []
            for col in range(1, count + 1):
                size = m.getColumnDisplaySize(col)
                jdbc_type = m.getColumnType(col) # jsn: call to java function
                # WIP: why isn't JDBCResultSetMetaData.getColumnType returning the correct code for an integer?
                if jdbc_type not in (
                    -5, 	# 'BIGINT'
                    1, 		# 'CHARACTER'
                    4, 		# 'INTEGER'
                    5, 		# 'SMALLINT'
                    12,		# 'VARCHAR'
                    16, 	# 'BOOLEAN'
                    91, 	# 'DATE'
                    92,		# 'TIME'
                    93, 	# 'TIMESTAMP'
                    2004, 	# 'BLOB'
                    ):
                    print('### jdbc_type: ', str(jdbc_type))
                    # breakpoint() #- check jdbc_type
                    # TODO: remove above block of code
                if jdbc_type == 0:
                    # PEP-0249: SQL NULL values are represented by the
                    # Python None singleton
                    dbapi_type = None
                else:
                    dbapi_type = DBAPITypeObject._map_jdbc_type_to_dbapi(jdbc_type)
                col_desc = ( m.getColumnName(col),
                             dbapi_type,
                             size,
                             size,
                             m.getPrecision(col),
                             m.getScale(col),
                             m.isNullable(col),
                             )
                self._description.append(col_desc)
            return self._description

#   optional callproc(self, procname, *parameters) unsupported

    def close(self):
        self._close_last()
        self._connection = None

    def _close_last(self):
        """Close the resultset and reset collected meta data.
        """
        if self._rs:
            self._rs.close()
        self._rs = None
        if self._prep:
            self._prep.close()
        self._prep = None
        self._meta = None
        self._description = None

    def _to_java_type(self, value): # jsn
        """ Converts certain Python types to Java type, but not all types."""
        if type(value) is datetime.time and value.tzinfo != None:
            value = jpype.java.time.OffsetTime@value
        elif type(value) is datetime.time:
            value = jpype.java.sql.Time@value
        elif type(value) is datetime.datetime and value.tzinfo != None:
            value = jpype.java.time.OffsetDateTime@value
        elif type(value) is datetime.datetime:
            value = jpype.java.sql.Timestamp@value
        elif type(value) is datetime.date:
            value = jpype.java.sql.Date@value
        # if not isinstance(value, (str, jpype.JObject)):
        #     breakpoint() #- check type Jobject?
        return value

    def _set_stmt_parms(self, prep_stmt, parameters):
        for i in range(len(parameters)):
            value = self._to_java_type(parameters[i]) # Try to convert to a Java type.

            if value is not None and not isinstance(value, (str, int,
                                      jpype.JArray(jpype.JByte),	# <java class 'byte[]'>
                                      jpype.java.sql.Date,
                                      jpype.java.sql.Time,
                                      jpype.java.sql.Timestamp,
                                      float, #- detected while experimenting with _yfinance_pandas.py
                                      )):
                print('### previously unseen type: ', type(value))
                # breakpoint() #-
            # TODO: remove code block once all types have been discovered and tested.

            if value is None:
                prep_stmt.setNull(i + 1, 0)  # java.sql.Types.NULL
            elif isinstance(value, jpype.java.sql.Time):
                prep_stmt.setTime(i + 1, value)
            elif isinstance(value, jpype.java.sql.Date):
                prep_stmt.setDate(i + 1, value)
            elif isinstance(value, jpype.java.sql.Timestamp):
                prep_stmt.setTimestamp(i + 1, value)
            elif type(value) is jpype.JArray(jpype.JByte):
                prep_stmt.setBytes(i + 1, value)
                # TODO: is it quicker to call isinstance or type()?
            #- elif type(value) is int:
            #-     prep_stmt.setInt(i + 1, jpype.JInt(value))
            else:
                prep_stmt.setObject(i + 1, value)
    # TODO: Optimise code. Is it faster to call setObject on everything and just let Java sort it out?

    def execute(self, operation, parameters=None):
        if self._connection._closed:
            raise Error()
        if not parameters:
            parameters = ()
        self._close_last()
        self._prep = self._connection.jconn.prepareStatement(operation)
        self._set_stmt_parms(self._prep, parameters)
        try:
            is_rs = self._prep.execute()
        except:
            _handle_sql_exception()
        if is_rs:
            self._rs = self._prep.getResultSet()
            self._meta = self._rs.getMetaData()
            self.rowcount = -1
        else:
            self.rowcount = self._prep.getUpdateCount()
        # self._prep.getWarnings() ???

    def executemany(self, operation, seq_of_parameters):
        self._close_last()
        self._prep = self._connection.jconn.prepareStatement(operation)
        for parameters in seq_of_parameters:
            self._set_stmt_parms(self._prep, parameters)
            self._prep.addBatch()
        update_counts = self._prep.executeBatch()
        # self._prep.getWarnings() ???
        self.rowcount = sum(update_counts)
        self._close_last()

    def fetchone(self):
        if not self._rs:
            raise Error()
        if not self._rs.next():
            return None
        row = []
        for col in range(1, self._meta.getColumnCount() + 1):
            sqltype = self._meta.getColumnType(col)
            converter = self._converters.get(sqltype, _unknownSqlTypeConverter)
            v = converter(self._rs, col)
            row.append(v)
        return tuple(row)

    def fetchmany(self, size=None):
        if not self._rs:
            raise Error()
        if size is None:
            size = self.arraysize
        # TODO: handle SQLException if not supported by db
        self._rs.setFetchSize(size)
        rows = []
        row = None
        for i in range(size):
            row = self.fetchone()
            if row is None:
                break
            else:
                rows.append(row)
        # reset fetch size
        if row:
            # TODO: handle SQLException if not supported by db
            self._rs.setFetchSize(0)
        return rows

    def fetchall(self):
        rows = []
        while True:
            row = self.fetchone()
            if row is None:
                break
            else:
                rows.append(row)
        return rows

    # optional nextset() unsupported

    arraysize = 1

    def setinputsizes(self, sizes):
        pass

    def setoutputsize(self, size, column=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def _unknownSqlTypeConverter(rs, col):
    if True:
        print('#### Unknown type encountered ####')
        md = rs.getMetaData()
        print('  table name:\t', md.getTableName(col))
        print('  column name:\t', md.getColumnName(col))
        print('  type code:\t', md.getColumnType(col))
        print('  type name:\t', md.getColumnTypeName(col))
        raise NotSupportedError('Unknown type code encountered')
    return rs.getObject(col)
# TODO: log an error message for unexpected type, don't block.

def _to_datetime(rs, col) -> datetime.datetime:
    """Convert java.sql.Timestamp to datetime.datetime"""
    value = rs.getTimestamp(col)
    if value is None:
        return value
    assert isinstance(value, jpype.java.sql.Timestamp), 'Expecting a java.sql.Timestamp object'
    year = value.getYear() + 1900
    month = value.getMonth() + 1
    day = value.getDate()
    hours = value.getHours()
    minutes = value.getMinutes()
    seconds = value.getSeconds()
    microseconds = int(value.getNanos() / 1000)
    return datetime.datetime(year, month, day, hours, minutes, seconds, microseconds)

def _to_datetime_with_timezone(rs, col) -> datetime.datetime:
    """Convert java.time.OffsetDateTime to datetime.datetime"""
    value = rs.getObject(col)
    if value == None:
        return value
    assert isinstance(value, jpype.java.time.OffsetDateTime), 'expecting a java.time.OffsetDateTime object'
    year = value.getYear()
    month = value.getMonthValue()
    day = value.getDayOfMonth()
    hour = value.getHour()
    minute = value.getMinute()
    second = value.getSecond()
    microsecond = int(value.getNano() / 1000)
    zone_offset = value.getOffset() # <java class 'java.time.ZoneOffset'>
    offset_seconds = zone_offset.getTotalSeconds()
    tzinfo1 = datetime.timezone(datetime.timedelta(seconds=offset_seconds))
    return datetime.datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo1)

def _jtime_to_ptime(t):
    """Convert java.sql.Time to datetime.time"""
    def func(rs, col) -> datetime.time:
        """Convert java.sql.Time to datetime.time"""
        value = rs.getTime(col) # <java class 'java.sql.Time'>
        if value == None:
            return
        assert isinstance(value, jpype.java.sql.Time), 'All work and no play makes Jack a dull boy'
        hours = value.getHours()
        minutes = value.getMinutes()
        seconds = value.getSeconds()
        microseconds = value.getTime() % 1000 * 1000
        return datetime.time(hours, minutes, seconds, microseconds)
    return func

def _to_time_with_timezone(rs, col) -> datetime.time:
    """Convert java.time.OffsetTime to datetime.datetime"""
    # rs is-a <java class 'org.hsqldb.jdbc.JDBCResultSet'>
    value = rs.getObject(col)  # Should return a java.time.OffsetTime
    if value == None:
        return
    assert isinstance(value, jpype.java.time.OffsetTime), 'Expecting a java.time.OffsetTime object'
    hour = value.getHour()
    minute = value.getMinute()
    second = value.getSecond()
    microsecond = int(value.getNano() / 1000)
    zone_offset = value.getOffset() # <java class 'java.time.ZoneOffset'>
    offset_seconds = zone_offset.getTotalSeconds()
    tzinfo1 = datetime.timezone(datetime.timedelta(seconds=offset_seconds))
    return datetime.time(hour, minute, second, microsecond, tzinfo=tzinfo1)

def _jdate_to_pdate(t):
    """Convert java.sql.date to datetime.date"""
    def func(rs, col) -> datetime.date:
        """Convert java.sql.date to datetime.date"""
        value = rs.getDate(col)
        if value == None:
            return
        assert isinstance(value, jpype.java.sql.Date), 'Expecting java.sql.Date object'
        year = value.getYear() + 1900
        month = value.getMonth() + 1
        day = value.getDate()
        return datetime.date(year, month, day)
    return func

def _jbinary_to_pbytes(t):
    ''' Convert Java byte array to Python bytes '''
    def func(rs, col: int) -> bytes:
        # obj = rs.getObject(col) # <java class 'byte[]'>
        # ctn = rs.getMetaData().getColumnTypeName(col) # e.g. 'BINARY'
        value = rs.getBytes(col)    # <java array 'byte[]'>
        assert value != None #- The original code had a check for None, but was it's necessary?
        return bytes(value)
    return func

def _varbinary_to_bytes(t):
    ''' Convert VARBINARY to Python bytes '''
    # convert VARBINARY to bytes. Call rs.getBytes(col)
    def func(rs, col: int) -> bytes:
        value = rs.getBytes(col)    # <java array 'byte[]'>
        return bytes(value)        # <class 'bytes'>
    return func

def _boolean_to_bool(t):
    '''Convert Java Boolean to Python bool'''
    def func(rs, col):
        #- ctn = rs.getMetaData().getColumnTypeName(col) # 'BIT' or 'BOOLEAN'
        #- SQLAlchemy's BooleanTest::test_null fails unless we return None when the Java object is None.
        #- pytest -rP -x --db hsqldb test/test_suite.py::BooleanTest::test_null
        value = rs.getObject(col) # <java class 'java.lang.Boolean'> or None
        if value is None:
            return
        return rs.getBoolean(col) # getBoolean returns <class 'bool'>
    return func

def _blob_to_bytes(t):
    def func(rs, col):
        blob = rs.getBlob(col) # <java class 'org.hsqldb.jdbc.JDBCBlobClient'>
        length = blob.length() # <java class 'JLong'>
        data = blob.getBytes(1, int(length)) # <java array 'byte[]'>
        return bytes(data)
    return func
    # TODO: investigate using blob.getBinaryStream instead of blob.getBytes. Should be more efficient.

def _jchar_to_pstr(t):
    '''Convert Java char to Python char''' # aka CHARACTER.
    def func(rs, col) -> str:
        value = rs.getString(col) # str or None
        assert(isinstance(value, str) or value is None)
        return value
    return func
    # TODO: This converter executed for CHARACTER eventhough CHARACTER is not in the _DEFAULT_CONVERTERS dictionary. Why?

def _clob_to_string(t):
    def func(rs, col) -> str:
        clob = rs.getClob(col) # <java class 'org.hsqldb.jdbc.JDBCClobClient'>
        length = clob.length() # <java class 'JLong'>
        data = clob.getSubString(1, int(length)) # <class 'str'>
        # TODO: investigate using clob.getcharacterStream instead of clob.getSubString. Should be more efficient.
        return data
    return func

def _jbigdecimal_to_pdecimal(t):
    '''Convert Java BigDecimal to Python Decimal'''
    def func(rs, col):
        # o = rs.getObject(col) # getObject returns <java class 'java.math.BigDecimal'>
        # column_type_name = rs.getMetaData().getColumnTypeName(col) # e.g. 'DECIMAL' or 'NUMERIC'
        bd = rs.getBigDecimal(col) # java.math.BigDecimal
        plain_string = bd.toPlainString()
        decimalObject = decimal.Decimal(plain_string) # returns <class 'decimal.Decimal'>
        return decimalObject
    return func

def _jdouble_to_pfloat(t: str) -> callable:
    '''Convert Java double to Python double'''
    def func(rs, col) -> float:
        #- o = rs.getObject(col) # getObject returns <java class 'java.lang.Double'>
        column_type_name = rs.getMetaData().getColumnTypeName(col) # 'DOUBLE'
        assert column_type_name == 'DOUBLE' # Not expecting to see 'FLOAT' or 'REAL' because they are converted to 'DOUBLE' by HSQLDB.
        return float(rs.getDouble(col)) # getDouble returns <java class 'JDouble'>, so cast as Python float
        # JPype.dbapi2 calls rs.getFloat(col) when converting a REAL, but we'll stick with getDouble because that's what HSQLDB uses to store REALs
    return func

def _jlong_to_pint(t):
    '''Convert Java long to Python int'''
    def func(rs, col):
        #- o = rs.getObject(col) # getObject returns <java class 'java.lang.Long'>
        java_object = rs.getLong(col) # getLong returns <java class 'JLong'>
        return int(java_object)
    return func

def _jint_to_pint(t):
    '''Convert Java int to Python int'''
    def func(rs, col):
        return rs.getInt(col)
    return func
# SMALLINT is a signed 16-bit integer in the range -32,768 to 32,767.
# TINYINT is a signed 8-bit integer in the range is -128 to 127.
# md.getColumnClassName returns 'java.lang.Integer'
# rs.getObject(col) returns a java.lang.Integer object
# JPype converts java.lang.Integer to Python int, although it does this using a call to rs.getShort.

#- pytest -rP -x --db hsqldb test/test_suite.py::BooleanTest::test_whereclause


# column_name = md.getColumnName(1)                # 'ABC'
# column_type = md.getColumnType(1)                # -6
# is_signed = md.isSigned(1)                    # True
# column_class_name = md.getColumnClassName(1)     # 'java.lang.Integer'
# column_type_name = md.getColumnTypeName(1)    # 'TINYINT'

# TODO: What to convert VARBINARY to? Check what JPype returns for VARBINARY.
#- Converter methods translate Java types to Python types. (Adapters convert Python types to Java types.)
def _varbinary_to_bytes(t):
    ''' Convert VARBINARY to Python bytes '''
    # convert VARBINARY to bytes. Call rs.getBytes(col)
    def func(rs, col: int) -> bytes:
        value = rs.getBytes(col)    # <java array 'byte[]'>
        assert(isinstance(value, jpype.JArray(jpype.JByte)) or value is None)
        if value is not None:
            value = bytes(value)
        return value
    return func
# jpype.dbapi2 converts JDBC type VARBINARY to Python type bytes.
# Python bytearray objects are a mutable counterpart to bytes objects.

def _varchar_to_str(t):
    ''' Convert VARCHAR to str '''
    def func(rs, col):
        value = rs.getString(col) # str or None, not a java.lang.String object
        assert(isinstance(value, str) or value is None)
        return value
    return func

#---- Assignment of converter methods to global variables...

# WIP: _to_array...
def _to_array(t):
    def func(rs, col):
        raise NotImplementedError
        o = rs.getObject(col) # getObject returns <java class 'org.hsqldb.jdbc.JDBCArray'>
        column_type_name = rs.getMetaData().getColumnTypeName(col) # 'BLOB'
        md = rs.getMetaData()
        jdbc_array = rs.getArray(col) # <java class 'org.hsqldb.jdbc.JDBCArray'>
        base_type = jdbc_array.getBaseType() # 4
        base_type_name = jdbc_array.getBaseTypeName() # 'INTEGER'
        conversion_func = _DEFAULT_CONVERTERS[base_type_name]
        breakpoint() #-
        return None
    return func
_to_array = _to_array('ARRAY')
# https://hsqldb.org/doc/2.0/apidocs/org.hsqldb/org/hsqldb/jdbc/JDBCArray.html
# Note SQLAlchemy's array tests are currently skipped.

"""
(Pdb) arr2 = arr.getArray()  # <java array 'java.lang.Object[]'>
(Pdb) repr(arr2)
"<java array 'java.lang.Object[]'>"
len(arr2) # 3
(Pdb) i1 = arr2[0]
(Pdb) type(i1) # <java class 'java.lang.Integer'>

(Pdb) md2 = rs2.getMetaData() # <java class 'org.hsqldb.jdbc.JDBCResultSetMetaData'>
(Pdb) md2.getColumnCount() # 2

Pdb) curs = Cursor(None, _DEFAULT_CONVERTERS)
(Pdb) repr(curs)
'<jaydebeapi_hsqldb.Cursor object at 0x000002697E0946D0>'
(Pdb) curs._meta = md2
curs._rs = rs2
"""

_bigint_to_int = _jlong_to_pint('BIGINT')
_binary_to_bytes = _jbinary_to_pbytes('BINARY')
_bit_to_bool = _boolean_to_bool('BIT')
_blob_to_pbytes = _blob_to_bytes('BLOB')
_boolean_to_bool = _boolean_to_bool('BOOLEAN')
_to_char = _jchar_to_pstr('CHAR')
_to_clob = _clob_to_string('CLOB')
_double_to_float = _jdouble_to_pfloat('DOUBLE')
_float_to_float = _jdouble_to_pfloat('FLOAT')
_real_to_float = _jdouble_to_pfloat('REAL')
_integer_to_int = _jint_to_pint('INTEGER')
_decimal_to_decimal = _jbigdecimal_to_pdecimal('DECIMAL')
_numeric_to_decimal = _jbigdecimal_to_pdecimal('NUMERIC')
_smallint_to_int = _jint_to_pint('SMALLINT')
_to_date = _jdate_to_pdate('DATE')
_to_time = _jtime_to_ptime('TIME')
_to_time_with_timezone = _to_time_with_timezone
_to_datetime = _to_datetime
_to_datetime_with_timezone = _to_datetime_with_timezone
_tinyint_to_int = _jint_to_pint('TINYINT')
_varbinary_to_bytes = _varbinary_to_bytes('VARBINARY')
_varchar_to_str = _varchar_to_str('VARCHAR')
# TODO: Some assignments above are to functions while others are to function calls. Make consistent.

def _init_types(types_map):
    global _jdbc_name_to_const
    _jdbc_name_to_const = types_map
    global _jdbc_const_to_name
    _jdbc_const_to_name = dict((y,x) for x,y in types_map.items())
    _init_converters(types_map)

def _init_converters(types_map):
    """Prepares the converters for conversion of java types to python
    objects.
    types_map: Mapping of java.sql.Types field name to java.sql.Types
    field constant value"""
    global _converters
    _converters = {}
    for i in _DEFAULT_CONVERTERS:
        const_val = types_map[i]
        _converters[const_val] = _DEFAULT_CONVERTERS[i]

# Mapping from java.sql.Types field to converter method
_converters = None

# The dictionary below uses the names of java.sql.Types constants as keys.
_DEFAULT_CONVERTERS = {
    'ARRAY': _to_array,
    'BIGINT': _bigint_to_int,
    'BINARY': _binary_to_bytes,
    'BIT': _bit_to_bool,
    'BLOB': _blob_to_pbytes,
    'BOOLEAN': _boolean_to_bool,
    'CHAR': _to_char, # aka CHARACTER
    'CLOB': _to_clob,
    'DATALINK': _unknownSqlTypeConverter,
    'DATE': _to_date,
    'DECIMAL': _decimal_to_decimal,
    'DISTINCT': _unknownSqlTypeConverter, # Not a datatype

    # HSQLDB stores FLOAT, DOUBLE, and REAL as a Java Double object, so the
    # mapping for FLOAT and REAL below can probably be ignored.
    'DOUBLE': _double_to_float,
    'FLOAT': _float_to_float,    # Map to double instead?
    'INTEGER': _integer_to_int,
    'JAVA_OBJECT': _unknownSqlTypeConverter,

    # HSQLDB uses Unicode strings internally, so N character data types are
    # possibly redundant.
    'LONGNVARCHAR': _unknownSqlTypeConverter, # N
    'LONGVARBINARY': _unknownSqlTypeConverter, # N
    'LONGVARCHAR': _unknownSqlTypeConverter, # N
    'NCHAR': _unknownSqlTypeConverter, # N
    'NCLOB': _unknownSqlTypeConverter, # N
    'NULL': _unknownSqlTypeConverter, # NULL type columns don't exist.
    'NUMERIC': _numeric_to_decimal,
    'NVARCHAR': _unknownSqlTypeConverter, # N
    'OTHER': _unknownSqlTypeConverter,
    'REAL': _real_to_float, # Map to double instead?
    'REF_CURSOR': _unknownSqlTypeConverter,
    'REF': _unknownSqlTypeConverter,
    'ROWID': _unknownSqlTypeConverter,
    'SMALLINT': _smallint_to_int,
    'SQLXML': _unknownSqlTypeConverter,
    'STRUCT': _unknownSqlTypeConverter,

    # TIME_WITH_TIMEZONE and TIMESTAMP_WITH_TIMEZONE are the names of constant
    # integers defined in jpype.java.sql.Types.  The actual names used in SQL
    # statements include an additional space, e.g. 'TIME WITH TIME ZONE'.
    'TIME_WITH_TIMEZONE': _to_time_with_timezone,
    'TIME': _to_time,
    'TIMESTAMP_WITH_TIMEZONE': _to_datetime_with_timezone,
    'TIMESTAMP': _to_datetime,
    'TINYINT': _tinyint_to_int,
    'VARBINARY': _varbinary_to_bytes,
    'VARCHAR': _varchar_to_str
}
# TODO: remove NULL and DISTINCT from the _DEFAULT_CONVERTERS dictionary.

class JvmTimezone:
    _dst_savings = None
    _raw_offset = None

    @staticmethod
    def _initialize():
        JTimeZone = jpype.JClass('java.util.TimeZone', False)
        # Get the default TimeZone of the Java virtual machine...
        zone_info = JTimeZone.getDefault() # <java class 'sun.util.calendar.ZoneInfo'>
        JvmTimezone._raw_offset = zone_info.getRawOffset()
        JvmTimezone._dst_savings = zone_info.getDSTSavings()
        del zone_info

    @staticmethod
    def get_offset():
        if JvmTimezone._raw_offset == None:
            JvmTimezone._initialize()
        assert JvmTimezone._raw_offset != None
        return JvmTimezone._raw_offset

    @staticmethod
    def get_dst_savings():
        if JvmTimezone._dst_savings == None:
            JvmTimezone._initialize()
        assert JvmTimezone._dst_savings != None
        return JvmTimezone._dst_savings

