from io import BytesIO
from threading import Event
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

from app.utils.images import decode_image
from app.utils import power


class MediaSupportTests(unittest.TestCase):
    def test_standard_images_and_invalid_bytes(self):
        image = np.full((10, 20, 3), 80, dtype=np.uint8)
        ok, encoded = cv2.imencode('.png', image)
        self.assertTrue(ok)
        np.testing.assert_array_equal(decode_image(encoded), image)
        self.assertIsNone(decode_image(b''))
        self.assertIsNone(decode_image(b'not an image'))

    def test_heif_bytes_decode_when_opencv_cannot_read_them(self):
        register_heif_opener(thumbnails=False)
        buffer = BytesIO()
        Image.new('RGB', (20, 10), (255, 0, 0)).save(buffer, format='HEIF', quality=90)
        for options in ({'return_value': None}, {'side_effect': cv2.error('unsupported format')}):
            with self.subTest(options=options), patch('app.utils.images.cv2.imdecode', **options):
                image = decode_image(buffer.getvalue())
            self.assertEqual(image.shape, (10, 20, 3))
            self.assertGreater(int(image[2, 2, 2]), 180)
            self.assertLess(int(image[2, 2, 0]), 60)

    def power_request(self, online):
        kernel = Mock()
        requested = Event()

        def status(pointer):
            pointer._obj.ACLineStatus = int(online)
            return 1

        kernel.GetSystemPowerStatus.side_effect = status
        kernel.SetThreadExecutionState.side_effect = lambda flags: requested.set() or 1
        with patch.object(power.os, 'name', 'nt'), patch.object(power.ctypes, 'WinDLL', return_value=kernel, create=True):
            with power.keep_awake_on_ac():
                self.assertTrue(requested.wait(2))
                first = kernel.SetThreadExecutionState.call_args_list[0].args[0]
                self.assertEqual(first, 0x80000001 if online else 0x80000000)
            self.assertEqual(kernel.SetThreadExecutionState.call_args_list[-1].args[0], 0x80000000)

    def test_power_request_on_ac_is_released_after_worker_exit(self):
        self.power_request(True)

    def test_battery_does_not_receive_keep_awake_request(self):
        self.power_request(False)

    def test_other_platforms_do_not_launch_power_thread(self):
        with patch.object(power.os, 'name', 'posix'), patch.object(power.threading.Thread, 'start') as start:
            with power.keep_awake_on_ac():
                pass
        start.assert_not_called()


if __name__ == '__main__':
    unittest.main()
