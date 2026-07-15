from __future__ import annotations

import copy
import json

from scripts.export_openapi import check_schema, export_schema


def test_contract_check_rejects_removed_response_field(tmp_path):
    stale_schema = copy.deepcopy(export_schema())
    data_stats = stale_schema["components"]["schemas"]["DataStats"]
    del data_stats["properties"]["database"]
    contract = tmp_path / "openapi.json"
    contract.write_text(
        json.dumps(stale_schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    matches, diff = check_schema(contract)

    assert matches is False
    assert '"database"' in diff
