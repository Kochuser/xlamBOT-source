import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import cv2
import numpy as np
from reward_receipts import _glyph, CONTINUE, skin_receipt_continue_position
from new_skin_glyphs import NEW_EPIC, CURRENT
from new_skin_receipt import new_skin_continue_position
from stage_manager import StageManager
from state_finder import get_state


def screen():
    f = np.full((720, 1280, 3), (30, 10, 190), np.uint8)
    f[584:659, 620:867] = (30, 110, 250)
    f[584:659, 908:1154] = (0, 230, 10)
    for encoded, x, y, color in [(NEW_EPIC, 633, 120, (210, 0, 250)),
                                (CURRENT, 754, 15, (255, 255, 255)),
                                (CONTINUE, 631, 601, (255, 255, 255))]:
        g = _glyph(encoded, 720)
        f[y:y+g.shape[0], x:x+g.shape[1]][g > 205] = color
    return f


class NewSkinReceiptTests(unittest.TestCase):
    def test_awarded_epic_skin_at_native_sizes_uses_continue(self):
        for w, h in [(960, 540), (1280, 720), (1920, 1080)]:
            f = cv2.resize(screen(), (w, h))
            p = new_skin_continue_position(f)
            self.assertIsNotNone(p, (w, h))
            self.assertAlmostEqual(p[0]/w, 729/1280, delta=.003)
            self.assertEqual(get_state(f), 'seasonal_announcement')
            self.assertIsNone(skin_receipt_continue_position(f))

    def test_new_heading_current_label_control_and_backdrop_each_required(self):
        for bounds in [(100, 235, 620, 1160), (0, 60, 750, 890),
                       (590, 650, 640, 860), (0, 180, 0, 150)]:
            f = screen()
            y1, y2, x1, x2 = bounds
            f[y1:y2, x1:x2] = 35
            self.assertIsNone(new_skin_continue_position(f))
        f = screen();f[594:641,628:851] = (220, 10, 20)
        g = _glyph(CONTINUE, 720)
        f[601:601+g.shape[0],631:631+g.shape[1]][g > 205] = 255
        self.assertIsNone(new_skin_continue_position(f))
        self.assertIsNone(new_skin_continue_position((screen()*.5).astype(np.uint8)))
        self.assertIsNone(new_skin_continue_position(None))

    def test_old_preview_without_remaining_items_stays_unauthorized(self):
        from test_reward_receipts import receipt
        f = receipt('skin');f[650:] = 0
        self.assertIsNone(skin_receipt_continue_position(f))
        self.assertIsNone(new_skin_continue_position(f))

    def test_owner_never_equips_and_rechecks_freshness_pause_and_retry(self):
        m = StageManager.__new__(StageManager);m.runtime_control = None
        f, fresh = screen(), True
        wc = SimpleNamespace(screenshot=lambda:f, frame_is_fresh=lambda:fresh,
                             release_all_inputs=Mock(), click=Mock())
        m.window_controller = wc
        with patch('stage_manager.time.monotonic', return_value=10.):
            m.dismiss_seasonal_announcement();m.dismiss_seasonal_announcement()
        self.assertEqual(wc.click.call_count, 1)
        self.assertLess(wc.click.call_args.args[0], 1280*.69)
        m._seasonal_last_tap = -100;fresh = False
        m.dismiss_seasonal_announcement()
        fresh = True;f = np.zeros_like(f)
        m.dismiss_seasonal_announcement()
        f = screen()
        for stop, pause in [(True, False), (False, True)]:
            m.runtime_control = SimpleNamespace(should_stop=lambda:stop, should_pause=lambda:pause)
            m.dismiss_seasonal_announcement()
        self.assertEqual(wc.click.call_count, 1)


if __name__ == '__main__':
    unittest.main()
