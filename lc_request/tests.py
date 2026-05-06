"""
Unit tests for the lc_request module.

Covers:
- LCRequestService coercion helpers
- LCFileManager queryset methods
- LcRequestProxy / LcDetailsProxy / LcFilesProxy entity logic
- Constants field maps
"""
from decimal import Decimal
from datetime import date

from django.test import TestCase

from lc_request.services import LCRequestService
from lc_request.entities import LcRequestProxy, LcDetailsProxy, LcFilesProxy
from lc_request import Constants


# ── LCRequestService — coercion helpers ───────────────────────────────────────

class TestCoerceInt(TestCase):
    """Unit tests for LCRequestService._coerce_int."""

    def setUp(self):
        self.service = LCRequestService()

    def test_valid_integer_string(self):
        assert self.service._coerce_int("90") == 90

    def test_valid_integer(self):
        assert self.service._coerce_int(30) == 30

    def test_empty_string_returns_none(self):
        assert self.service._coerce_int("") is None

    def test_null_sentinel_returns_none(self):
        assert self.service._coerce_int("null") is None

    def test_undefined_sentinel_returns_none(self):
        assert self.service._coerce_int("undefined") is None

    def test_none_returns_none(self):
        assert self.service._coerce_int(None) is None

    def test_invalid_string_returns_none(self):
        assert self.service._coerce_int("abc") is None

    def test_float_string_truncates(self):
        assert self.service._coerce_int("90.9") == 90


class TestCoerceDecimal(TestCase):
    """Unit tests for LCRequestService._coerce_decimal."""

    def setUp(self):
        self.service = LCRequestService()

    def test_valid_decimal_string(self):
        assert self.service._coerce_decimal("8.5") == Decimal("8.5")

    def test_valid_integer_string(self):
        assert self.service._coerce_decimal("100") == Decimal("100")

    def test_empty_string_returns_none(self):
        assert self.service._coerce_decimal("") is None

    def test_null_sentinel_returns_none(self):
        assert self.service._coerce_decimal("null") is None

    def test_none_returns_none(self):
        assert self.service._coerce_decimal(None) is None

    def test_invalid_string_returns_none(self):
        assert self.service._coerce_decimal("abc") is None


class TestCoerceDate(TestCase):
    """Unit tests for LCRequestService._coerce_date."""

    def setUp(self):
        self.service = LCRequestService()

    def test_ocr_format_dd_mm_yyyy(self):
        result = self.service._coerce_date("15.06.2024")
        assert result == date(2024, 6, 15)

    def test_iso_format_yyyy_mm_dd(self):
        result = self.service._coerce_date("2024-06-15")
        assert result == date(2024, 6, 15)

    def test_empty_string_returns_none(self):
        assert self.service._coerce_date("") is None

    def test_invalid_date_sentinel_returns_none(self):
        assert self.service._coerce_date("Invalid Date") is None

    def test_none_returns_none(self):
        assert self.service._coerce_date(None) is None

    def test_invalid_format_returns_none(self):
        assert self.service._coerce_date("not-a-date") is None


# ── Constants — field maps ────────────────────────────────────────────────────

class TestConstantsFieldMaps(TestCase):
    """Unit tests for Constants field map integrity."""

    def test_ocr_field_map_values_are_valid_model_fields(self):
        """Every value in OCR_FIELD_MAP must appear in LC_DETAIL_FIELDS."""
        for ocr_key, model_field in Constants.OCR_FIELD_MAP.items():
            assert model_field in Constants.LC_DETAIL_FIELDS, (
                f"OCR key '{ocr_key}' maps to '{model_field}' "
                f"which is not in LC_DETAIL_FIELDS"
            )

    def test_full_field_map_contains_all_ocr_keys(self):
        """FULL_FIELD_MAP must contain every key from OCR_FIELD_MAP."""
        for key in Constants.OCR_FIELD_MAP:
            assert key in Constants.FULL_FIELD_MAP, (
                f"OCR key '{key}' missing from FULL_FIELD_MAP"
            )

    def test_full_field_map_contains_model_field_passthrough(self):
        """FULL_FIELD_MAP must accept model field names as keys (pass-through)."""
        for model_field in Constants.OCR_FIELD_MAP.values():
            assert model_field in Constants.FULL_FIELD_MAP, (
                f"Model field '{model_field}' not in FULL_FIELD_MAP as pass-through"
            )

    def test_ocr_date_fields_are_subset_of_lc_detail_fields(self):
        """Every date field must be a valid LC detail field."""
        for field in Constants.OCR_DATE_FIELDS:
            assert field in Constants.LC_DETAIL_FIELDS, (
                f"Date field '{field}' not in LC_DETAIL_FIELDS"
            )

    def test_status_choices_cover_all_status_constants(self):
        """STATUS_CHOICES must include all defined status constants."""
        status_values = [s[0] for s in Constants.STATUS_CHOICES]
        assert Constants.STATUS_DRAFT in status_values
        assert Constants.STATUS_SUBMITTED in status_values
        assert Constants.STATUS_SYNCED in status_values


# ── LcRequestProxy — entity logic ────────────────────────────────────────────

class TestLcRequestProxyStatus(TestCase):
    """Unit tests for LcRequestProxy status methods."""

    def _make_proxy(self, status):
        """Create an unsaved LcRequestProxy with the given status."""
        obj = LcRequestProxy()
        obj.request_status = status
        return obj

    def test_is_draft_true(self):
        obj = self._make_proxy(Constants.STATUS_DRAFT)
        assert obj.is_draft() is True

    def test_is_draft_false(self):
        obj = self._make_proxy(Constants.STATUS_SUBMITTED)
        assert obj.is_draft() is False

    def test_is_submitted_true(self):
        obj = self._make_proxy(Constants.STATUS_SUBMITTED)
        assert obj.is_submitted() is True

    def test_is_synced_true(self):
        obj = self._make_proxy(Constants.STATUS_SYNCED)
        assert obj.is_synced() is True

    def test_can_edit_draft(self):
        obj = self._make_proxy(Constants.STATUS_DRAFT)
        assert obj.can_edit() is True

    def test_can_edit_submitted(self):
        obj = self._make_proxy(Constants.STATUS_SUBMITTED)
        assert obj.can_edit() is True

    def test_cannot_edit_synced(self):
        obj = self._make_proxy(Constants.STATUS_SYNCED)
        assert obj.can_edit() is False

    def test_mark_as_synced(self):
        obj = self._make_proxy(Constants.STATUS_SUBMITTED)
        obj.mark_as_synced("INW001", "LC001")
        assert obj.request_status == Constants.STATUS_SYNCED
        assert obj.inward_no == "INW001"
        assert obj.lc_ref_no == "LC001"


# ── LcDetailsProxy — entity logic ────────────────────────────────────────────

class TestLcDetailsProxyFlags(TestCase):
    """Unit tests for LcDetailsProxy extracted_flag methods."""

    def _make_proxy(self, flag):
        obj = LcDetailsProxy()
        obj.extracted_flag = flag
        return obj

    def test_is_ocr_extracted_y(self):
        obj = self._make_proxy('Y')
        assert obj.is_ocr_extracted() is True

    def test_is_ocr_extracted_n(self):
        obj = self._make_proxy('N')
        assert obj.is_ocr_extracted() is False

    def test_is_user_editable_n(self):
        obj = self._make_proxy('N')
        assert obj.is_user_editable() is True

    def test_is_user_editable_y(self):
        obj = self._make_proxy('Y')
        assert obj.is_user_editable() is False


# ── LcFilesProxy — entity logic ──────────────────────────────────────────────

class TestLcFilesProxyCategory(TestCase):
    """Unit tests for LcFilesProxy category methods."""

    def _make_proxy(self, category, status='active'):
        obj = LcFilesProxy()
        obj.category = category
        obj.status = status
        return obj

    def test_is_primary_document(self):
        obj = self._make_proxy(Constants.LC_DOCUMENT)
        assert obj.is_primary_document() is True

    def test_is_attachment(self):
        obj = self._make_proxy(Constants.LC_ATTACHMENT)
        assert obj.is_attachment() is True

    def test_is_active(self):
        obj = self._make_proxy(Constants.LC_DOCUMENT, status='active')
        assert obj.is_active() is True

    def test_is_not_active(self):
        obj = self._make_proxy(Constants.LC_DOCUMENT, status='archived')
        assert obj.is_active() is False
