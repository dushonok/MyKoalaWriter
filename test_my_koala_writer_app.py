"""
Unit tests for MyKoalaWriterApp UI behaviour.
"""

import os
import sys
import tkinter as tk
import unittest
from unittest.mock import patch

# Ensure project modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from my_koala_writer_app import MyKoalaWriterApp


class TestMyKoalaWriterAppButtonState(unittest.TestCase):
    """Verify button state respects feature flag."""

    def _build_app(self, flag_value):
        root = tk.Tk()
        root.withdraw()
        patcher = patch('my_koala_writer_app.ENABLE_ADD_WP_IMGS_BUTTON', flag_value)
        patcher.start()
        try:
            app = MyKoalaWriterApp(root, test_mode=True)
        except Exception:
            patcher.stop()
            root.destroy()
            raise
        return root, app, patcher

    def test_add_wp_imgs_button_enabled_when_flag_true(self):
        root, app, patcher = self._build_app(True)
        try:
            self.assertEqual(app.add_wp_imgs_btn.cget('state'), tk.NORMAL)
            app.disable_all_buttons()
            app.enable_all_buttons()
            self.assertEqual(app.add_wp_imgs_btn.cget('state'), tk.NORMAL)
        finally:
            patcher.stop()
            root.destroy()

    def test_add_wp_imgs_button_disabled_when_flag_false(self):
        root, app, patcher = self._build_app(False)
        try:
            self.assertEqual(app.add_wp_imgs_btn.cget('state'), tk.DISABLED)
            app.disable_all_buttons()
            app.enable_all_buttons()
            self.assertEqual(app.add_wp_imgs_btn.cget('state'), tk.DISABLED)
        finally:
            patcher.stop()
            root.destroy()


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMyKoalaWriterAppButtonState)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    test_result = run_tests()
    print("\n" + "=" * 70)
    print(f"Tests run: {test_result.testsRun}")
    print(f"Failures: {len(test_result.failures)}")
    print(f"Errors: {len(test_result.errors)}")
    print(f"Skipped: {len(test_result.skipped)}")
    print("=" * 70)
    sys.exit(0 if test_result.wasSuccessful() else 1)
