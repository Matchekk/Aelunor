import tempfile
import unittest
from pathlib import Path

from app.repositories.campaign_repository import CampaignRepository
from app.services.campaigns import persistence


class CampaignPersistenceServiceTests(unittest.TestCase):
    def test_json_helpers_preserve_repository_format_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            campaigns_dir = data_dir / "campaigns"
            repo = CampaignRepository(data_dir=str(data_dir), campaigns_dir=str(campaigns_dir))

            path = persistence.campaign_path(repo, "camp_1")
            self.assertEqual(path, str(campaigns_dir / "camp_1.json"))

            payload = {"campaign_meta": {"campaign_id": "camp_1"}, "title": "Aelunor"}
            persistence.save_json(repo, path, payload)

            self.assertEqual(persistence.load_json(repo, path), payload)
            self.assertEqual(persistence.list_campaign_ids(repo), ["camp_1"])
            self.assertTrue(Path(path).read_text(encoding="utf-8").endswith("\n"))


if __name__ == "__main__":
    unittest.main()
