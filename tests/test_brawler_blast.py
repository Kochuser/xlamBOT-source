import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import cv2
import numpy as np
from reward_receipts import _glyph
from brawler_blast_glyphs import TAP, ARROW, BONUS, LEFT_GUN, RIGHT_GUN, DOME, DOME_GLOW, DOME_PULSE
from brawler_blast import brawler_blast_fire_position
from stage_manager import StageManager
from state_finder import get_state


def gallery(w=1280, h=720):
    f = np.full((h,w,3), (40,15,25), np.uint8)
    f[:round(h*.17), :round(w*.14)] = (230,170,250)
    for a,b in ((.07,.2),(.81,.94)):
        f[round(h*.63):round(h*.72),round(w*a):round(w*b)] = (35,50,220)
    for center in (.1363,.8738):
        f[round(h*.55):round(h*.62), round(w*center-h*.035):round(w*center+h*.035)] = (250,215,40)
    for encoded,cx,y,color in ((TAP,.14,.393,(255,255,255)),(TAP,.877,.393,(255,255,255)),
                               (ARROW,.1363,.499,(255,255,255)),(ARROW,.8738,.499,(255,255,255)),
                               (BONUS,.5023,.914,(250,160,245))):
        g = _glyph(encoded,h)
        x,y = round(cx*w-g.shape[1]/2),round(y*h)
        f[y:y+g.shape[0],x:x+g.shape[1]][g>235] = color
    return f


class BrawlerBlastTests(unittest.TestCase):
    def test_capsule_pulse_preserves_scene_requirements_and_modal_priority(self):
        f=gallery();f[270:400]=0;f[650:]=0
        for encoded,x,y in ((LEFT_GUN,40,385),(RIGHT_GUN,1049,385),(DOME_PULSE,507,550)):
            g=_glyph(encoded,720)
            f[y:y+g.shape[0],x:x+g.shape[1]]=g[:,:,None]
        f[411:429,165:183]=(255,244,40)
        for w,h in ((960,540),(1280,720),(1920,1080)):
            resized=cv2.resize(f,(w,h))
            with patch('onboarding.onboarding_screen',side_effect=AssertionError('Unrelated scan')):
                self.assertEqual(get_state(resized),'brawler_blast')
            with patch('disconnect_dialog.idle_disconnect_reload_position',return_value=(200,300)):
                self.assertEqual(get_state(resized),'idle_disconnect')
        for y1,y2,x1,x2 in ((385,565,40,225),(385,565,1049,1238),(550,637,507,575),
                           (411,429,165,183),(0,120,0,180)):
            broken=f.copy();broken[y1:y2,x1:x2]=0
            self.assertIsNone(brawler_blast_fire_position(broken))
        self.assertIsNone(brawler_blast_fire_position((f*.5).astype(np.uint8)))

    def test_gallery_with_blinking_prompts_uses_independently_verified_control(self):
        f=gallery();f[270:400]=0;f[650:]=0
        for encoded,x,y in ((LEFT_GUN,40,385),(RIGHT_GUN,1049,385),(DOME,521,550)):
            g=_glyph(encoded,720)
            f[y:y+g.shape[0],x:x+g.shape[1]]=g[:,:,None]
        f[411:429,165:183]=(255,244,40)
        for w,h in ((960,540),(1280,720),(1920,1080)):
            resized=cv2.resize(f,(w,h))
            p=brawler_blast_fire_position(resized)
            self.assertIsNotNone(p,(w,h))
            self.assertAlmostEqual(p[0]/w,174/1280,delta=.003)
        for y1,y2,x1,x2 in ((385,565,40,225),(385,565,1049,1238),(550,637,521,565),
                           (411,429,165,183),(0,120,0,180)):
            broken=f.copy();broken[y1:y2,x1:x2]=0
            self.assertIsNone(brawler_blast_fire_position(broken))
        self.assertIsNone(brawler_blast_fire_position((f*.5).astype(np.uint8)))

    def test_fragment_glow_without_bonus_caption_still_requires_both_guns(self):
        f=gallery();f[270:400]=0;f[650:]=0
        for encoded,x,y in ((LEFT_GUN,40,385),(RIGHT_GUN,1049,385),(DOME_GLOW,521,550)):
            g=_glyph(encoded,720)
            f[y:y+g.shape[0],x:x+g.shape[1]]=g[:,:,None]
        f[411:429,165:183]=(255,244,40)
        for w,h in ((960,540),(1280,720),(1920,1080)):
            self.assertIsNotNone(brawler_blast_fire_position(cv2.resize(f,(w,h))))
        for y1,y2,x1,x2 in ((385,565,40,225),(385,565,1049,1238),(550,637,521,565)):
            broken=f.copy();broken[y1:y2,x1:x2]=0
            self.assertIsNone(brawler_blast_fire_position(broken))

    def test_visible_controls_at_native_resolutions_and_wide_layout(self):
        for w,h in ((960,540),(1280,720),(1920,1080),(1536,720)):
            f=gallery(w,h)
            p=brawler_blast_fire_position(f)
            self.assertIsNotNone(p,(w,h))
            self.assertAlmostEqual(p[0]/w,.1363,delta=.003)
            self.assertTrue(.56<p[1]/h<.6)
            self.assertEqual(get_state(f),'brawler_blast')

    def test_each_control_caption_arrow_and_scene_marker_is_required(self):
        for y1,y2,x1,x2 in ((0,120,0,180),(650,715,450,850),
                           (270,350,85,265),(270,350,1025,1210),
                           (355,400,135,210),(355,400,1080,1155),
                           (400,440,145,205),(400,440,1090,1150),
                           (450,525,80,260),(450,525,1035,1210)):
            f=gallery();f[y1:y2,x1:x2]=0
            self.assertIsNone(brawler_blast_fire_position(f),(y1,x1))
        self.assertIsNone(brawler_blast_fire_position(None))
        self.assertIsNone(brawler_blast_fire_position((gallery()*.5).astype(np.uint8)))

    def test_animation_without_prompts_and_wrong_colour_caps_are_rejected(self):
        f=gallery();f[270:400]=0
        self.assertIsNone(brawler_blast_fire_position(f))
        f=gallery();f[400:440,145:205]=(255,20,40)
        self.assertIsNone(brawler_blast_fire_position(f))
        # Decorative gallery targets or an EXIT caption cannot authorize input.
        self.assertIsNone(brawler_blast_fire_position(np.full((720,1280,3),220,np.uint8)))

    def test_owner_rechecks_cancel_and_freshness_then_limits_each_shot(self):
        m=StageManager.__new__(StageManager);m.runtime_control=None
        f,fresh=gallery(),True
        wc=SimpleNamespace(screenshot=lambda:f,frame_is_fresh=lambda:fresh,
                           release_all_inputs=Mock(),click=Mock())
        m.window_controller=wc
        with patch('stage_manager.time.monotonic',return_value=10):
            m.fire_brawler_blast();m.fire_brawler_blast()
        self.assertEqual(wc.click.call_count,1)
        self.assertAlmostEqual(wc.click.call_args.args[0],174.5,delta=2)
        m._blast_last_tap=-100;fresh=False;m.fire_brawler_blast()
        fresh=True;f=np.zeros_like(f);m.fire_brawler_blast()
        f=gallery()
        for stop,pause in ((True,False),(False,True)):
            m.runtime_control=SimpleNamespace(should_stop=lambda:stop,should_pause=lambda:pause)
            m.fire_brawler_blast()
        self.assertEqual(wc.click.call_count,1)

    def test_pause_during_recognition_cancels_non_release_input(self):
        m=StageManager.__new__(StageManager)
        paused=False
        m.runtime_control=SimpleNamespace(should_stop=lambda:False,should_pause=lambda:paused)
        m.window_controller=SimpleNamespace(screenshot=lambda:gallery(),frame_is_fresh=lambda:True,
                                            release_all_inputs=Mock(),click=Mock())
        def recognise(frame):
            nonlocal paused
            paused=True
            return brawler_blast_fire_position(frame)
        with patch('brawler_blast.brawler_blast_fire_position',side_effect=recognise):
            m.fire_brawler_blast()
        m.window_controller.click.assert_not_called()


if __name__=='__main__':
    unittest.main()
