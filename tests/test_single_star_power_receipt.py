import unittest
from types import SimpleNamespace
from unittest.mock import patch
import cv2,numpy as np
from reward_receipts import _glyph
from star_power_glyph import STAR_POWER_TITLE
from star_power_receipt import star_power_receipt
from single_star_power_receipt import single_star_power_receipt
from state_finder import get_state,get_action_state
from stage_manager import StageManager
from test_star_power_receipt import screen as sequence_screen


def receipt(w=1280,h=720):
    f=np.full((h,w,3),(0,65,180),np.uint8)
    f[round(h*.33):round(h*.65),round(w*.10):round(w*.30)]=(245,190,30)
    g=_glyph(STAR_POWER_TITLE,h);x,y=round(w*.51),round(h*.252)
    f[y:y+g.shape[0],x:x+g.shape[1]][g>205]=255
    cv2.putText(f,'COLT',(round(w*.64),round(h*.21)),cv2.FONT_HERSHEY_SIMPLEX,h/600,(255,255,255),round(h/180))
    cv2.putText(f,'STAR ABILITY',(round(w*.55),round(h*.39)),cv2.FONT_HERSHEY_SIMPLEX,h/600,(70,235,250),round(h/300))
    f[round(h*.432):round(h*.673),round(w*.387):round(w*.965)]=0
    f[round(h*.44):round(h*.663),round(w*.55):round(w*.96)]=(8,15,100)
    for index,text in enumerate(('Friendly brawlers gain health','Every second in range','While this ability is active')):
        cv2.putText(f,text,(round(w*.57),round(h*(.48+.06*index))),cv2.FONT_HERSHEY_SIMPLEX,h/850,(70,235,250),round(h/360))
    return f


class SingleStarPowerTests(unittest.TestCase):
    def test_independent_card_reveal_with_no_remaining_counter(self):
        for w,h in ((960,540),(1280,720),(1920,1080),(1600,720)):
            f=receipt(w,h)
            self.assertFalse(star_power_receipt(f))
            self.assertTrue(single_star_power_receipt(f),(w,h))
            self.assertEqual(get_state(f),'reward_received')
            self.assertEqual(get_action_state(f),'reward_received')

    def test_old_preview_without_counter_still_rejected(self):
        f=sequence_screen();f[640:]=(0,65,180)
        self.assertFalse(star_power_receipt(f))
        self.assertFalse(single_star_power_receipt(f))

    def test_requires_title_medal_name_ability_borders_and_card_text(self):
        for region in ((.45,.23,.92,.33),(.065,.29,.335,.71),(.48,.16,.88,.225),(.47,.335,.89,.414),(.39,.432,.96,.439),(.39,.666,.96,.673),(.56,.445,.955,.655),(.03,.03,.43,.20)):
            f=receipt();left,top,right,bottom=region
            f[round(720*top):round(720*bottom),round(1280*left):round(1280*right)]=35 if region==(.03,.03,.43,.20) else (0,65,180)
            self.assertFalse(single_star_power_receipt(f),region)

    def test_wrong_colors_solid_shapes_and_dimmed_overlay_are_rejected(self):
        f=receipt();f[np.all(f==(70,235,250),axis=2)]=(0,235,0)
        self.assertFalse(single_star_power_receipt(f))
        f=receipt();f[322:470,716:1222]=(70,235,250)
        self.assertFalse(single_star_power_receipt(f))
        self.assertFalse(single_star_power_receipt((receipt()*.65).astype(np.uint8)))
        self.assertFalse(single_star_power_receipt(None))

    def test_owner_obeys_retry_freshness_and_cancel(self):
        m=StageManager.__new__(StageManager);calls=[];fresh=[True];frame=receipt()
        m.runtime_control=None
        m.window_controller=SimpleNamespace(screenshot=lambda:frame,frame_is_fresh=lambda:fresh[0],release_all_inputs=lambda:None,click=lambda *a,**kw:calls.append(a))
        for now in (100,101.2):
            with patch('stage_manager.time.monotonic',return_value=now):m.dismiss_received_reward()
        self.assertEqual(calls,[(640,634)])
        fresh[0]=False
        with patch('stage_manager.time.monotonic',return_value=102):m.dismiss_received_reward()
        fresh[0]=True
        for stop,pause in ((True,False),(False,True)):
            m.runtime_control=SimpleNamespace(should_stop=lambda:stop,should_pause=lambda:pause)
            with patch('stage_manager.time.monotonic',return_value=104):m.dismiss_received_reward()
        self.assertEqual(len(calls),1)

    def test_pause_during_recognition_cancels_owner(self):
        m=StageManager.__new__(StageManager);paused=[False];calls=[]
        m.runtime_control=SimpleNamespace(should_stop=lambda:False,should_pause=lambda:paused[0])
        m.window_controller=SimpleNamespace(screenshot=receipt,frame_is_fresh=lambda:True,release_all_inputs=lambda:None,click=lambda *a,**kw:calls.append(a))
        def recognize(frame):paused[0]=True;return True
        with patch('reward_received.is_reward_received',side_effect=recognize):m.dismiss_received_reward()
        self.assertEqual(calls,[])
