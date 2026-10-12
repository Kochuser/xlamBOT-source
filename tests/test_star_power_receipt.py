import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from reward_receipts import _glyph,REMAINING
from star_power_glyph import STAR_POWER_TITLE
from star_power_receipt import star_power_receipt
from state_finder import get_state,get_action_state
from stage_manager import StageManager


def screen(w=1280,h=720):
    frame=np.full((h,w,3),(0,65,180),np.uint8)
    frame[round(h*.33):round(h*.65),round(w*.10):round(w*.30)]=(245,190,30)
    for encoded,x,y in ((STAR_POWER_TITLE,651,181),(REMAINING,948,666)):
        glyph=_glyph(encoded,h);x,y=round(x*w/1280),round(y*h/720)
        frame[y:y+glyph.shape[0],x:x+glyph.shape[1]][glyph>205]=255
    frame[round(h*.885):round(h*.968),round(w*.923):round(w*.968)]=(240,15,10)
    frame[round(h*.90):round(h*.94),round(w*.94):round(w*.95)]=255
    return frame


class StarPowerReceiptTests(unittest.TestCase):
    def test_native_scales_route_full_and_action_recognition_to_receipt(self):
        for w,h in ((960,540),(1280,720),(1920,1080)):
            frame=screen(w,h)
            self.assertTrue(star_power_receipt(frame),(w,h))
            self.assertEqual(get_state(frame),'reward_received')
            self.assertEqual(get_action_state(frame),'reward_received')
        with patch('disconnect_dialog.idle_disconnect_reload_position',return_value=(200,300)):
            self.assertEqual(get_state(screen()),'idle_disconnect')

    def test_heading_medal_backdrop_counter_and_remaining_each_required(self):
        for bounds in ((160,255,570,1170),(210,530,70,440),(0,145,0,550),(540,640,30,1150),(640,710,1170,1250),(655,700,935,1180)):
            frame=screen();y1,y2,x1,x2=bounds;frame[y1:y2,x1:x2]=35
            self.assertFalse(star_power_receipt(frame),bounds)
        self.assertFalse(star_power_receipt(None))
        self.assertFalse(star_power_receipt(np.zeros((0,0,3),np.uint8)))

    def test_star_power_preview_and_isolated_heading_never_authorize_tap(self):
        frame=screen();frame[640:]=(0,65,180)
        self.assertFalse(star_power_receipt(frame))
        frame=screen();frame[230:510,:430]=(0,65,180)
        self.assertFalse(star_power_receipt(frame))

    def test_dimmed_receipt_and_wrong_counter_colour_are_rejected(self):
        self.assertFalse(star_power_receipt((screen()*.6).astype(np.uint8)))
        frame=screen();frame[637:699,1180:1240]=(10,230,20)
        self.assertFalse(star_power_receipt(frame))

    def test_owner_rechecks_scene_freshness_cancel_and_one_and_half_second_retry(self):
        frame,fresh=screen(),True
        manager=StageManager.__new__(StageManager);manager.runtime_control=None
        controller=SimpleNamespace(screenshot=lambda:frame,frame_is_fresh=lambda:fresh,release_all_inputs=Mock(),click=Mock())
        manager.window_controller=controller
        with patch('stage_manager.time.monotonic',return_value=10):manager.dismiss_received_reward()
        with patch('stage_manager.time.monotonic',return_value=11.2):manager.dismiss_received_reward()
        self.assertEqual(controller.click.call_count,1)
        fresh=False
        with patch('stage_manager.time.monotonic',return_value=12):manager.dismiss_received_reward()
        fresh=True;frame=np.zeros_like(frame)
        with patch('stage_manager.time.monotonic',return_value=13):manager.dismiss_received_reward()
        frame=screen()
        for stop,pause in ((True,False),(False,True)):
            manager.runtime_control=SimpleNamespace(should_stop=lambda:stop,should_pause=lambda:pause)
            manager.dismiss_received_reward()
        self.assertEqual(controller.click.call_count,1)
        manager.runtime_control=None
        with patch('stage_manager.time.monotonic',return_value=14):manager.dismiss_received_reward()
        self.assertEqual(controller.click.call_count,2)
        self.assertEqual(controller.click.call_args.args,(640,634))

    def test_pause_during_recognition_cancels_owner_action(self):
        manager=StageManager.__new__(StageManager);paused=False
        manager.runtime_control=SimpleNamespace(should_stop=lambda:False,should_pause=lambda:paused)
        manager.window_controller=SimpleNamespace(screenshot=screen,frame_is_fresh=lambda:True,release_all_inputs=Mock(),click=Mock())
        def recognise(frame):
            nonlocal paused
            paused=True
            return star_power_receipt(frame)
        with patch('reward_received.is_reward_received',side_effect=recognise):manager.dismiss_received_reward()
        manager.window_controller.click.assert_not_called()
