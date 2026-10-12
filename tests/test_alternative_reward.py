import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np
from alternative_reward import alternative_claim_position
from alternative_reward_glyphs import HEADER,EXPLANATION,CLAIM
from seasonal_rewards import _glyph,seasonal_announcement_dismiss_position
from state_finder import get_state,get_action_state
from stage_manager import StageManager


def screen(w=1280,h=720):
    frame=np.full((h,w,3),30,np.uint8)
    frame[round(h*.24):round(h*.75),round(w*.245):round(w*.755)]=(15,88,230)
    frame[round(h*.24):round(h*.34),round(w*.245):round(w*.755)]=(35,145,244)
    frame[round(h*.61):round(h*.715),round(w*.405):round(w*.595)]=(35,112,255)
    for encoded,y in ((HEADER,.26),(EXPLANATION,.44),(CLAIM,.642)):
        glyph=_glyph(encoded,h);left=round(w*.5)-glyph.shape[1]//2;top=round(h*y)
        frame[top:top+glyph.shape[0],left:left+glyph.shape[1]][glyph>205]=255
    return frame


class AlternativeRewardTests(unittest.TestCase):
    def test_native_sizes_and_wide_frame_keep_exact_claim_position(self):
        for w,h in ((960,540),(1280,720),(1920,1080),(1680,720)):
            frame=screen(w,h);position=alternative_claim_position(frame)
            self.assertIsNotNone(position,(w,h));self.assertAlmostEqual(position[0],w*.5,delta=1)
            self.assertTrue(h*.64<position[1]<h*.70)
            self.assertEqual(get_state(frame),'seasonal_announcement')
            self.assertEqual(get_action_state(frame),'seasonal_announcement')

    def test_all_three_captions_and_modal_colours_are_independently_required(self):
        for bounds in ((.30,.25,.70,.33),(.275,.425,.725,.525),(.42,.62,.58,.70),(.27,.245,.73,.34),(.27,.36,.73,.72)):
            frame=screen();x1,y1,x2,y2=bounds
            frame[round(720*y1):round(720*y2),round(1280*x1):round(1280*x2)]=35
            self.assertIsNone(alternative_claim_position(frame),bounds)

    def test_generic_claim_and_purchase_colours_or_dimmed_content_are_rejected(self):
        frame=screen();frame[:280]=30
        self.assertIsNone(alternative_claim_position(frame))
        for colour in ((20,230,30),(230,20,20)):
            frame=screen();frame[446:504,538:742]=colour
            self.assertIsNone(alternative_claim_position(frame))
        self.assertIsNone(alternative_claim_position((screen()*.5).astype(np.uint8)))
        frame=screen();frame[216:504,38:192]=180
        self.assertIsNone(alternative_claim_position(frame))

    def test_modal_precedes_underlying_lobby_and_blank_button_is_not_a_control(self):
        with patch('state_finder.is_in_lobby',return_value=True):
            self.assertEqual(get_state(screen()),'seasonal_announcement')
        frame=screen();frame[458:495,585:695]=(35,112,255)
        self.assertIsNone(alternative_claim_position(frame))
        self.assertIsNone(alternative_claim_position(None))
        self.assertIsNone(alternative_claim_position(np.zeros((0,0,3),np.uint8)))

    def test_owner_claim_requires_fresh_frame_and_bounded_retry(self):
        fresh=True;manager=StageManager.__new__(StageManager);manager.runtime_control=None
        controller=SimpleNamespace(screenshot=screen,frame_is_fresh=lambda:fresh,release_all_inputs=Mock(),click=Mock())
        manager.window_controller=controller
        with patch('stage_manager.time.monotonic',return_value=10):manager.dismiss_seasonal_announcement()
        with patch('stage_manager.time.monotonic',return_value=11.2):manager.dismiss_seasonal_announcement()
        self.assertEqual(controller.click.call_count,1)
        fresh=False
        with patch('stage_manager.time.monotonic',return_value=12):manager.dismiss_seasonal_announcement()
        self.assertEqual(controller.click.call_count,1)
        fresh=True
        with patch('stage_manager.time.monotonic',return_value=13):manager.dismiss_seasonal_announcement()
        self.assertEqual(controller.click.call_count,2)
        self.assertEqual(controller.click.call_args.args,alternative_claim_position(screen()))

    def test_owner_cancel_arriving_during_recognition_prevents_claim(self):
        for cancellation in ('stop','pause'):
            state={'stop':False,'pause':False};manager=StageManager.__new__(StageManager)
            manager.runtime_control=SimpleNamespace(should_stop=lambda:state['stop'],should_pause=lambda:state['pause'])
            controller=SimpleNamespace(screenshot=screen,frame_is_fresh=lambda:True,release_all_inputs=Mock(),click=Mock())
            manager.window_controller=controller
            def recognise(frame):
                state[cancellation]=True
                return seasonal_announcement_dismiss_position(frame)
            with patch('seasonal_rewards.seasonal_announcement_dismiss_position',side_effect=recognise):manager.dismiss_seasonal_announcement()
            controller.click.assert_not_called()

