"""
Tests for pure utility/helper functions in app.py:
  - calculate_distance()
  - calculate_bounding_box()
  - validate_coordinates()
  - validate_heading()
  - format_capture_time()
  - APP_VERSION constant
"""
import pytest
from unittest.mock import patch


# Import the functions under test from app
import app as app_module
from app import (
    calculate_distance,
    calculate_bounding_box,
    validate_coordinates,
    validate_heading,
    format_capture_time,
    APP_VERSION,
    ValidationError,
)


# ---------------------------------------------------------------------------
# calculate_distance
# ---------------------------------------------------------------------------

class TestCalculateDistance:
    def test_same_point_is_zero(self):
        assert calculate_distance(51.5, -0.1, 51.5, -0.1) == 0.0

    def test_known_distance_london_to_paris(self):
        # London (51.5074, -0.1278) to Paris (48.8566, 2.3522) ≈ 340–344 km
        dist = calculate_distance(51.5074, -0.1278, 48.8566, 2.3522)
        assert 338_000 < dist < 346_000, f"Expected ~340–344 km, got {dist}"

    def test_returns_meters_not_km(self):
        # 1 degree of latitude ≈ 111 320 m
        dist = calculate_distance(0.0, 0.0, 1.0, 0.0)
        assert 110_000 < dist < 112_000, f"Expected ~111 320 m, got {dist}"

    def test_result_is_symmetric(self):
        d1 = calculate_distance(51.5, -0.1, 48.9, 2.4)
        d2 = calculate_distance(48.9, 2.4, 51.5, -0.1)
        assert abs(d1 - d2) < 0.001

    def test_result_rounded_to_four_decimal_places(self):
        dist = calculate_distance(51.5074, -0.1278, 48.8566, 2.3522)
        # Check the number of decimal places
        decimal_str = str(dist).split('.')
        assert len(decimal_str) == 1 or len(decimal_str[1]) <= 4


# ---------------------------------------------------------------------------
# calculate_bounding_box
# ---------------------------------------------------------------------------

class TestCalculateBoundingBox:
    def test_returns_four_values(self):
        result = calculate_bounding_box(51.5, -0.1, 1000)
        assert len(result) == 4

    def test_bounding_box_ordering(self):
        min_lat, max_lat, min_lng, max_lng = calculate_bounding_box(51.5, -0.1, 1000)
        assert min_lat < 51.5 < max_lat
        assert min_lng < -0.1 < max_lng

    def test_larger_radius_gives_larger_box(self):
        min1, max1, _, _ = calculate_bounding_box(51.5, -0.1, 500)
        min2, max2, _, _ = calculate_bounding_box(51.5, -0.1, 5000)
        assert (max2 - min2) > (max1 - min1)

    def test_equator_symmetry(self):
        min_lat, max_lat, min_lng, max_lng = calculate_bounding_box(0.0, 0.0, 1000)
        assert abs(max_lat - 0.0) == pytest.approx(abs(0.0 - min_lat), rel=1e-6)
        assert abs(max_lng - 0.0) == pytest.approx(abs(0.0 - min_lng), rel=1e-6)


# ---------------------------------------------------------------------------
# validate_coordinates
# ---------------------------------------------------------------------------

class TestValidateCoordinates:
    def test_valid_coordinates_returned(self):
        lat, lng = validate_coordinates(51.5074, -0.1278)
        assert lat == pytest.approx(51.5074)
        assert lng == pytest.approx(-0.1278)

    def test_string_inputs_are_converted(self):
        lat, lng = validate_coordinates('51.5', '-0.1')
        assert lat == pytest.approx(51.5)
        assert lng == pytest.approx(-0.1)

    def test_boundary_values_accepted(self):
        validate_coordinates(90.0, 180.0)
        validate_coordinates(-90.0, -180.0)
        validate_coordinates(0.0, 0.0)

    def test_latitude_above_90_raises(self):
        with pytest.raises(ValidationError):
            validate_coordinates(91.0, 0.0)

    def test_latitude_below_minus_90_raises(self):
        with pytest.raises(ValidationError):
            validate_coordinates(-91.0, 0.0)

    def test_longitude_above_180_raises(self):
        with pytest.raises(ValidationError):
            validate_coordinates(0.0, 181.0)

    def test_longitude_below_minus_180_raises(self):
        with pytest.raises(ValidationError):
            validate_coordinates(0.0, -181.0)

    def test_non_numeric_raises(self):
        with pytest.raises(ValidationError):
            validate_coordinates('not-a-number', 0.0)

    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_coordinates(None, 0.0)


# ---------------------------------------------------------------------------
# validate_heading
# ---------------------------------------------------------------------------

class TestValidateHeading:
    def test_valid_heading_returned(self):
        assert validate_heading(180.0) == pytest.approx(180.0)

    def test_zero_is_valid(self):
        assert validate_heading(0.0) == pytest.approx(0.0)

    def test_359_is_valid(self):
        assert validate_heading(359.9) == pytest.approx(359.9)

    def test_string_input_converted(self):
        assert validate_heading('90') == pytest.approx(90.0)

    def test_none_returns_none(self):
        assert validate_heading(None) is None

    def test_360_raises(self):
        with pytest.raises(ValidationError):
            validate_heading(360.0)

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            validate_heading(-1.0)

    def test_non_numeric_raises(self):
        with pytest.raises(ValidationError):
            validate_heading('north')


# ---------------------------------------------------------------------------
# format_capture_time
# ---------------------------------------------------------------------------

class TestFormatCaptureTime:
    def test_valid_iso_timestamp(self):
        result = format_capture_time('2024-01-15T10:30:00Z')
        assert result == '15 Jan 2024'

    def test_none_returns_na(self):
        assert format_capture_time(None) == 'N/A'

    def test_empty_string_returns_na(self):
        assert format_capture_time('') == 'N/A'

    def test_invalid_format_returns_original(self):
        result = format_capture_time('not-a-date')
        assert result == 'not-a-date'

    def test_different_date(self):
        result = format_capture_time('2023-12-25T00:00:00Z')
        assert result == '25 Dec 2023'


# ---------------------------------------------------------------------------
# APP_VERSION
# ---------------------------------------------------------------------------

class TestAppVersion:
    def test_version_is_string(self):
        assert isinstance(APP_VERSION, str)

    def test_version_matches_template(self):
        """The context processor must inject app_version to templates."""
        import app as app_module
        with app_module.app.test_request_context('/'):
            ctx = app_module.inject_app_version()
            assert ctx['app_version'] == APP_VERSION

    def test_version_format(self):
        parts = APP_VERSION.split('.')
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
