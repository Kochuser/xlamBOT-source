import unittest
from unittest.mock import patch
import cv2
import numpy as np
from transition_glyphs import LOGO, PERCENT, VERSUS, INTRO_CAPTION, BAR_CAP
from transition_screen import _glyph, transition_state
from state_finder import get_state


def screen(kind):
    f=np.full((720,1280,3),(15,30,70),np.uint8)
    items=[(LOGO,23,28),(PERCENT,644,573)] if kind=='loading' else [(VERSUS,590,277),(INTRO_CAPTION,369,648)]
    if kind=='loading':
        f[649:680,481:800]=(240,116,25)
    for encoded,x,y in items:
        g=_glyph(encoded,720);f[y:y+g.shape[0],x:x+g.shape[1]][g>0]=255
    return f


class TransitionScreenTests(unittest.TestCase):
    def test_loading_and_intro_at_supported_sizes(self):
        for kind in ['loading','match_intro']:
            for w,h in [(960,540),(1280,720),(1920,1080)]:
                f=cv2.resize(screen(kind),(w,h))
                self.assertEqual(transition_state(f),kind,(kind,w,h))

    def test_percentage_path_requires_logo_percentage_and_bar(self):
        for bounds in [(0,180,0,300),(560,640,620,710),(640,690,460,830)]:
            f=screen('loading');y1,y2,x1,x2=bounds;f[y1:y2,x1:x2]=0
            self.assertIsNone(transition_state(f))

    def outline_screen(self):
        f=screen('loading');f[560:640,620:710]=(15,30,70)
        glyph=_glyph(BAR_CAP,720)
        h,w=glyph.shape
        f[640:640+h,472:472+w]=(240,116,25)
        f[640:640+h,472:472+w][glyph>0]=0
        return f

    def test_faded_percentage_requires_independent_logo_bar_and_outline(self):
        for w,h in [(960,540),(1280,720),(1920,1080)]:
            self.assertEqual(transition_state(cv2.resize(self.outline_screen(),(w,h))),'loading')
        for bounds in [(0,180,0,300),(640,692,472,540),(640,692,472,800)]:
            f=self.outline_screen();y1,y2,x1,x2=bounds;f[y1:y2,x1:x2]=(80,100,170)
            self.assertIsNone(transition_state(f))

    def test_percentage_remains_independent_of_neighbouring_digit(self):
        # A native crop can accidentally include the edge of the last digit.
        # Remove such a clipped component when constructing an independent
        # percentage screen, then vary the neighbouring digit's appearance.
        glyph=_glyph(PERCENT,720)
        _,labels,stats,_=cv2.connectedComponentsWithStats(glyph)
        percent=glyph.copy()
        for label,(x,y,w,h,area) in enumerate(stats[1:],1):
            if x==0:
                percent[labels==label]=0
        for neighbour in [0,255]:
            f=screen('loading')
            f[573:624,644:644+glyph.shape[1]]=(15,30,70)
            f[573:624,638:644]=neighbour
            f[573:624,644:644+glyph.shape[1]][percent>0]=255
            self.assertEqual(transition_state(f),'loading')

    def test_intro_requires_both_captions(self):
        for bounds in [(270,345,580,690),(640,705,350,900)]:
            f=screen('match_intro');y1,y2,x1,x2=bounds;f[y1:y2,x1:x2]=0
            self.assertIsNone(transition_state(f))
        for kind in ['loading','match_intro']:
            self.assertIsNone(transition_state((screen(kind)*.5).astype(np.uint8)))

    def test_full_native_classifier_skips_unrelated_menu_scans(self):
        for kind in ['loading','match_intro']:
            with patch('onboarding.onboarding_screen',side_effect=AssertionError('Unnecessary scan')):
                self.assertEqual(get_state(screen(kind)),kind)

    def test_known_modal_priority_is_preserved(self):
        with patch('disconnect_dialog.idle_disconnect_reload_position',return_value=(1,2)):
            self.assertEqual(get_state(screen('loading')),'idle_disconnect')
        with patch('rating_dialog.rating_later_position',return_value=(1,2)):
            self.assertEqual(get_state(screen('match_intro')),'rating_dialog')

    def test_invalid_and_ordinary_blue_frames_have_no_transition_authority(self):
        for frame in [None,np.zeros((720,1280),np.uint8),np.full((720,1280,3),(15,70,230),np.uint8)]:
            self.assertIsNone(transition_state(frame))
