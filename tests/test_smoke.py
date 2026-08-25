"""冒烟测试：包可导入、CLI 入口存在。"""

import assistant
from assistant import cli


def test_package_importable() -> None:
    assert assistant.__version__ == "0.1.0"


def test_cli_entry_exists() -> None:
    assert callable(cli.main)
