import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from uuid import uuid4

from harness import __main__ as cli
from harness import recover


class RecoverTest(unittest.TestCase):
    def test_confirmation_required_before_changes(self):
        with patch.object(recover, 'recover') as execute, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                cli.main(['recover', str(uuid4())])
        self.assertEqual(exc.exception.code, 2)
        execute.assert_not_called()

    def test_confirmed_dispatch(self):
        run_id = uuid4()
        with patch.object(recover, 'recover', return_value=1) as execute, redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['recover', str(run_id), '--worker-stopped']), 0)
        execute.assert_called_once_with(run_id)

    def test_unknown_run(self):
        with patch.object(recover, 'recover', side_effect=LookupError('Прогон не найден')), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['recover', str(uuid4()), '--worker-stopped']), 1)


if __name__ == '__main__':
    unittest.main()
