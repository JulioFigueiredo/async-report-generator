import csv
import os
import tempfile

import pytest

from app.builders.report_builder import build_report

SALES_COLUMNS = ["date", "product", "quantity", "unit_price", "total"]
INVENTORY_COLUMNS = ["sku", "product", "stock", "min_stock", "status"]
CUSTOMERS_COLUMNS = ["id", "name", "city", "orders", "total_spent"]


@pytest.fixture
def tmp_csv(tmp_path):
    return str(tmp_path / "report.csv")


def read_csv(path: str) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


class TestBuildReportCreatesFile:
    def test_creates_file_at_given_path(self, tmp_csv):
        build_report("sales", "north", "january", tmp_csv)
        assert os.path.isfile(tmp_csv)


class TestSalesReport:
    def test_has_correct_columns(self, tmp_csv):
        build_report("sales", "north", "january", tmp_csv)
        headers, _ = read_csv(tmp_csv)
        assert headers == SALES_COLUMNS

    def test_row_count_between_30_and_100(self, tmp_csv):
        build_report("sales", "southeast", "march", tmp_csv)
        _, rows = read_csv(tmp_csv)
        assert 30 <= len(rows) <= 100

    def test_total_equals_quantity_times_unit_price(self, tmp_csv):
        build_report("sales", "south", "june", tmp_csv)
        _, rows = read_csv(tmp_csv)
        for row in rows:
            quantity = int(row["quantity"])
            unit_price = float(row["unit_price"])
            total = float(row["total"])
            assert total == pytest.approx(quantity * unit_price)


class TestInventoryReport:
    def test_has_correct_columns(self, tmp_csv):
        build_report("inventory", "north", "january", tmp_csv)
        headers, _ = read_csv(tmp_csv)
        assert headers == INVENTORY_COLUMNS

    def test_row_count_between_30_and_100(self, tmp_csv):
        build_report("inventory", "northeast", "july", tmp_csv)
        _, rows = read_csv(tmp_csv)
        assert 30 <= len(rows) <= 100

    def test_status_is_valid_value(self, tmp_csv):
        build_report("inventory", "midwest", "october", tmp_csv)
        _, rows = read_csv(tmp_csv)
        valid_statuses = {"ok", "low", "critical"}
        for row in rows:
            assert row["status"] in valid_statuses


class TestCustomersReport:
    def test_has_correct_columns(self, tmp_csv):
        build_report("customers", "north", "january", tmp_csv)
        headers, _ = read_csv(tmp_csv)
        assert headers == CUSTOMERS_COLUMNS

    def test_row_count_between_30_and_100(self, tmp_csv):
        build_report("customers", "south", "december", tmp_csv)
        _, rows = read_csv(tmp_csv)
        assert 30 <= len(rows) <= 100

    def test_ids_are_unique(self, tmp_csv):
        build_report("customers", "southeast", "february", tmp_csv)
        _, rows = read_csv(tmp_csv)
        ids = [row["id"] for row in rows]
        assert len(ids) == len(set(ids))
