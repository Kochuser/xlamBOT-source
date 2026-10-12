import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import unlocked_receipt as u
from reward_received import is_reward_received
from stage_manager import StageManager
from state_finder import get_state, get_action_state


def receipt(w=1280,h=720,header=True,unlocked=True,blue=True,portrait=True,footer=True):
    f=np.full((h,w,3),(10,125,225) if blue else (200,35,30),np.uint8)
    if portrait:
        f[round(h*.30):round(h*.49),round(w*.43):round(w*.57)]=(150,215,235)
    if footer:
        f[round(h*.495):round(h*.552),round(w*.438):round(w*.565)]=0
    for enabled,glyph,x,y,color in (
            (header,u.HEADER,.438,.185,(80,235,250)),
            (unlocked,u.UNLOCKED,.44,.591,(255,220,0))):
        if enabled:
            mask=u._glyph(glyph,h);left,top=round(w*x),round(h*y)
            f[top:top+mask.shape[0],left:left+mask.shape[1]][mask>0]=color
    return f


class UnlockedReceiptTests(unittest.TestCase):
    def test_exact_unlock_receipt_at_native_resolutions_and_wide_aspect(self):
        for w,h in ((1280,720),(960,540),(1920,1080),(1600,720)):
            with self.subTest(w=w,h=h):
                f=receipt(w,h)
                self.assertTrue(u.unlocked_receipt(f))
                self.assertTrue(is_reward_received(f))
                self.assertEqual(get_state(f),'reward_received')
                self.assertEqual(get_action_state(f),'reward_received')

    def test_requires_both_actual_captions_blue_background_and_portrait(self):
        for missing in ('header','unlocked','blue','portrait','footer'):
            with self.subTest(missing=missing):
                self.assertFalse(u.unlocked_receipt(receipt(**{missing:False})))

    def test_rejects_wrong_caption_colors_dim_overlay_and_solid_shapes(self):
        f=receipt();f[np.all(f==(80,235,250),axis=2)]=255
        self.assertFalse(u.unlocked_receipt(f))
        f=receipt();f[np.all(f==(255,220,0),axis=2)]=(80,235,250)
        self.assertFalse(u.unlocked_receipt(f))
        self.assertFalse(u.unlocked_receipt((receipt()*.65).astype(np.uint8)))
        f=receipt(header=False);f[133:165,560:725]=(80,235,250)
        self.assertFalse(u.unlocked_receipt(f))
        self.assertFalse(u.unlocked_receipt(None))

    def test_owner_rechecks_freshness_stop_pause_and_retry(self):
        m=StageManager.__new__(StageManager);frame=receipt();calls=[]
        m.runtime_control=None
        m.window_controller=SimpleNamespace(screenshot=lambda:frame,
            release_all_inputs=lambda:None,frame_is_fresh=lambda:True,
            click=lambda *args,**kw:calls.append(args))
        with patch('stage_manager.time.monotonic',return_value=100):m.dismiss_received_reward()
        self.assertEqual(calls,[(640,634)])
        with patch('stage_manager.time.monotonic',return_value=101.2):m.dismiss_received_reward()
        self.assertEqual(len(calls),1)
        with patch('stage_manager.time.monotonic',return_value=101.6):m.dismiss_received_reward()
        self.assertEqual(len(calls),2)
        m.window_controller.frame_is_fresh=lambda:False
        with patch('stage_manager.time.monotonic',return_value=104):m.dismiss_received_reward()
        m.window_controller.frame_is_fresh=lambda:True
        for stop,pause in ((True,False),(False,True)):
            m.runtime_control=SimpleNamespace(should_stop=lambda:stop,should_pause=lambda:pause)
            with patch('stage_manager.time.monotonic',return_value=106):m.dismiss_received_reward()
        self.assertEqual(len(calls),2)

    def test_pause_during_recognition_cancels_dismissal(self):
        m=StageManager.__new__(StageManager);paused=[False];calls=[]
        m.runtime_control=SimpleNamespace(should_stop=lambda:False,should_pause=lambda:paused[0])
        m.window_controller=SimpleNamespace(screenshot=lambda:receipt(),release_all_inputs=lambda:None,
            frame_is_fresh=lambda:True,click=lambda *a,**kw:calls.append(a))
        def recognize(frame):paused[0]=True;return True
        with patch('reward_received.is_reward_received',side_effect=recognize):m.dismiss_received_reward()
        self.assertEqual(calls,[])

    def test_owner_does_not_tap_missing_unlock_or_preview(self):
        m=StageManager.__new__(StageManager);calls=[];frame=receipt(unlocked=False)
        m.runtime_control=None
        m.window_controller=SimpleNamespace(screenshot=lambda:frame,release_all_inputs=lambda:None,
            frame_is_fresh=lambda:True,click=lambda *a,**kw:calls.append(a))
        m.dismiss_received_reward()
        self.assertEqual(calls,[])
