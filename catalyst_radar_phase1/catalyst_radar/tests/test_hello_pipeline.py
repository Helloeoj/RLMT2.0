import json
import os
import tempfile
import unittest
from pathlib import Path

from catalyst_radar.config.settings import Settings
from catalyst_radar.pipeline.runner import PipelineRunner


class TestHelloPipeline(unittest.TestCase):
    def test_hello_pipeline_creates_outputs(self):
        repo_root = Path(__file__).resolve().parents[1]
        fixtures = repo_root / "data" / "fixtures" / "stub_events.json"
        self.assertTrue(fixtures.exists(), str(fixtures))

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            ledger = out_dir / "event_ledger.jsonl"
            os.environ["CATRADAR_OUT_DIR"] = str(out_dir)
            os.environ["CATRADAR_LEDGER_PATH"] = str(ledger)
            os.environ["CATRADAR_MIN_CONFIDENCE"] = "MEDIUM"

            settings = Settings()
            runner = PipelineRunner(settings=settings, fixtures_path=str(fixtures))
            result = runner.run()

            self.assertTrue(Path(result.ledger_path).exists())
            self.assertTrue(Path(result.watchlist_path).exists())

            wl = json.loads(Path(result.watchlist_path).read_text(encoding="utf-8"))
            self.assertIn("watchlist", wl)
            self.assertIn("digest", wl)


if __name__ == "__main__":
    unittest.main()
