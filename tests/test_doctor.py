import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from harness import __main__ as cli
from harness import doctor


class DoctorTest(unittest.TestCase):
    def test_checks_report_and_exit_status(self):
        output = io.StringIO()
        with patch.object(doctor, '_database', return_value='ok'), patch.object(doctor, '_broker', return_value='ok'), patch.object(doctor, '_model', side_effect=RuntimeError('no key')), patch.object(doctor, '_docker', return_value='ok'), patch.object(doctor, '_disk', return_value='ok'), redirect_stdout(output):
            self.assertEqual(doctor.main([]), 1)
        self.assertIn('[ERROR] Модель: no key', output.getvalue())
        self.assertEqual(output.getvalue().count('[OK]'), 4)

    def test_cli_dispatch_preserves_original_parser(self):
        with patch.object(doctor, 'main', return_value=7) as run:
            self.assertEqual(cli.main(['doctor', '--manifest', 'x']), 7)
            run.assert_called_once_with(['--manifest', 'x'])
        with patch.object(cli, 'run', return_value={'subtype': 'success', 'result': 'ok', 'messages': []}) as run, redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['-p', 'hello']), 0)
            self.assertEqual(run.call_args.args[0], 'hello')


if __name__ == '__main__':
    unittest.main()
