from pathlib import Path

from app.parser import parse_creator_videos


def test_parse_creator_videos_extracts_latest_items():
    html = Path("tests/fixtures/douyin_creator_page.html").read_text(encoding="utf-8")

    videos = parse_creator_videos(html, creator_name="Alice")

    assert videos[0].video_id == "7480000000000000001"
    assert videos[0].title == "春天的第一条短片"
    assert videos[0].video_url.startswith("https://www.douyin.com/video/")


def test_parse_creator_videos_sorts_by_publish_time_not_pinned_order():
    html = '''
    <html>
      <body>
        <script id="RENDER_DATA" type="application/json">
          {
            "aweme_list": [
              {
                "aweme_id": "old-top",
                "desc": "置顶旧视频",
                "create_time": 1700000000,
                "is_top": 1,
                "share_url": "https://www.douyin.com/video/old-top"
              },
              {
                "aweme_id": "newest-normal",
                "desc": "真正最新视频",
                "create_time": 1800000000,
                "is_top": 0,
                "share_url": "https://www.douyin.com/video/newest-normal"
              },
              {
                "aweme_id": "mid-normal",
                "desc": "中间视频",
                "create_time": 1750000000,
                "is_top": 0,
                "share_url": "https://www.douyin.com/video/mid-normal"
              }
            ]
          }
        </script>
      </body>
    </html>
    '''

    videos = parse_creator_videos(html, creator_name="Alice")

    assert [video.video_id for video in videos] == [
        "newest-normal",
        "mid-normal",
        "old-top",
    ]
