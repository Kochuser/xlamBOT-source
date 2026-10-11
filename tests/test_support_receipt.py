import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
import cv2,numpy as np
import support_receipt as receipt
import support_receipt_glyphs as glyphs
from new_brawler_receipt import _glyph,new_brawler_continue_position
from state_finder import get_state
from stage_manager import StageManager


def screen(w=1280,h=720):
    f=np.full((h,w,3),(10,70,180),np.uint8)
    f[round(h*.14):round(h*.23),round(w*.455):round(w*.64)]=(10,185,245)
    f[round(h*.13):round(h*.23),round(w*.65):round(w*.83)]=0
    f[round(h*.345):round(h*.475),round(w*.90):round(w*.985)]=(225,70,50)
    f[round(h*.49):round(h*.62),round(w*.91):round(w*.98)]=(250,195,40)
    f[round(h*.795):round(h*.915),round(w*.745):round(w*.945)]=(10,115,250)
    for e,x,y in ((glyphs.SUPER_RARE,607,115),(glyphs.SUPPORT,889,110),(glyphs.RIGHT_CONTINUE,1001,598)):
        g=_glyph(e,h);x,y=round(x*h/720),round(y*h/720)
        # The receipt layout is height-scaled and centred for wider windows.
        x+=round((w-1280*h/720)/2)
        f[y:y+g.shape[0],x:x+g.shape[1]][g>0]=255
    return f


class SupportReceiptTests(unittest.TestCase):
    def test_positive_native_scales_choose_right_continue(self):
        for w,h in ((960,540),(1280,720),(1920,1080)):
            f=screen(w,h)
            self.assertIsNotNone(new_brawler_continue_position(f),(w,h))
            x,y=new_brawler_continue_position(f)
            self.assertTrue(.78*w<x<.91*w and .81*h<y<.90*h)
            with patch('onboarding.onboarding_screen',side_effect=AssertionError('Unrelated search')):
                self.assertEqual(get_state(f),'new_brawler')
            with patch('disconnect_dialog.idle_disconnect_reload_position',return_value=(200,300)):
                self.assertEqual(get_state(f),'idle_disconnect')

    def test_all_independent_captions_and_scene_controls_are_required(self):
        for box in ((607,115,793,151),(889,110,1032,147),(1001,598,1164,638),
                    (590,105,815,165),(845,95,1060,165),(1152,248,1261,342),(1165,353,1254,446)):
            f=screen();x1,y1,x2,y2=box;f[y1:y2,x1:x2]=(25,25,25) if x1!=845 else (80,80,80)
            self.assertIsNone(receipt.support_continue_position(f),box)
        self.assertIsNone(receipt.support_continue_position((screen()*.5).astype(np.uint8)))
        self.assertIsNone(receipt.support_continue_position(np.full((720,1280,3),220,np.uint8)))
        self.assertIsNone(receipt.support_continue_position(None))

    def test_green_select_and_red_review_style_controls_cannot_continue(self):
        for color in ((20,230,0),(230,40,50)):
            f=screen();f[572:659,954:1210]=color
            g=_glyph(glyphs.RIGHT_CONTINUE,720);f[598:638,1001:1164][g>0]=255
            self.assertIsNone(receipt.support_continue_position(f))

    def test_owner_rechecks_freshness_stop_pause_and_repeat_interval(self):
        m=StageManager.__new__(StageManager);m.runtime_control=None
        wc=SimpleNamespace(screenshot=lambda:screen(),frame_is_fresh=lambda:True,
                           release_all_inputs=Mock(),click=Mock())
        m.window_controller=wc
        with patch('stage_manager.time.monotonic',return_value=10):
            m.dismiss_new_brawler();m.dismiss_new_brawler()
        self.assertEqual(wc.click.call_count,1)
        self.assertGreater(wc.click.call_args.args[0],1000)
        wc.frame_is_fresh=lambda:False;m._new_brawler_last_tap=-100
        m.dismiss_new_brawler();wc.frame_is_fresh=lambda:True
        for stop,pause in ((True,False),(False,True)):
            m.runtime_control=SimpleNamespace(should_stop=lambda:stop,should_pause=lambda:pause)
            m.dismiss_new_brawler()
        self.assertEqual(wc.click.call_count,1)

    def test_pause_during_recognition_cancels_continue(self):
        m=StageManager.__new__(StageManager);paused=False
        m.runtime_control=SimpleNamespace(should_stop=lambda:False,should_pause=lambda:paused)
        m.window_controller=SimpleNamespace(screenshot=lambda:screen(),frame_is_fresh=lambda:True,
                                            release_all_inputs=Mock(),click=Mock())
        def recognise(frame):
            nonlocal paused
            paused=True
            return new_brawler_continue_position(frame)
        with patch('new_brawler_receipt.new_brawler_continue_position',side_effect=recognise):
            m.dismiss_new_brawler()
        m.window_controller.click.assert_not_called()
