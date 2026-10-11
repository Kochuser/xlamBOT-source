import concurrent.futures
import gc
from pathlib import Path
import tempfile
import threading
import unittest
import model_sessions


class Session:
    pass


class ModelSessionsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'weights.onnx'
        self.path.write_bytes(b'weights-one')

    def acquire(self, factory=Session, providers=('CPUExecutionProvider',), threads=2):
        return model_sessions.acquire(self.path, providers, threads, factory)

    def test_concurrent_owners_load_weights_once(self):
        calls = []
        gate = threading.Barrier(10)
        def factory():
            calls.append(1)
            return Session()
        def load(_):
            gate.wait()
            return self.acquire(factory)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(load, range(10)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len({id(s) for s,_ in results}), 1)
        self.assertEqual(sum(shared for _,shared in results), 9)

    def test_model_replacement_with_same_size_and_timestamp_invalidates(self):
        import os
        first,_ = self.acquire()
        stat = self.path.stat()
        self.path.write_bytes(b'weights-two')
        os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        second,shared = self.acquire()
        self.assertIsNot(first, second)
        self.assertFalse(shared)

    def test_execution_provider_and_threads_remain_separate(self):
        cpu,_ = self.acquire()
        gpu,_ = self.acquire(providers=('DmlExecutionProvider','CPUExecutionProvider'))
        fewer,_ = self.acquire(threads=1)
        self.assertIsNot(cpu,gpu)
        self.assertIsNot(cpu,fewer)

    def test_unused_weights_are_released(self):
        import weakref
        first,_ = self.acquire()
        reference = weakref.ref(first)
        del first
        gc.collect()
        self.assertIsNone(reference())
        _,shared = self.acquire()
        self.assertFalse(shared)

    def test_failed_initialization_does_not_poison_cache(self):
        def fail():raise RuntimeError('device initialization failed')
        with self.assertRaises(RuntimeError):self.acquire(fail)
        good,shared=self.acquire()
        self.assertIsInstance(good,Session)
        self.assertFalse(shared)

    def test_replacement_during_initialization_is_not_cached_under_old_weights(self):
        def replace():
            self.path.write_bytes(b'weights-two')
            return Session()
        old,_=self.acquire(replace)
        self.path.write_bytes(b'weights-one')
        current,shared=self.acquire()
        self.assertIsNot(old,current)
        self.assertFalse(shared)

    def test_detector_buffers_and_gpu_fallback_are_owner_local(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import numpy as np
        import detect
        class RuntimeSession(Session):
            def __init__(self, provider):
                self.provider=provider
                self.fallback_disabled=False
            def disable_fallback(self):self.fallback_disabled=True
            def get_providers(self):return [self.provider]
            def get_inputs(self):return [SimpleNamespace(name='images')]
            def run(self,_outputs,_inputs):
                if self.provider=='DmlExecutionProvider':raise RuntimeError('GPU unavailable')
                return [np.empty((1,6,0),dtype=np.float32)]
        created=[]
        def factory(_path,sess_options,providers):
            session=RuntimeSession(providers[0]);created.append(session);return session
        config={'used_threads':2,'cpu_or_gpu':'gpu'}
        with patch.object(detect,'load_toml_as_dict',return_value=config),patch.object(detect.ort,'get_available_providers',return_value=['DmlExecutionProvider','CPUExecutionProvider']),patch.object(detect.ort,'InferenceSession',side_effect=factory):
            first=detect.Detect(str(self.path),classes=['player'])
            second=detect.Detect(str(self.path),classes=['enemy'])
            self.assertIs(first.model,second.model)
            self.assertTrue(first.model.fallback_disabled)
            self.assertFalse(np.shares_memory(first._padded_img_buffer,second._padded_img_buffer))
            second_buffer=second._padded_img_buffer.copy()
            first.detect_objects(np.zeros((40,40,3),dtype=np.uint8))
            self.assertEqual(first.device,'CPUExecutionProvider')
            self.assertEqual(second.device,'DmlExecutionProvider')
            self.assertIsNot(first.model,second.model)
            self.assertEqual(len(created),2)
            np.testing.assert_array_equal(second._padded_img_buffer,second_buffer)
            self.assertEqual(first.classes,['player'])
            self.assertEqual(second.classes,['enemy'])


if __name__=='__main__':unittest.main()
