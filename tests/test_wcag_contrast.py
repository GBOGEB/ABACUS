"""Unit tests for WCAG_CONTRAST_CHECKER.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.WCAG_CONTRAST_CHECKER import (
    check_color_pair,
    check_theme_file,
    contrast_ratio,
    hex_to_rgb,
    relative_luminance,
)


class TestColorUtilities:
    def test_hex_to_rgb_6digit(self):
        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)
        assert hex_to_rgb("#0000FF") == (0, 0, 255)
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_hex_to_rgb_3digit(self):
        assert hex_to_rgb("#F00") == (255, 0, 0)
        assert hex_to_rgb("#FFF") == (255, 255, 255)

    def test_hex_to_rgb_no_hash(self):
        assert hex_to_rgb("FF0000") == (255, 0, 0)

    def test_hex_to_rgb_8digit_strips_alpha(self):
        assert hex_to_rgb("#FF0000FF") == (255, 0, 0)

    def test_hex_to_rgb_invalid(self):
        with pytest.raises(ValueError):
            hex_to_rgb("#GG")

    def test_relative_luminance_white(self):
        lum = relative_luminance(255, 255, 255)
        assert abs(lum - 1.0) < 0.001

    def test_relative_luminance_black(self):
        lum = relative_luminance(0, 0, 0)
        assert abs(lum - 0.0) < 0.001


class TestContrastRatio:
    def test_black_on_white(self):
        ratio = contrast_ratio((0, 0, 0), (255, 255, 255))
        assert abs(ratio - 21.0) < 0.1

    def test_white_on_white(self):
        ratio = contrast_ratio((255, 255, 255), (255, 255, 255))
        assert abs(ratio - 1.0) < 0.1

    def test_symmetric(self):
        r1 = contrast_ratio((100, 50, 200), (255, 255, 255))
        r2 = contrast_ratio((255, 255, 255), (100, 50, 200))
        assert abs(r1 - r2) < 0.001


class TestCheckColorPair:
    def test_high_contrast_passes(self):
        finding = check_color_pair("#000000", "#FFFFFF")
        assert finding.passed
        assert finding.ratio > 20

    def test_low_contrast_fails(self):
        finding = check_color_pair("#CCCCCC", "#FFFFFF")
        assert not finding.passed
        assert finding.ratio < 4.5

    def test_dark_gray_on_white_passes(self):
        finding = check_color_pair("#333333", "#FFFFFF")
        assert finding.passed

    def test_large_text_context(self):
        finding = check_color_pair("#666666", "#FFFFFF", "large_text")
        assert finding.required_ratio == 3.0


class TestThemeFile:
    def test_theme_file_loads(self, sample_theme_file):
        results = check_theme_file(sample_theme_file)
        assert len(results.findings) > 0

    def test_theme_file_checks_light_mode(self, sample_theme_file):
        results = check_theme_file(sample_theme_file)
        light_findings = [f for f in results.findings if "light" in f.location]
        assert len(light_findings) > 0

    def test_theme_file_checks_dark_mode(self, sample_theme_file):
        results = check_theme_file(sample_theme_file)
        dark_findings = [f for f in results.findings if "dark" in f.location]
        assert len(dark_findings) > 0

    def test_nonexistent_theme(self):
        results = check_theme_file("/nonexistent/theme.yaml")
        assert len(results.findings) == 0

    def test_results_json_output(self, sample_theme_file):
        import json
        results = check_theme_file(sample_theme_file)
        output = results.to_json()
        data = json.loads(output)
        assert "passed" in data
        assert "findings" in data
