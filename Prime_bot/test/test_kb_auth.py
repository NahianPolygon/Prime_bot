from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import api
import auth_store
import kb_runtime


class KnowledgeBaseAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.banks_root = self.root / "banks"
        self.runtime_config = self.root / "runtime_kb_config.json"
        self.auth_store_path = self.root / "kb_users.json"

        self._patchers = [
            patch.object(api, "PROJECT_ROOT", self.root),
            patch.object(api, "BANKS_ROOT", self.banks_root),
            patch.object(api, "ingest_markdown_path", side_effect=self.fake_ingest_markdown_path),
            patch.object(api, "ingest_company_text", side_effect=self.fake_ingest_company_text),
            patch.object(kb_runtime, "RUNTIME_CONFIG_PATH", self.runtime_config),
            patch.object(auth_store, "AUTH_STORE_PATH", self.auth_store_path),
            patch.object(auth_store, "AUTH_SECRET", "test-secret"),
        ]
        for patcher in self._patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        api._cfg.setdefault("llm", {})["warmup_on_start"] = False
        self.ingest_calls = []

        self._write_markdown(
            "prime_bank",
            "conventional",
            "i_need_a_credit_card",
            "prime_card",
            "# Prime Card\n\nPrime bank content.\n",
        )
        self._write_markdown(
            "city_bank",
            "conventional",
            "i_need_a_credit_card",
            "city_card",
            "# City Card\n\nCity bank content.\n",
        )
        kb_runtime.save_runtime_state({
            "active_bank": "prime_bank",
            "collections": kb_runtime.build_collection_map("prime_bank"),
        })
        auth_store.ensure_default_super_admin(api.ADMIN_USERNAME, api.ADMIN_PASSWORD)
        self.client = TestClient(api.app)

    def tearDown(self):
        self.client.close()
        self.tmpdir.cleanup()

    def fake_ingest_markdown_path(self, md_path, replace_existing=True):
        return {"chunk_count": 1, "collections": ["test_collection"], "path": str(md_path)}

    def fake_ingest_company_text(self, **kwargs):
        self.ingest_calls.append(kwargs)
        bank_slug = kwargs["company_name"]
        markdown_path = (
            self.banks_root
            / bank_slug
            / "conventional"
            / "credit"
            / "i_need_a_credit_card"
            / "generated_doc.md"
        )
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text("# Generated Doc\n\nGenerated content.\n", encoding="utf-8")
        return {
            "bank_slug": bank_slug,
            "company_slug": bank_slug,
            "document_type": kwargs["document_type"],
            "banking_type": kwargs["banking_type"],
            "chunk_count": 1,
            "collections": [f"{bank_slug}_collection"],
            "markdown_paths": [str(markdown_path)],
        }

    def _write_markdown(self, bank_slug: str, banking_type: str, document_type: str, file_stem: str, content: str):
        md_path = self.banks_root / bank_slug / banking_type / "credit" / document_type / f"{file_stem}.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(content, encoding="utf-8")
        return md_path

    def _login_super_admin(self) -> str:
        res = self.client.post("/admin/login", json={
            "username": api.ADMIN_USERNAME,
            "password": api.ADMIN_PASSWORD,
        })
        self.assertEqual(res.status_code, 200)
        return res.json()["token"]

    def _create_bank_admin(self, super_token: str, bank_name: str, username: str, password: str):
        res = self.client.post(
            "/admin/kb/bank-users",
            headers={"Authorization": f"Bearer {super_token}"},
            json={"bank_name": bank_name, "username": username, "password": password},
        )
        self.assertEqual(res.status_code, 200)

    def _login_bank_admin(self, username: str, password: str) -> str:
        res = self.client.post("/bank/login", json={"username": username, "password": password})
        self.assertEqual(res.status_code, 200)
        return res.json()["token"]

    def test_kb_studio_requires_authentication(self):
        self.assertEqual(self.client.get("/kb/studio/context").status_code, 401)
        self.assertEqual(
            self.client.get("/kb/studio/file", params={"path": str(self.banks_root / "prime_bank" / "conventional" / "credit" / "i_need_a_credit_card" / "prime_card.md")}).status_code,
            401,
        )
        self.assertEqual(
            self.client.post("/kb/studio/ingest-text", json={
                "document_title": "Test Card",
                "document_type": "i_need_a_credit_card",
                "banking_type": "conventional",
                "raw_text": "raw",
            }).status_code,
            401,
        )

    def test_bank_admin_sees_only_own_workspace(self):
        super_token = self._login_super_admin()
        self._create_bank_admin(super_token, "city_bank", "city_admin", "StrongPass1")
        bank_token = self._login_bank_admin("city_admin", "StrongPass1")

        context_res = self.client.get("/kb/studio/context", headers={"Authorization": f"Bearer {bank_token}"})
        self.assertEqual(context_res.status_code, 200)
        data = context_res.json()
        self.assertEqual(data["active_bank"], "city_bank")
        self.assertEqual(len(data["files"]), 1)
        self.assertIn("city_bank", data["files"][0]["path"])

    def test_bank_admin_cannot_open_other_bank_file(self):
        super_token = self._login_super_admin()
        self._create_bank_admin(super_token, "city_bank", "city_admin", "StrongPass1")
        bank_token = self._login_bank_admin("city_admin", "StrongPass1")
        other_bank_path = str(
            self.banks_root / "prime_bank" / "conventional" / "credit" / "i_need_a_credit_card" / "prime_card.md"
        )

        res = self.client.get(
            "/kb/studio/file",
            params={"path": other_bank_path},
            headers={"Authorization": f"Bearer {bank_token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_bank_ingest_uses_logged_in_bank_not_global_active_bank(self):
        super_token = self._login_super_admin()
        self._create_bank_admin(super_token, "city_bank", "city_admin", "StrongPass1")
        bank_token = self._login_bank_admin("city_admin", "StrongPass1")

        res = self.client.post(
            "/kb/studio/ingest-text",
            headers={"Authorization": f"Bearer {bank_token}"},
            json={
                "document_title": "City New Card",
                "document_type": "i_need_a_credit_card",
                "banking_type": "conventional",
                "raw_text": "raw input",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.ingest_calls[-1]["company_name"], "city_bank")


if __name__ == "__main__":
    unittest.main()
