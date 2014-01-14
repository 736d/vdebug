import vdebug.connection
import vdebug.opts
import vim

class Listener:

    def __init__(self):
        self.__server = vdebug.connection.SocketServer()

    def start(self):
        if vdebug.opts.Options.get("auto_start", bool):
            vim.command('au CursorHold * python debugger.start_if_ready()')
            vim.command('au CursorMoved * python debugger.start_if_ready()')
        self.__server.start(vdebug.opts.Options.get('server'),
                            vdebug.opts.Options.get('port',int))

    def stop(self):
        if vdebug.opts.Options.get("auto_start", bool):
            vim.command('au! CursorHold *')
            vim.command('au! CursorMoved *')
        self.__server.stop()

    def status(self):
        if not self.__server:
            return "inactive"
        if self.is_ready():
            return "ready"
        elif self.__server.is_alive():
            return "listening"
        else:
            return "inactive"

    def is_ready(self):
        return self.__server.has_socket()

    def is_listening(self):
        return not self.is_ready() and self.__server.is_alive()

    def create_connection(self):
        handler = vdebug.connection.ConnectionHandler(*self.__server.socket())
        self.stop()
        return handler
