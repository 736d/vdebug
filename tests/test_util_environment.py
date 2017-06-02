if __name__ == "__main__":
    import sys
    sys.path.append('pythonx')
import unittest
from mock import MagicMock, patch
import vdebug.util

class EnvironmentTest(unittest.TestCase):
    def test_reload_evals_options(self):
        new_options = {"foo": "bar"}
        options = MagicMock()
        options.isset = MagicMock(return_value=False)
        with patch('vim.eval', MagicMock(return_value=new_options)) as vimeval:
            vdebug.util.Environment.reload(options)
            vimeval.assert_called_once_with("g:vdebug_options")
        options.set.assert_called_once_with(new_options)
