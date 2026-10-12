import unittest
from types import SimpleNamespace
import numpy as np
from gas_boundary import GasBoundary
from gas_guard import improving_escape
from play import Play

class GasBoundaryTests(unittest.TestCase):
    def test_live_isolated_detections_do_not_create_a_closing_front(self):
        mask=np.zeros((720,1280),np.uint8)
        for x1,y1,x2,y2 in [(33,520,121,581),(522,453,584,502),(86,614,118,645),(0,551,23,591)]:
            mask[y1:y2,x1:x2]=255
        p=GasBoundary()
        self.assertIsNone(p.observe(mask,[605,325,655,375],41,lambda v,d:False))
        self.assertFalse(p.active)
        self.assertEqual(p.report['reason'],'isolated_detections')
        self.assertGreater(np.count_nonzero(mask),0)

    def test_contact_with_isolated_detection_keeps_emergency_escape(self):
        mask=np.zeros((240,400),np.uint8);mask[80:130,100:145]=255
        p=GasBoundary();box=[110,100,130,120]
        v=p.observe(mask,box,20,lambda v,d:False)
        self.assertTrue(p.active);self.assertIn('exit_reach',p.report)
        self.assertTrue(improving_escape(mask,box,v,p.report['exit_reach']))

    def test_buffer_uses_extended_front_instead_of_closer_isolated_patch(self):
        mask=np.zeros((240,400),np.uint8);mask[:,:140]=255
        mask[100:120,190:205]=255
        p=GasBoundary();v=p.observe(mask,[160,100,180,120],20,lambda v,d:False)
        self.assertGreater(v[0],.8)
        # The final path guard still sees the isolated obstacle.
        self.assertEqual(np.count_nonzero(mask[100:120,190:205]),300)

    def test_front_qualification_releases_latch_when_only_fragments_remain(self):
        p=GasBoundary();mask=np.zeros((240,400),np.uint8);mask[:,:140]=255
        p.observe(mask,[160,100,180,120],20,lambda v,d:False)
        fragment=np.zeros_like(mask);fragment[90:120,125:140]=255
        self.assertIsNone(p.observe(fragment,[160,100,180,120],20,lambda v,d:False))
        self.assertFalse(p.active)

    def test_advancing_front_triggers_before_contact_and_camera_translation_is_invariant(self):
        p=GasBoundary();mask=np.zeros((240,400),np.uint8);mask[:,:140]=255
        self.assertIsNone(p.observe(mask,[200,100,220,120],20,lambda v,d:False))
        mask=np.zeros_like(mask);mask[:,:180]=255
        v=p.observe(mask,[200,100,220,120],20,lambda v,d:False)
        self.assertGreater(v[0],.8);self.assertEqual(np.count_nonzero(mask[100:120,200:220]),0)
        clearance=p.report['clearance_px']
        moved=np.zeros_like(mask);moved[:,:230]=255
        v=p.observe(moved,[250,100,270,120],20,lambda v,d:False)
        self.assertGreater(v[0],.8);self.assertEqual(clearance,p.report['clearance_px'])

    def test_final_play_guard_allows_only_verified_decreasing_escape(self):
        p=Play.__new__(Play);p.gas_mask=np.zeros((240,400),np.uint8);p.gas_mask[:,:200]=255
        p.gas_in_danger=True;p.gas_reach=3;p.gas_sensitivity=.05
        p.get_actual_player_box=lambda b:b;p.is_path_blocked=lambda *a,**kw:False
        p.gas_direction_share=lambda *a:1.
        p.gas_boundary=GasBoundary();box=[110,100,130,120]
        v=p.gas_boundary.observe(p.gas_mask,box,20,lambda v,d:False)
        self.assertTrue(p.safe_memory_step(v,box,[]))
        self.assertFalse(p.safe_memory_step((-v[0],-v[1]),box,[]))

    def test_front_retreat_starts_before_body_contact(self):
        mask=np.zeros((240,400),np.uint8);mask[:,:140]=255
        p=GasBoundary();v=p.observe(mask,[160,100,180,120],20,lambda v,d:False)
        self.assertGreater(v[0],.8);self.assertTrue(p.active)
        self.assertEqual(np.count_nonzero(mask[100:120,160:180]),0)

    def test_right_and_corner_fronts_choose_observed_clean_interior(self):
        for right in (True,False):
            mask=np.zeros((240,400),np.uint8)
            if right:mask[:,195:]=255
            else:mask[:95,:]=255;mask[:,:150]=255
            v=GasBoundary().observe(mask,[160,100,180,120],20,lambda v,d:False)
            if right:self.assertLess(v[0],-.8)
            else:self.assertGreater(v[0],0);self.assertGreater(v[1],0)

    def test_margin_hysteresis_and_empty_measurement_release_retreat(self):
        p=GasBoundary();mask=np.zeros((240,400),np.uint8);mask[:,:140]=255
        p.observe(mask,[160,100,180,120],20,lambda v,d:False)
        p.observe(mask,[185,100,205,120],20,lambda v,d:False);self.assertTrue(p.active)
        self.assertIsNone(p.observe(mask,[220,100,240,120],20,lambda v,d:False))
        self.assertIsNone(p.observe(np.zeros_like(mask),[160,100,180,120],20,lambda v,d:False))
        self.assertIsNone(p.observe(None,[160,100,180,120],20,lambda v,d:False))

    def test_narrow_endgame_holds_deepest_clean_position(self):
        mask=np.zeros((240,400),np.uint8);mask[:,:145]=255;mask[:,195:]=255
        self.assertEqual(GasBoundary().observe(mask,[160,100,180,120],20,lambda v,d:False),(0.,0.))

    def test_walls_and_one_pixel_front_survive_route_and_resolution_checks(self):
        mask=np.zeros((240,400),np.uint8);mask[:,:140]=255
        self.assertEqual(GasBoundary().observe(mask,[160,100,180,120],20,lambda v,d:v[0]>.1),(0.,0.))
        mask=np.zeros((720,1280),np.uint8);mask[:,568:569]=255
        self.assertGreater(GasBoundary().observe(mask,[580,300,600,320],20,lambda v,d:False)[0],.8)

    def test_existing_gas_escape_cannot_cross_more_gas_or_unseen_ground(self):
        mask=np.zeros((240,400),np.uint8);mask[:,:130]=255;box=[110,100,130,120]
        self.assertTrue(improving_escape(mask,box,(1,0),3))
        self.assertFalse(improving_escape(mask,box,(-1,0),3))
        self.assertFalse(improving_escape(mask,box,(0,-1),20))
        mask[:,165:180]=255
        self.assertFalse(improving_escape(mask,box,(1,0),3))

    def test_deep_gas_uses_visible_exit_instead_of_screen_midpoint(self):
        mask=np.zeros((240,400),np.uint8);mask[:,200:]=255
        p=GasBoundary();v=p.observe(mask,[270,100,290,120],20,lambda v,d:False)
        self.assertLess(v[0],-.8);self.assertGreater(p.report['exit_reach'],3)
        self.assertTrue(improving_escape(mask,[270,100,290,120],v,p.report['exit_reach']))

    def test_play_prioritizes_buffer_and_failed_detector_cannot_retain_it(self):
        p=Play.__new__(Play);p.gas_mask=np.zeros((240,400),np.uint8);p.gas_mask[:,:140]=255
        p.gas_in_danger=False;p.gas_detection_ok=True;p.gas_player_box=[160,100,180,120]
        p.refresh_gas=lambda *a:None;p.get_actual_player_box=lambda b:b
        p.TILE_SIZE=20;p.window_controller=SimpleNamespace(scale_factor=1)
        p.is_path_blocked=lambda *a,**kw:False
        self.assertGreater(p.avoid_gas(image=np.zeros((240,400,3),np.uint8),current_time=10)[0],.8)
        self.assertFalse(p.gas_in_danger)
        p.gas_detection_ok=False
        self.assertIsNone(p.avoid_gas(image=np.zeros((240,400,3),np.uint8),current_time=11))
        self.assertFalse(p.gas_boundary.active)
