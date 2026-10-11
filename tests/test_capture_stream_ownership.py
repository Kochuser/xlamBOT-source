"""Late decoder deliveries must not prove recovery of a replacement stream."""
import threading
import unittest
from unittest.mock import Mock, patch

from test_runtime_consistency import WindowController, scrcpy


class Stream:
    def __init__(self, deliver):
        self.deliver = deliver
        self.listener = None
        self.alive = True

    def add_listener(self, event, listener):
        self.listener = listener

    def start(self, threaded):
        self.deliver(self)

    def stop(self):
        self.alive = False


class CaptureOwnershipTests(unittest.TestCase):
    def controller(self):
        controller = WindowController.__new__(WindowController)
        controller.frame_lock = threading.Lock()
        controller.scrcpy_client = Mock()
        controller.device = Mock()
        controller.device.get_state.return_value = 'device'
        controller.last_frame = None
        controller.last_frame_time = 0.
        controller._capture_count = 0
        controller._capture_window = 0.
        controller.capture_fps = 0.
        controller.release_all_inputs = Mock()
        return controller

    def clock(self):
        now = [100.]
        def sleep(delay):
            now[0] += delay
        return patch.object(__import__('time'), 'time', side_effect=lambda: now[0]), patch.object(__import__('time'), 'sleep', side_effect=sleep)

    def test_old_decoder_frame_cannot_restore_replacement_without_video(self):
        controller = self.controller()
        first_frame, old_late_frame = object(), object()
        first = Stream(lambda stream: stream.listener(first_frame))
        second = Stream(lambda stream: first.listener(old_late_frame))
        controller._create_scrcpy_client = Mock(side_effect=[first, second])
        clock, sleep = self.clock()
        with patch.object(scrcpy, 'EVENT_FRAME', 'frame', create=True), clock, sleep:
            self.assertTrue(controller.reconnect_scrcpy(max_retries=1))
            self.assertIs(controller.get_latest_frame()[0], first_frame)
            self.assertFalse(controller.reconnect_scrcpy(max_retries=1))
            self.assertEqual(controller.get_latest_frame(), (None, 0.))

    def test_current_stream_accepts_frame_after_rejected_old_delivery(self):
        controller = self.controller()
        first_frame, current_frame = object(), object()
        first = Stream(lambda stream: stream.listener(first_frame))
        def deliver_current(stream):
            first.listener(object())
            stream.listener(current_frame)
        second = Stream(deliver_current)
        controller._create_scrcpy_client = Mock(side_effect=[first, second])
        clock, sleep = self.clock()
        with patch.object(scrcpy, 'EVENT_FRAME', 'frame', create=True), clock, sleep:
            self.assertTrue(controller.reconnect_scrcpy(max_retries=1))
            self.assertTrue(controller.reconnect_scrcpy(max_retries=1))
            self.assertIs(controller.get_latest_frame()[0], current_frame)

    def test_frame_during_stop_cannot_restore_silent_new_stream(self):
        controller = self.controller()
        first = Stream(lambda stream: stream.listener(object()))
        first.stop = lambda: first.listener(object())
        second = Stream(lambda stream: None)
        controller._create_scrcpy_client = Mock(side_effect=[first, second])
        clock, sleep = self.clock()
        with patch.object(scrcpy, 'EVENT_FRAME', 'frame', create=True), clock, sleep:
            self.assertTrue(controller.reconnect_scrcpy(max_retries=1))
            self.assertFalse(controller.reconnect_scrcpy(max_retries=1))
            self.assertEqual(controller.get_latest_frame(), (None, 0.))

    def test_one_frame_followed_by_disconnect_is_not_restored_feed(self):
        controller = self.controller()
        def disconnect(stream):
            stream.listener(object())
            stream.alive = False
        controller._create_scrcpy_client = Mock(return_value=Stream(disconnect))
        clock, sleep = self.clock()
        with patch.object(scrcpy, 'EVENT_FRAME', 'frame', create=True), clock, sleep:
            self.assertFalse(controller.reconnect_scrcpy(max_retries=1))

    def test_delayed_stop_thread_stops_its_client_not_new_connection(self):
        controller = self.controller()
        old_client, new_client = Mock(), Mock()
        controller.scrcpy_client = old_client
        tasks = []
        def thread_factory(target, **kwargs):
            tasks.append(target)
            return Mock(is_alive=Mock(return_value=True))
        with patch.object(threading, 'Thread', side_effect=thread_factory):
            controller.stop_scrcpy_with_timeout()
        controller.scrcpy_client = new_client
        tasks[0]()
        old_client.stop.assert_called_once()
        new_client.stop.assert_not_called()

    def test_close_discards_frame_and_rejects_delayed_callback(self):
        controller = self.controller()
        client = Stream(lambda stream: stream.listener(object()))
        controller._create_scrcpy_client = Mock(return_value=client)
        controller.debug_view = Mock()
        controller.stop_scrcpy_with_timeout = Mock()
        clock, sleep = self.clock()
        with patch.object(scrcpy, 'EVENT_FRAME', 'frame', create=True), clock, sleep:
            self.assertTrue(controller.reconnect_scrcpy(max_retries=1))
            controller.close()
            client.listener(object())
            self.assertEqual(controller.get_latest_frame(), (None, 0.))
            self.assertFalse(controller.reconnect_scrcpy(max_retries=1))
            self.assertEqual(controller._create_scrcpy_client.call_count, 1)


if __name__ == '__main__':
    unittest.main()
