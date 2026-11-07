"""Regression for impossible market trades in the human interface."""

from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

from hamurabi.__main__ import play


class PlayTest(unittest.TestCase):
    def test_impossible_trade_does_not_display_a_negative_granary(self):
        output = StringIO()
        with patch('builtins.input', side_effect=['999', 'q']) as ask, redirect_stdout(output):
            play('steady', 101)
        prompts = [call.args[0] for call in ask.call_args_list]
        self.assertTrue(all('Acres to trade' in text for text in prompts), prompts)
        self.assertIn('Trade must be between -20 and 20 acres.', output.getvalue())
        self.assertNotIn('After trade:', output.getvalue())
