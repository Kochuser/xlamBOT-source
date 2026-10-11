import unittest
import cv2
import numpy as np
from spray_receipt import spray_receipt
from spray_receipt_glyph import SPRAY_TITLE
from reward_receipts import REMAINING
from test_reward_receipts import paste
from state_finder import get_state


def frame(w=1280, h=720):
    f = np.full((720,1280,3), (170,90,200), np.uint8)
    f[:,:300] = (115,50,220)
    f[:,980:] = (245,135,90)
    paste(f, SPRAY_TITLE, 520, 109)
    paste(f, REMAINING, 941, 661)
    f[642:700,1181:1239] = (240,0,0)
    cv2.putText(f, '0', (1194,679), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 3)
    f[330:390,550:720] = (20,20,20)
    return cv2.resize(f, (w,h), interpolation=cv2.INTER_AREA)


class SprayReceiptTests(unittest.TestCase):
    def test_receipt_at_supported_resolutions_uses_existing_owner(self):
        for w,h in ((960,540),(1280,720),(1920,1080)):
            self.assertTrue(spray_receipt(frame(w,h)))
            self.assertEqual(get_state(frame(w,h)), 'reward_received')

    def test_caption_counter_and_item_are_required(self):
        for ys,xs in ((slice(70,190),slice(400,850)),(slice(650,720),slice(900,1175)),(slice(630,720),slice(1180,1280)),(slice(250,520),slice(430,850))):
            f=frame();f[ys,xs]=(170,90,200)
            self.assertFalse(spray_receipt(f))

    def test_ordinary_menu_wrong_backdrop_and_dimmed_modal_are_rejected(self):
        for f in (None,np.zeros((20,20),np.uint8),(frame()*.65).astype(np.uint8)):
            self.assertFalse(spray_receipt(f))
        for side in (slice(0,300),slice(980,1280)):
            f=frame();f[:,side]=(40,40,40)
            self.assertFalse(spray_receipt(f))
