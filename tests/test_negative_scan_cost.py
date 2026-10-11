import unittest
from unittest.mock import patch

import numpy as np

import disconnect_dialog as disconnect
import onboarding
import screen_evidence


class NegativeScanCostTests(unittest.TestCase):
    def test_unrelated_screen_does_not_search_reload_controls(self):
        frame = np.zeros((720, 1280, 3), np.uint8)
        original = disconnect._match

        def match(image, encoded, *args):
            if encoded in (disconnect.RELOAD, disconnect.RUSSIAN_RELOAD):
                self.fail('Missing dialog title must reject its reload search')
            return original(image, encoded, *args)

        with patch('disconnect_dialog._match', side_effect=match), \
             patch('rejoin_dialog.rejoin_reload_position', return_value=(200, 300)):
            self.assertEqual(disconnect.idle_disconnect_reload_position(frame), (200, 300))

    def test_reward_road_requires_heading_before_large_claim_search(self):
        frame = np.zeros((720, 1280, 3), np.uint8)
        original = onboarding.localized

        def locate(image, encoded, *args):
            if encoded in (onboarding.GUIDE_CLAIM, onboarding.CLAIM_SMALL):
                self.fail('Ordinary scenery must not trigger the large claim search')
            return original(image, encoded, *args)

        with patch('onboarding.localized', side_effect=locate):
            self.assertIsNone(onboarding.first_reward_guide(frame))

    def test_coin_caption_cannot_enable_receipt_without_gold_and_background(self):
        frame = np.full((270, 480, 3), (0, 70, 200), np.uint8)
        glyph = screen_evidence._scaled(screen_evidence.COINS, 81, 25)
        frame[33:58, 200:281] = glyph
        with patch('screen_evidence._find', side_effect=AssertionError('Unnecessary caption scan')):
            self.assertFalse(screen_evidence.coin_reward(frame))
        frame[80:200, 170:310] = (255, 180, 0)
        self.assertTrue(screen_evidence.coin_reward(frame))
        frame[33:58, 200:281] = (0, 70, 200)
        self.assertFalse(screen_evidence.coin_reward(frame))
