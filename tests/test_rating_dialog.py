import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import cv2
import numpy as np
import state_finder
from rating_dialog import _glyph, rating_later_position
from rating_dialog_glyphs import TITLE, LATER
from stage_manager import StageManager


def screen():
    frame = np.full((720, 1280, 3), (20, 70, 30), np.uint8)
    frame[242:478, 312:967] = 64
    for encoded, x, y, color in [(TITLE, 344, 273, (255, 255, 255)),
                                (LATER, 344, 424, (125, 205, 205))]:
        glyph = _glyph(encoded, 720)
        frame[y:y+glyph.shape[0], x:x+glyph.shape[1]][glyph > 0] = color
    return frame


class RatingDialogTests(unittest.TestCase):
    def test_later_at_supported_sizes_and_underlying_state_priority(self):
        for w, h in [(960, 540), (1280, 720), (1920, 1080)]:
            frame = cv2.resize(screen(), (w, h))
            position = rating_later_position(frame)
            self.assertIsNotNone(position, (w, h))
            self.assertAlmostEqual(position[0]/w, 379/1280, delta=.003)
            self.assertAlmostEqual(position[1]/h, 437/720, delta=.003)
            with patch('showdown_hud.visible_showdown_caption', return_value=True):
                self.assertEqual(state_finder.get_state(frame), 'rating_dialog')

    def test_uniform_font_scale_in_wide_screen_modal(self):
        frame = np.full((720, 1600, 3), 20, np.uint8)
        frame[:, 160:1440] = screen()
        position = rating_later_position(frame)
        self.assertIsNotNone(position)
        self.assertAlmostEqual(position[0], 539, delta=2)

    def test_reduced_menu_reader_falls_back_to_native_controls(self):
        self.assertEqual(state_finder.get_action_state(screen()), 'rating_dialog')

    def test_title_later_and_modal_body_each_required(self):
        for bounds in [(270, 312, 340, 578), (420, 455, 340, 420), (320, 410, 325, 955)]:
            frame = screen()
            y1, y2, x1, x2 = bounds
            frame[y1:y2, x1:x2] = (20, 90, 150)
            self.assertIsNone(rating_later_position(frame))
        self.assertIsNone(rating_later_position((screen()*.5).astype(np.uint8)))
        self.assertIsNone(rating_later_position(None))
        self.assertIsNone(rating_later_position(np.zeros((720,1280), np.uint8)))

    def test_generic_cyan_button_or_wrong_colour_cannot_authorize_tap(self):
        frame = screen()
        frame[424:450, 344:415] = (125, 205, 205)
        self.assertIsNone(rating_later_position(frame))
        frame = screen()
        frame[424:450, 344:415] = 64
        glyph = _glyph(LATER, 720)
        frame[424:450,344:415][glyph > 0] = 255
        self.assertIsNone(rating_later_position(frame))

    def test_owner_rechecks_freshness_controls_and_bounded_retry(self):
        manager = StageManager.__new__(StageManager)
        manager.runtime_control = None
        frame, fresh = screen(), True
        controller = SimpleNamespace(screenshot=lambda:frame, frame_is_fresh=lambda:fresh,
                                     release_all_inputs=Mock(), click=Mock())
        manager.window_controller = controller
        with patch('stage_manager.time.monotonic', return_value=10.):
            manager.dismiss_rating_dialog()
            manager.dismiss_rating_dialog()
        self.assertEqual(controller.click.call_count, 1)
        self.assertAlmostEqual(controller.click.call_args.args[0], 379, delta=2)
        manager._last_rating_later_tap = -100
        frame = np.zeros_like(frame)
        manager.dismiss_rating_dialog()
        frame, fresh = screen(), False
        manager.dismiss_rating_dialog()
        fresh = True
        for stop, pause in [(True, False), (False, True)]:
            manager.runtime_control = SimpleNamespace(should_stop=lambda:stop, should_pause=lambda:pause)
            manager.dismiss_rating_dialog()
        self.assertEqual(controller.click.call_count, 1)
        self.assertEqual(controller.release_all_inputs.call_count, 1)

    def test_pause_arriving_during_recognition_prevents_input(self):
        manager = StageManager.__new__(StageManager)
        manager.window_controller = SimpleNamespace(screenshot=screen, frame_is_fresh=lambda:True,
                                                    release_all_inputs=Mock(), click=Mock())
        manager._should_stop = Mock(return_value=False)
        manager._should_pause = Mock(side_effect=[False, True])
        manager.dismiss_rating_dialog()
        manager.window_controller.click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
