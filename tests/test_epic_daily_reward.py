import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import cv2,numpy as np
from test_seasonal_recovery import reward
from seasonal_rewards import modern_daily_reward
from state_finder import get_state,get_action_state
from stage_manager import StageManager


def epic():
    frame=reward();frame[120:]=(175,25,245)
    star=reward()[176:628,448:836].copy()
    outline=np.all(star==(0,20,15),axis=2)
    face=np.all(star==(20,130,75),axis=2)
    star[:]=(175,25,245);star[outline]=(55,0,70);star[face]=(215,40,150)
    star=cv2.resize(star,(364,408))
    frame[192:600,252:616]=star;frame[192:600,668:1032]=star
    return frame


class EpicDailyRewardTests(unittest.TestCase):
    def test_two_purple_stars_keep_existing_full_and_action_reward_route(self):
        for w,h in ((960,540),(1280,720),(1920,1080)):
            frame=cv2.resize(epic(),(w,h))
            self.assertTrue(modern_daily_reward(frame))
            self.assertEqual(get_state(frame),'daily_reward')
            self.assertEqual(get_action_state(frame),'daily_reward')

    def test_heading_and_both_stars_remain_required(self):
        for bounds in ((0,120,0,1280),(192,600,252,616),(192,600,668,1032)):
            frame=epic();y1,y2,x1,x2=bounds;frame[y1:y2,x1:x2]=(175,25,245)
            self.assertFalse(modern_daily_reward(frame),bounds)

    def test_colour_blocks_and_occluded_star_halves_do_not_authorize_action(self):
        frame=epic();frame[192:600,252:616]=(55,0,70);frame[192:600,668:1032]=(55,0,70)
        self.assertFalse(modern_daily_reward(frame))
        frame=epic();frame[350:440,200:1100]=255
        self.assertFalse(modern_daily_reward(frame))
        self.assertFalse(modern_daily_reward((epic()*.5).astype(np.uint8)))

    def test_unsupported_outline_colour_is_not_accepted(self):
        frame=epic();frame[np.all(frame==(55,0,70),axis=2)]=(80,50,150)
        self.assertFalse(modern_daily_reward(frame))

    def test_owner_checks_freshness_and_one_and_half_second_retry(self):
        fresh=True;manager=StageManager.__new__(StageManager);manager.runtime_control=None
        controller=SimpleNamespace(screenshot=epic,frame_is_fresh=lambda:fresh,release_all_inputs=Mock(),click=Mock())
        manager.window_controller=controller
        with patch('stage_manager.time.monotonic',return_value=10):manager.dismiss_daily_reward()
        with patch('stage_manager.time.monotonic',return_value=11.2):manager.dismiss_daily_reward()
        self.assertEqual(controller.click.call_count,1)
        fresh=False
        with patch('stage_manager.time.monotonic',return_value=12):manager.dismiss_daily_reward()
        self.assertEqual(controller.click.call_count,1)
        fresh=True
        with patch('stage_manager.time.monotonic',return_value=13):manager.dismiss_daily_reward()
        self.assertEqual(controller.click.call_count,2)
        self.assertEqual(controller.click.call_args.args,(640,360))

    def test_stop_or_pause_arriving_during_recognition_prevents_input(self):
        for cancellation in ('stop','pause'):
            state={'stop':False,'pause':False};manager=StageManager.__new__(StageManager)
            manager.runtime_control=SimpleNamespace(should_stop=lambda:state['stop'],should_pause=lambda:state['pause'])
            controller=SimpleNamespace(screenshot=epic,frame_is_fresh=lambda:True,release_all_inputs=Mock(),click=Mock())
            manager.window_controller=controller
            def recognise(frame):
                state[cancellation]=True
                return modern_daily_reward(frame)
            with patch('screen_evidence.daily_reward',side_effect=recognise):manager.dismiss_daily_reward()
            controller.click.assert_not_called()

