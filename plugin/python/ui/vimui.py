import ui.interface
import vim
import log

class Ui(ui.interface.Ui):
    """Ui layer which manages the Vim windows.
    """

    def open(self):
        if self.is_open:
            return
        self.is_open = True
        vim.command('silent tabnew')
        
        srcwin_name = self.__get_srcwin_name()

        self.tabnr = vim.eval("tabpagenr()")

        logwin = LogWindow(self,'rightbelow 4new')
        log.Log.set_logger(log.WindowLogger(\
                log.Logger.DEBUG,\
                logwin))

        self.watchwin = WatchWindow(self,'vertical belowright new')
        self.watchwin.create()

        self.stackwin = StackWindow(self,'belowright 6new')
        self.stackwin.create()

        self.statuswin = StatusWindow(self,'belowright 3new')
        self.statuswin.create()
        self.statuswin.set_status("Monkey")

        winnr = self.__get_srcwinno_by_name(srcwin_name)
        self.sourcewin = SourceWindow(self,winnr)

    def get_current_file(self):
        return vim.current.buffer.name

    def get_current_row(self):
        return vim.current.window.cursor[0]

    def place_breakpoint(self,sign_id,file,line):
        vim.command('sign place '+str(sign_id)+\
                ' name=breakpt line='+str(line)+\
                ' file='+file)

    def remove_breakpoint(self,sign_id):
        log.Log("Removing breakpoint sign ID %i " % sign_id)
        vim.command('sign unplace '+str(sign_id))

    def __get_srcwin_name(self):
        return vim.windows[0].buffer.name

    def __get_srcwinno_by_name(self,name):
        i = 1
        for w in vim.windows:
            if w.buffer.name == name:
                break
            else:
                i += 1
        return i

    def say(self,string):
        """ Vim picks up Python prints, so just print """
        print string

    def error(self,string):
        vim.command('echohl Error | echo "'+string+'" | echohl None')

    def close(self):
        if not self.is_open:
            return
        self.is_open = False

        if self.sourcewin:
            self.sourcewin.clear_signs()

        self.watchwin.destroy()
        self.stackwin.destroy()
        self.statuswin.destroy()

        log.Log.shutdown()

        vim.command('silent! '+self.tabnr+'tabc!')

        self.watchwin = None
        self.stackwin = None

class SourceWindow(ui.interface.Window):

    file = None
    pointer_sign_id = '6145'
    breakpoint_sign_id = '6146'

    def __init__(self,ui,winno):
        self.winno = str(winno)

    def focus(self):
        vim.command(self.winno+"wincmd w")

    def command(self,cmd,silent = True):
        self.focus()
        prepend = "silent " if silent else ""
        command_str = prepend + self.winno + "wincmd " + cmd
        #print "Executing command: '"+command_str+"'"
        vim.command(command_str)

    def set_file(self,file):
        if file.startswith("file://"):
            file = file[7:]
        self.file = file
        log.Log("Setting source file: "+file,log.Logger.DEBUG)
        self.focus()
        vim.command("silent edit " + file)

    def clear_signs(self):
        vim.command('sign unplace *')


    def place_pointer(self,line):
        log.Log("Placing pointer sign on line "+str(line))
        vim.command('sign unplace '+self.pointer_sign_id)
        vim.command('sign place '+self.pointer_sign_id+\
                ' name=current line='+str(line)+\
                ' file='+self.file)


class Window(ui.interface.Window):
    name = "WINDOW"
    open_cmd = "new"

    def __init__(self,ui,open_cmd):
        self.firstwrite = 1
        self.buffer = None
        self.ui = ui
        self.open_cmd = open_cmd

    def getwinnr(self):
        return int(vim.eval("bufwinnr('"+self.name+"')"))

    def write(self, msg):
        """ append last """
        """if type(msg) is unicode:
          msg =
          unicodedata.normalize('NFKD',msg).encode('ascii','ignore')"""
        if self.buffer_empty():
            self.buffer[:] = str(msg).split('\n')
        else:
            self.buffer.append(str(msg).split('\n'))
        self.command('normal G')
        #self.window.cursor = (len(self.buffer), 1)

    def insert(self, msg, lineno = None, overwrite = False, allowEmpty = False):
        """ insert into current position in buffer"""
        if len(msg) == 0 and allowEmpty == False:
            return
        if self.buffer_empty():
            self.buffer[:] = str(msg).split('\n')
        else:
            if lineno == None:
                (lineno, rol) = vim.current.window.cursor
            remaining_buffer = str(msg).split('\n')
            if overwrite:
                lfrom = lineno + 1
            else:
                lfrom = lineno
            remaining_buffer.extend(self.buffer[lfrom:])
            del self.buffer[lineno:]
            if self.buffer_empty():
                self.buffer[:] = remaining_buffer
            else:
                for line in remaining_buffer:
                    self.buffer.append(line)

    def buffer_empty(self):
        if len(self.buffer) == 1 \
                and len(self.buffer[0]) == 0:
            return True
        else:
            return False

    def create(self):
        """ create window """
        vim.command('silent ' + self.open_cmd + ' ' + self.name)
        #if self.name != 'LOG___WINDOW':
        vim.command("setlocal buftype=nofile")
        self.buffer = vim.current.buffer
        self.width  = int( vim.eval("winwidth(0)")  )
        self.height = int( vim.eval("winheight(0)") )
        self.is_open = True
        self.on_create()

    def destroy(self):
        """ destroy window """
        if self.buffer == None or len(dir(self.buffer)) == 0:
            return
        #if self.name == 'LOG___WINDOW':
        #  self.command('hide')
        #else:
        self.command('bwipeout ' + self.name)
        self.firstwrite = 1

    def clean(self):
        """ clean all datas in buffer """
        self.buffer[:] = []
        self.firstwrite = 1

    def command(self, cmd):
        """ go to my window & execute command """
        winnr = self.getwinnr()
        if winnr != int(vim.eval("winnr()")):
            vim.command(str(winnr) + 'wincmd w')
        vim.command(cmd)

class LogWindow(Window):
    name = "LOG_WINDOW"

class StackWindow(Window):
    name = "STACK_WINDOW"

class WatchWindow(Window):
    name = "WATCH_WINDOW"

class StatusWindow(Window):
    name = "STATUS_WINDOW"

    def on_create(self):
        self.write("Status: \n<F5> Run")

    def set_status(self,status):
        self.insert("Status: "+str(status),0,True)

