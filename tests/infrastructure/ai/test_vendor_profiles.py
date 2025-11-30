"""Tests for vendor-specific code extraction profiles."""

from troostwatch.infrastructure.ai.vendor_profiles import (
    VENDOR_PROFILES,
    detect_vendor,
    extract_vendor_codes,
    get_all_vendor_names,
    HP_PROFILE,
    LENOVO_PROFILE,
    UBIQUITI_PROFILE,
    DELL_PROFILE,
    APPLE_PROFILE,
    SAMSUNG_PROFILE,
    CISCO_PROFILE,
)


class TestDetectVendor:
    """Tests for vendor detection from text."""

    def test_detect_hp(self):
        text = "HP LaserJet Pro MFP M428fdw Printer"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "HP"

    def test_detect_hp_alias(self):
        text = "Hewlett-Packard Enterprise Server"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "HP"

    def test_detect_lenovo(self):
        text = "Lenovo ThinkPad X1 Carbon Gen 9"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "Lenovo"

    def test_detect_lenovo_thinkpad_alias(self):
        text = "ThinkPad T480s - Business Laptop"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "Lenovo"

    def test_detect_ubiquiti(self):
        text = "Ubiquiti UniFi AP-AC-PRO Access Point"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "Ubiquiti"

    def test_detect_ubiquiti_unifi_alias(self):
        text = "UniFi Dream Machine Pro"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "Ubiquiti"

    def test_detect_dell(self):
        text = "Dell PowerEdge R740 Server"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "Dell"

    def test_detect_apple(self):
        text = "Apple MacBook Pro 14-inch M1 Pro"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "Apple"

    def test_detect_samsung(self):
        text = "Samsung Galaxy S21 Ultra 5G"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "Samsung"

    def test_detect_cisco(self):
        text = "Cisco Catalyst 9200 Switch"
        vendor = detect_vendor(text)
        assert vendor is not None
        assert vendor.name == "Cisco"

    def test_detect_no_vendor(self):
        text = "Generic laptop computer model 12345"
        vendor = detect_vendor(text)
        assert vendor is None


class TestHPExtraction:
    """Tests for HP-specific code extraction."""

    def test_hp_product_number(self):
        text = "HP Product: L3M56A#ABB\nSerial: CND1234ABC"
        codes = extract_vendor_codes(text, HP_PROFILE)
        product_codes = [c for c in codes if c.code_type == "product_code"]
        assert len(product_codes) >= 1
        assert any("L3M56A" in c.value for c in product_codes)

    def test_hp_spare_part(self):
        text = "Spare Part: 123456-001"
        codes = extract_vendor_codes(text, HP_PROFILE)
        part_codes = [c for c in codes if c.code_type == "part_number"]
        assert len(part_codes) == 1
        assert part_codes[0].value == "123456-001"

    def test_hp_serial_number(self):
        text = "S/N: CND1234ABC"
        codes = extract_vendor_codes(text, HP_PROFILE)
        serials = [c for c in codes if c.code_type == "serial_number"]
        assert len(serials) == 1
        assert serials[0].value == "CND1234ABC"

    def test_hp_ct_number(self):
        text = "CT12345678 HP Toner"
        codes = extract_vendor_codes(text, HP_PROFILE)
        ct_codes = [c for c in codes if "CT" in c.value]
        assert len(ct_codes) == 1
        assert ct_codes[0].value == "CT12345678"


class TestLenovoExtraction:
    """Tests for Lenovo-specific code extraction."""

    def test_lenovo_mtm(self):
        text = "MTM: 20HS001QMH"
        codes = extract_vendor_codes(text, LENOVO_PROFILE)
        model_codes = [c for c in codes if c.code_type == "model_number"]
        assert len(model_codes) == 1
        assert "20HS001QMH" in model_codes[0].value

    def test_lenovo_product_number(self):
        text = "Model: 20HQ0014MH ThinkPad"
        codes = extract_vendor_codes(text, LENOVO_PROFILE)
        product_codes = [c for c in codes if c.code_type == "product_code"]
        assert len(product_codes) >= 1

    def test_lenovo_fru(self):
        text = "FRU: 01AY094"
        codes = extract_vendor_codes(text, LENOVO_PROFILE)
        part_codes = [c for c in codes if c.code_type == "part_number"]
        assert len(part_codes) == 1
        assert part_codes[0].value == "01AY094"


class TestUbiquitiExtraction:
    """Tests for Ubiquiti-specific code extraction."""

    def test_ubiquiti_model(self):
        text = "UniFi UAP-AC-PRO Access Point"
        codes = extract_vendor_codes(text, UBIQUITI_PROFILE)
        model_codes = [c for c in codes if c.code_type == "model_number"]
        assert len(model_codes) == 1
        assert model_codes[0].value == "UAP-AC-PRO"

    def test_ubiquiti_mac(self):
        text = "MAC: 78:8A:20:12:34:56"
        codes = extract_vendor_codes(text, UBIQUITI_PROFILE)
        mac_codes = [c for c in codes if c.code_type == "mac_address"]
        assert len(mac_codes) == 1
        assert mac_codes[0].value == "78:8A:20:12:34:56"

    def test_ubiquiti_switch_model(self):
        text = "Ubiquiti USW-24-POE Switch"
        codes = extract_vendor_codes(text, UBIQUITI_PROFILE)
        model_codes = [c for c in codes if c.code_type == "model_number"]
        assert len(model_codes) == 1
        assert model_codes[0].value == "USW-24-POE"


class TestDellExtraction:
    """Tests for Dell-specific code extraction."""

    def test_dell_service_tag(self):
        text = "Service Tag: ABC1234"
        codes = extract_vendor_codes(text, DELL_PROFILE)
        service_tags = [c for c in codes if c.code_type == "service_tag"]
        assert len(service_tags) == 1
        assert service_tags[0].value == "ABC1234"

    def test_dell_express_code(self):
        text = "Express Service Code: 12345678901"
        codes = extract_vendor_codes(text, DELL_PROFILE)
        express_codes = [c for c in codes if c.code_type == "service_tag"]
        assert len(express_codes) == 1
        assert express_codes[0].value == "12345678901"


class TestAppleExtraction:
    """Tests for Apple-specific code extraction."""

    def test_apple_serial(self):
        text = "Serial: C02X12345ABC"
        codes = extract_vendor_codes(text, APPLE_PROFILE)
        serials = [c for c in codes if c.code_type == "serial_number"]
        assert len(serials) == 1
        assert serials[0].value == "C02X12345ABC"

    def test_apple_model(self):
        text = "Model: A2337"
        codes = extract_vendor_codes(text, APPLE_PROFILE)
        models = [c for c in codes if c.code_type == "model_number"]
        assert len(models) == 1
        assert models[0].value == "A2337"

    def test_apple_part_number(self):
        text = "Part: MGND3LL/A"
        codes = extract_vendor_codes(text, APPLE_PROFILE)
        parts = [c for c in codes if c.code_type == "part_number"]
        assert len(parts) == 1
        assert parts[0].value == "MGND3LL/A"


class TestSamsungExtraction:
    """Tests for Samsung-specific code extraction."""

    def test_samsung_model_sm(self):
        text = "Samsung SM-G991B Galaxy S21"
        codes = extract_vendor_codes(text, SAMSUNG_PROFILE)
        models = [c for c in codes if c.code_type == "model_number"]
        assert len(models) == 1
        assert models[0].value == "SM-G991B"

    def test_samsung_model_gt(self):
        text = "Model: GT-I9500"
        codes = extract_vendor_codes(text, SAMSUNG_PROFILE)
        models = [c for c in codes if c.code_type == "model_number"]
        assert len(models) == 1
        assert models[0].value == "GT-I9500"


class TestCiscoExtraction:
    """Tests for Cisco-specific code extraction."""

    def test_cisco_pid(self):
        text = "Cisco C9200L-24P-4G Switch"
        codes = extract_vendor_codes(text, CISCO_PROFILE)
        products = [c for c in codes if c.code_type == "product_code"]
        assert len(products) == 1
        assert "C9200L-24P-4G" in products[0].value

    def test_cisco_ws_switch(self):
        text = "Model: WS-C2960X-24PS-L"
        codes = extract_vendor_codes(text, CISCO_PROFILE)
        products = [c for c in codes if c.code_type == "product_code"]
        assert len(products) == 1
        assert "WS-C2960X-24PS-L" in products[0].value


class TestAutoDetection:
    """Tests for auto-detection of vendor from text."""

    def test_auto_detect_and_extract_hp(self):
        text = "HP LaserJet Pro\nProduct: L3M56A#ABB\nS/N: CND1234ABC"
        codes = extract_vendor_codes(text)  # No vendor specified
        assert len(codes) >= 2
        assert any(c.code_type == "product_code" for c in codes)
        assert any(c.code_type == "serial_number" for c in codes)

    def test_auto_detect_and_extract_samsung(self):
        text = "Samsung Galaxy\nModel: SM-G991B"
        codes = extract_vendor_codes(text)
        assert len(codes) >= 1
        assert any(c.value == "SM-G991B" for c in codes)


class TestGetAllVendorNames:
    """Tests for vendor name listing."""

    def test_get_all_vendor_names(self):
        names = get_all_vendor_names()
        assert "HP" in names
        assert "Lenovo" in names
        assert "Ubiquiti" in names
        assert "Dell" in names
        assert "Apple" in names
        assert "Samsung" in names
        assert "Cisco" in names
        assert len(names) == 7


class TestVendorProfiles:
    """Tests for vendor profile registry."""

    def test_all_profiles_have_patterns(self):
        for name, profile in VENDOR_PROFILES.items():
            assert len(profile.patterns) > 0, f"{name} has no patterns"

    def test_all_profiles_have_normalizers(self):
        for name, profile in VENDOR_PROFILES.items():
            assert len(profile.normalizers) > 0, f"{name} has no normalizers"
