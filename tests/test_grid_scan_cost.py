import unittest
from unittest.mock import patch
import numpy as np
import state_finder as finder


def grid():
    h,w=720,1280
    frame=np.full((h,w,3),(10,65,150),np.uint8)
    for name in ('brawler_menu_heart','brawler_menu_search'):
        glyph=finder.load_template(finder.states_path+name+'.png',w,h)
        x,y,_,_=finder.region_data[name]
        x,y=round(x*w/1920),round(y*h/1080)
        frame[y:y+glyph.shape[0],x:x+glyph.shape[1]]=glyph
    return frame


class GridScanTests(unittest.TestCase):
    def test_confirmed_grid_avoids_unrelated_legacy_result_scans(self):
        frame=grid()
        self.assertTrue(finder.is_in_brawler_selection(frame))
        with patch('state_finder.is_in_end_of_a_match',side_effect=AssertionError('Grid is already confirmed')):
            self.assertEqual(finder.get_state(frame),'brawler_selection')

    def test_grid_keeps_modal_and_onboarding_priority(self):
        frame=grid()
        with patch('disconnect_dialog.idle_disconnect_reload_position',return_value=(200,300)):
            self.assertEqual(finder.get_state(frame),'idle_disconnect')
        with patch('onboarding.onboarding_screen',return_value=True):
            self.assertEqual(finder.get_state(frame),'onboarding')

    def test_one_icon_cannot_identify_grid(self):
        frame=grid()
        x,y,width,height=finder.region_data['brawler_menu_search']
        frame[round(y*720/1080):round((y+height)*720/1080),round(x*1280/1920):round((x+width)*1280/1920)]=0
        self.assertFalse(finder.is_in_brawler_selection(frame))
