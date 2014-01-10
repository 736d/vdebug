import vdebug.event
import vdebug.listener
import vdebug.session
import vdebug.util
import vdebug.breakpoint
import vdebug.ui.vimui
import vim

class DebuggerInterface:
    """Provides all methods used to control the debugger."""
    def __init__(self):
        self.listener = vdebug.listener.Listener()
        self.event_dispatcher = vdebug.event.Dispatcher()
        breakpoints = vdebug.breakpoint.Store()
        self.ui = vdebug.ui.vimui.Ui(breakpoints)
        self.__reload_environment()

        self.session = vdebug.session.Session(self.ui,
                breakpoints,
                vdebug.util.Keymapper())

    def __del__(self):
        self.session.close()
        self.session = None

    def status(self):
        if self.session.is_connected():
            return "running"
        else:
            return self.listener.status()

    def status_for_statusline(self):
        return "vdebug(%s)" % self.status()

    def start_if_ready(self):
        if not self.session.is_connected() and self.listener.is_ready():
            return True
        else:
            return False

    def listen(self):
        if self.listener.is_listening():
            print "Already waiting for a connection: none found so far"
        elif self.listener.is_ready():
            print "Found connection, starting debugger"
            self.session.start(self.listener.create_connection())
        else:
            print "Vdebug will wait for a connection in the background"
            if self.session.is_open():
                self.session.ui().statuswin.set_status("listening")
            self.__reload_environment()
            self.listener.start()

    def run(self):
        """Tell the debugger to run, until the next breakpoint or end of script.
        """
        if self.session.is_connected():
            self.session.dispatch_event("run")
        else:
            self.listen()

    def run_to_cursor(self):
        """Run to the current VIM cursor position.
        """
        self.session.dispatch_event("run_to_cursor")

    def step_over(self):
        """Step over to the next statement.
        """
        self.session.dispatch_event("step_over")

    def step_into(self):
        """Step into a statement on the current line.
        """
        self.session.dispatch_event("step_into")

    def step_out(self):
        """Step out of the current statement.
        """
        self.session.dispatch_event("step_out")

    def handle_opt(self,option,value = None):
        """Set an option, overwriting the existing value.
        """
        if value is None:
            return self.ui.say(vdebug.opts.Options.get(option))
        else:
            self.ui.say("Setting vdebug option '%s' to: %s"\
                                %(option,value))
            vim.command('let g:vdebug_options["%s"] = "%s"' %(option,value))
            return vdebug.opts.Options.overwrite(option,value)

    def handle_return_keypress(self):
        """React to a <enter> keypress event.
        """
        return self.event_dispatcher.by_position(self.session)

    def handle_double_click(self):
        """React to a mouse double click event.
        """
        return self.event_dispatcher.by_position(self.session)

    def handle_visual_eval(self):
        """React to eval during visual selection.
        """
        return self.event_dispatcher.visual_eval(self.session)

    def handle_eval(self,args):
        """Evaluate a code snippet specified by args.
        """
        return self.session.dispatch_event("eval", args)

    def eval_under_cursor(self):
        """Evaluate the property under the cursor.
        """
        return self.event_dispatcher.eval_under_cursor(self.session)

    def toggle_breakpoint_window(self):
        """Open or close the breakpoint window.

        The window appears as a horizontal split below the
        currently selected window."""
        if self.session.ui().breakpointwin.is_open:
            self.session.ui().breakpointwin.destroy()
        else:
            self.session.ui().breakpointwin.create()

    def toggle_status_window(self):
        """Open or close the status window.

        The window appears as a horizontal split below the
        currently selected window."""
        if self.session.ui().statuswin.is_open:
            self.session.ui().statuswin.destroy()
        else:
            self.session.ui().statuswin.create()


    def set_breakpoint(self,args = None):
        """Set a breakpoint, specified by args.
        """
        self.session.dispatch_event("set_breakpoint", args)

    def remove_breakpoint(self,args = None):
        """Remove one or more breakpoints, specified by args.
        """
        self.session.dispatch_event("remove_breakpoint", args)

    def get_context(self):
        """Get all the variables in the default context
        """
        self.session.get_context()

    def detach(self):
        """Detach the debugger, so the script runs to the end.
        """
        self.session.detach()

    def close(self):
        """Close the connection, or the UI if already closed.
        """
        if self.session.is_connected():
            self.session.close_connection()
        elif self.session.is_open():
            self.session.close()
        else:
            self.listener.stop()

    def __reload_environment(self):
        vdebug.util.Environment.reload()
