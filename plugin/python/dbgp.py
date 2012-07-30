import xml.etree.ElementTree as ET
import socket
import log

""" Response objects for the DBGP module."""

class Response:
    """Contains response data from a command made to the debugger."""

    def __init__(self,response,cmd,cmd_args):
        self.response = response
        self.cmd = cmd
        self.cmd_args = cmd_args
        self.xml = None
        if "<error" in self.response:
            self.__parse_error()

    def __parse_error(self):
        """Parse an error message which has been returned
        in the response, then raise it as a DBGPError."""
        xml = self.as_xml()
        err_el = xml.find('error')
        code = err_el.get("code")
        if code is None:
            raise ResponseError(
                    "Missing error code in response",
                    self.response)
        msg_el = err_el.find('message')
        if msg_el is None:
            raise ResponseError(
                    "Missing error message in response",
                    self.response)
        raise DBGPError(msg_el.text,code)

    def get_cmd(self):
        """Get the command that created this response."""
        return self.cmd

    def get_cmd_args(self):
        """Get the arguments to the command."""
        return self.cmd_args

    def as_string(self):
        """Return the full response as a string.
        
        There is a __str__ method, which will render the
        whole object as a string and should be used for
        displaying.
        """
        return self.response

    def as_xml(self):
        """Get the response as element tree XML.

        Returns an xml.etree.ElementTree.Element object.
        """
        if self.xml == None:
            self.xml = ET.fromstring(self.response)
        return self.xml

    def __str__(self):
        return self.as_string()

class StatusResponse(Response):
    """Response object returned by the status command."""

    def __str__(self):
        return self.as_xml().get('status')

class FeatureGetResponse(Response):
    """Response object specifically for the feature_get command."""

    def is_supported(self):
        """Whether the feature is supported or not."""
        xml = self.as_xml()
        return int(xml.get('supported'))

    def __str__(self):
        if self.is_supported():
            xml = self.as_xml()
            return xml.text
        else:
            return "* Feature not supported *"

class Api:
    """Api for eBGP commands.

    Uses a Connection object to read and write with the debugger,
    and builds commands and returns the results.
    """

    conn = None
    transID = 0

    def __init__(self,connection,exp_idekey = None):
        """Create a new Api using a Connection object.

        The Connection object specifies the debugger connection,
        and the Protocol provides a OO api to interacting
        with it.

        connection -- The Connection object to use
        """
        self.language = None
        self.protocol = None
        self.exp_idekey = exp_idekey
        self.idekey = None
        self.startfile = None
        self.conn = connection
        if self.conn.isconnected() == 0:
            self.conn.open()
        self.__parse_init_msg(self.conn.recv_msg())
        
    def __parse_init_msg(self,msg):
        """Parse the init message from the debugger"""
        xml = ET.fromstring(msg)
        self.language = xml.get("language")
        if self.language is None:
            raise ResponseError(
                "Invalid XML response from debugger",
                msg)

        self.idekey = xml.get("idekey")
        if self.exp_idekey is not None:
            if self.idekey != self.exp_idekey:
                raise WrongIDEKeyException()
        self.version = xml.get("api_version")
        self.startfile = xml.get("fileuri")

    def send_cmd(self,cmd,args = '',
            res_cls = Response):
        """Send a command to the debugger.

        This method automatically adds a unique transaction
        ID to the command which is required by the debugger.

        Returns a Response object, which contains the
        response message and command.

        cmd -- the command name, e.g. 'status'
        args -- arguments for the command, which is optional 
                for certain commands (default '')
        """
        args = args.strip()
        send = cmd.strip()
        self.transID += 1
        send += ' -i '+ str(self.transID)
        if len(args) > 0:
            send += ' ' + args
        log.Log("Command: "+send,\
                log.Logger.DEBUG)
        self.conn.send_msg(send)
        msg = self.conn.recv_msg()
        log.Log("Response: "+msg,\
                log.Logger.DEBUG)
        return res_cls(msg,cmd,args)

    def status(self):
        """Get the debugger status.
        
        Returns a Response object.
        """
        return self.send_cmd('status','',StatusResponse)

    def feature_get(self,name):
        """Get the value of a feature from the debugger.

        See the DBGP documentation for a list of features.
        
        Returns a FeatureGetResponse object.
        
        name -- name of the feature, e.g. encoding
        """
        return self.send_cmd(
                'feature_get',
                '-n '+str(name),
                FeatureGetResponse)

    def feature_set(self,name,value):
        """Set the value of a debugger feature.

        See the DBGP documentation for a list of features.
        
        Returns a Response object.
        
        name -- name of the feature, e.g. encoding
        value -- new value for the feature
        """
        return self.send_cmd(
                'feature_set',
                '-n ' + str(name) + ' -v ' + str(value))

    def run(self):
        """Tell the debugger to start or resume
        execution."""
        return self.send_cmd('run','',StatusResponse)

    def step_into(self):
        """Tell the debugger to step to the next
        statement.
        
        If there's a function call, the debugger engine
        will break on the first statement in the function.
        """
        return self.send_cmd('step_into','',StatusResponse)

    def step_over(self):
        """Tell the debugger to step to the next
        statement.
        
        If there's a function call, the debugger engine
        will stop at the next statement after the function call.
        """
        return self.send_cmd('step_over','',StatusResponse)

    def step_out(self):
        """Tell the debugger to step out of the statement.
        
        The debugger will step out of the current scope.
        """
        return self.send_cmd('step_out','',StatusResponse)

    def stop(self):
        """Tell the debugger to stop execution.

        The script is terminated immediately."""
        return self.send_cmd('stop','',StatusResponse)

    def stack_get(self):
        """Get the stack information.
        """
        return self.send_cmd('stack_get','',StatusResponse)

    def detach(self):
        """Tell the debugger to detach itself from this
        client.

        The script is not terminated, but runs as normal
        from this point."""
        return self.send_cmd('detach','',StatusResponse)

    def breakpoint_set(self,cmd_args):
        return self.send_cmd('breakpoint_set',cmd_args,Response)


class WrongIDEKeyException(Exception):
    """An exception raised when the debugger session key is
    different to the expected one."""
    pass


"""Connection module for managing a socket connection
between this client and the debugger."""

class Connection:
    """DBGP connection class, for managing the connection to the debugger.

    The host, port and socket timeout are configurable on object construction.
    """

    sock = None
    address = None
    isconned = 0

    def __init__(self, host = '', port = 9000, timeout = 30):
        """Create a new Connection.

        The connection is not established until open() is called.

        host -- host name where debugger is running (default '')
        port -- port number which debugger is listening on (default 9000)
        timeout -- time in seconds to wait for a debugger connection before giving up (default 30)
        """
        self.port = 9000
        self.host = host
        self.timeout = timeout

    def __del__(self):
        """Make sure the connection is closed."""
        self.close()

    def isconnected(self):
        """Whether the connection has been established."""
        return self.isconned

    def open(self):
        """Listen for a connection from the debugger.

        The socket is blocking, and it will wait for the length of
        time given by the timeout (default is 30 seconds).
        """
        print 'Waiting for a connection (this message will self-destruct in ',self.timeout,' seconds...)'
        serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serv.settimeout(self.timeout)
            serv.bind((self.host, self.port))
            serv.listen(5)
            (self.sock, self.address) = serv.accept()
            self.sock.settimeout(None)
        except socket.timeout:
            serv.close()
            raise TimeoutError,"Timeout waiting for connection"

        self.isconned = 1
        serv.close()

    def close(self):
        """Close the connection."""
        if self.sock != None:
            self.sock.close()
            self.sock = None
        self.isconned = 0

    def __recv_length(self):
        """Get the length of the proceeding message."""
        length = ''
        while 1:
            c = self.sock.recv(1)
            if c == '':
                self.close()
                raise EOFError, 'Socket Closed'
            if c == '\0':
                return int(length)
            if c.isdigit():
                length = length + c

    def __recv_null(self):
        """Receive a null byte."""
        while 1:
            c = self.sock.recv(1)
            if c == '':
                self.close()
                raise EOFError, 'Socket Closed'
            if c == '\0':
                return

    def __recv_body(self, to_recv):
        """Receive a message of a given length.

        to_recv -- length of the message to receive
        """
        body = ''
        while to_recv > 0:
            buf = self.sock.recv(to_recv)
            if buf == '':
                self.close()
                raise EOFError, 'Socket Closed'
            to_recv -= len(buf)
            body = body + buf
        return body

    def recv_msg(self):
        """Receive a message from the debugger.
        
        Returns a string, which is expected to be XML.
        """
        length = self.__recv_length()
        body     = self.__recv_body(length)
        self.__recv_null()
        return body

    def send_msg(self, cmd):
        """Send a message to the debugger.

        cmd -- command to send
        """
        self.sock.send(cmd + '\0')

class TimeoutError(Exception):
    pass


""" Errors/Exceptions """

class DBGPError(Exception):
    """Raised when the debugger returns an error message."""
    pass

class ResponseError(Exception):
    """An error caused by an unexpected response from the
    debugger (e.g. invalid format XML)."""
    pass

error_codes = { \
    # 000 Command parsing errors
    0   : """no error""",\
    1   : """parse error in command""",\
    2   : """duplicate arguments in command""", \
    3   : """invalid options (ie, missing a required option)""",\
    4   : """Unimplemented command""",\
    5   : """Command not available (Is used for async commands. For instance if the engine is in state "run" than only "break" and "status" are available). """,\
    # 100 : File related errors
    100 : """can not open file (as a reply to a "source" command if the requested source file can't be opened)""",\
    101 : """stream redirect failed """,\
    # 200 Breakpoint, or code flow errors
    200 : """breakpoint could not be set (for some reason the breakpoint could not be set due to problems registering it)""",\
    201 : """breakpoint type not supported (for example I don't support 'watch' yet and thus return this error)""",\
    202 : """invalid breakpoint (the IDE tried to set a breakpoint on a line that does not exist in the file (ie "line 0" or lines past the end of the file)""",\
    203 : """no code on breakpoint line (the IDE tried to set a breakpoint on a line which does not have any executable code. The debugger engine is NOT required to """     + \
          """return this type if it is impossible to determine if there is code on a given location. (For example, in the PHP debugger backend this will only be """         + \
          """returned in some special cases where the current scope falls into the scope of the breakpoint to be set)).""",\
    204 : """Invalid breakpoint state (using an unsupported breakpoint state was attempted)""",\
    205 : """No such breakpoint (used in breakpoint_get etc. to show that there is no breakpoint with the given ID)""",\
    206 : """Error evaluating code (use from eval() (or perhaps property_get for a full name get))""",\
    207 : """Invalid expression (the expression used for a non-eval() was invalid) """,\
    # 300 Data errors
    300 : """Can not get property (when the requested property to get did not exist, this is NOT used for an existing but uninitialized property, which just gets the """    + \
          """type "uninitialised" (See: PreferredTypeNames)).""",\
    301 : """Stack depth invalid (the -d stack depth parameter did not exist (ie, there were less stack elements than the number requested) or the parameter was < 0)""",\
    302 : """Context invalid (an non existing context was requested) """,\
    # 900 Protocol errors
    900 : """Encoding not supported""",\
    998 : """An internal exception in the debugger occurred""",\
    999 : """Unknown error """\
}

