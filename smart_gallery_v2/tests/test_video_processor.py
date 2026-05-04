from core.video_processor import VideoKeyframeExtractor


def test_extract_nonexistent():
    v = VideoKeyframeExtractor()
    kf = v.extract("/path/that/does/not/exist.mp4")
    assert isinstance(kf, list) and len(kf) == 0
