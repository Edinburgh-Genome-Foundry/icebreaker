from icebreaker.tools import sanitize_well_name

def test_sanitize_wellname():
    assert sanitize_well_name("A1") == "A01"
    assert sanitize_well_name("A11") == "A11"
    assert sanitize_well_name("AH1") == "AH01"
    assert sanitize_well_name("AH11") == "AH11"
    
