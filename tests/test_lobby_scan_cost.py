import unittest
from unittest.mock import patch
import numpy as np
import onboarding as o
import state_finder as s

class LobbyScanCostTests(unittest.TestCase):
    def test_native_lobby_candidate_avoids_reduced_negative_pass(self):
        frame=np.zeros((720,1280,3),np.uint8)
        with patch('screen_evidence.current_lobby',return_value=True), patch('state_finder.get_in_game_state',return_value='lobby') as classify:
            self.assertEqual(s.get_action_state(frame),'lobby')
        classify.assert_called_once()
        self.assertIs(classify.call_args.args[0],frame)

    def test_native_lobby_candidate_keeps_full_modal_and_tutorial_priority(self):
        frame=np.zeros((720,1280,3),np.uint8)
        with patch('screen_evidence.current_lobby',return_value=True), patch('disconnect_dialog.idle_disconnect_reload_position',return_value=(200,300)):
            self.assertEqual(s.get_action_state(frame),'idle_disconnect')
        with patch('screen_evidence.current_lobby',return_value=True), patch('onboarding.onboarding_screen',return_value=True):
            self.assertEqual(s.get_action_state(frame),'onboarding')

    def test_absent_grey_body_avoids_large_disconnect_caption_scans(self):
        frame=np.full((720,1280,3),(20,90,200),np.uint8)
        template=np.full((16,48,3),220,np.uint8)
        with patch('state_finder.load_template',return_value=template), patch('state_finder.cv2.matchTemplate',side_effect=AssertionError('No possible grey body')):
            self.assertIsNone(s.connection_lost_retry_position(frame))

    def test_possible_grey_body_survives_gate_at_edges_and_colour_limits(self):
        for location in ((0,0),(668,218)):
            for colour in ((33,33,33),(94,94,94),(34,33,33),(94,93,94)):
                frame=np.full((720,1280,3),colour,np.uint8)
                frame[410:475,320:512]=(20,160,190)
                template=np.full((26,48,3),220,np.uint8)
                score=np.zeros((219,669),np.float32)
                score[location[1],location[0]]=.99
                with patch('state_finder.load_template',return_value=template),patch('state_finder.cv2.matchTemplate',return_value=score):
                    self.assertIsNotNone(s.connection_lost_retry_position(frame),(location,colour))

    def test_absent_upgrade_hand_and_confirmation_skip_large_titles(self):
        frame=np.zeros((720,1280,3),np.uint8)
        original=o.localized
        def localized(image,encoded,*args):
            self.assertNotIn(encoded,(o.UPGRADE_TWO_TITLE,o.SHELLY_DETAIL_NAME,o.UPGRADE_INFO))
            return original(image,encoded,*args)
        with patch('onboarding.localized',side_effect=localized):
            self.assertIsNone(o.guided_upgrade(frame))
            self.assertIsNone(o.instruction_confirm(frame))
        self.assertIsNone(o.guided_upgrade(np.zeros((0,0,3),np.uint8)))
