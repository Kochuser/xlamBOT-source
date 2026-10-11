import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import cv2
import numpy as np
from team_invite import _glyph, team_invite_reject_position
from team_invite_glyphs import TITLE, REJECT
from stage_manager import StageManager
from state_finder import get_state, get_action_state


def screen():
    frame = np.full((720,1280,3), (10,25,50), np.uint8)
    frame[143:573,367:913] = (15,85,220)
    frame[144:213,368:912] = (35,140,245)
    frame[414:489,409:632] = (224,45,40)
    frame[414:489,648:868] = (0,220,0)
    for encoded,x,y in [(TITLE,549,164),(REJECT,480,439)]:
        glyph = _glyph(encoded,720)
        frame[y:y+glyph.shape[0],x:x+glyph.shape[1]][glyph>0] = 255
    return frame


class TeamInviteTests(unittest.TestCase):
    def test_sizes_wide_screen_and_actual_reject_position(self):
        for w,h in [(960,540),(1280,720),(1920,1080)]:
            frame = cv2.resize(screen(),(w,h))
            point = team_invite_reject_position(frame)
            self.assertIsNotNone(point,(w,h))
            self.assertAlmostEqual(point[0]/w,521/1280,delta=.004)
            self.assertAlmostEqual(point[1]/h,452/720,delta=.004)
        frame = np.zeros((720,1600,3),np.uint8)
        frame[:,160:1440] = screen()
        self.assertAlmostEqual(team_invite_reject_position(frame)[0],681,delta=2)

    def test_each_independent_marker_and_button_colour_required(self):
        for bounds in [(143,214,368,912),(164,194,549,731),(439,465,480,562),(425,478,419,626)]:
            frame=screen();y1,y2,x1,x2=bounds
            frame[y1:y2,x1:x2] = (10,20,30)
            self.assertIsNone(team_invite_reject_position(frame))
        frame=screen();frame[414:489,409:632] = (0,220,0)
        glyph=_glyph(REJECT,720)
        frame[439:465,480:562][glyph>0] = 255
        self.assertIsNone(team_invite_reject_position(frame))
        self.assertIsNone(team_invite_reject_position((screen()*.5).astype(np.uint8)))
        self.assertIsNone(team_invite_reject_position(None))

    def test_modal_wins_over_underlying_hud_without_large_negative_scans(self):
        with patch('showdown_hud.visible_showdown_caption',return_value=True), \
             patch('onboarding.onboarding_screen',side_effect=AssertionError('Unnecessary scan')):
            self.assertEqual(get_state(screen()),'team_invite')
        self.assertEqual(get_action_state(screen()),'team_invite')

    def manager(self):
        manager=StageManager.__new__(StageManager);manager.runtime_control=None
        manager.window_controller=SimpleNamespace(screenshot=screen,frame_is_fresh=lambda:True,
            release_all_inputs=Mock(),click=Mock())
        return manager

    def test_owner_freshness_stop_pause_and_retry(self):
        manager=self.manager();controller=manager.window_controller
        with patch('stage_manager.time.monotonic',return_value=10):
            manager.reject_team_invite();manager.reject_team_invite()
        self.assertEqual(controller.click.call_count,1)
        self.assertLess(controller.click.call_args.args[0],640)
        manager._last_team_invite_reject=-100
        controller.frame_is_fresh=lambda:False
        manager.reject_team_invite()
        controller.frame_is_fresh=lambda:True
        for stop,pause in [(True,False),(False,True)]:
            manager.runtime_control=SimpleNamespace(should_stop=lambda:stop,should_pause=lambda:pause)
            manager.reject_team_invite()
        self.assertEqual(controller.click.call_count,1)

    def test_pause_during_recognition_or_missing_control_prevents_tap(self):
        manager=self.manager();manager._should_stop=Mock(return_value=False)
        manager._should_pause=Mock(side_effect=[False,True])
        manager.reject_team_invite();manager.window_controller.click.assert_not_called()
        manager=self.manager();manager.window_controller.screenshot=lambda:np.zeros((720,1280,3),np.uint8)
        manager.reject_team_invite();manager.window_controller.click.assert_not_called()
