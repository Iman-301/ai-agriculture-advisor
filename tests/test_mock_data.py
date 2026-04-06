from pathlib import Path

import config


def test_mock_json_files_exist() -> None:
    assert Path(config.settings.knowledge_base_path).exists()
    assert Path(config.settings.market_prices_path).exists()
    assert Path(config.settings.farmer_profiles_path).exists()
