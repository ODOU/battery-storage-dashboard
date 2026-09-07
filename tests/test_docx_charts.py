import os, pytest
from scripts.docx_charts import read_charts

DOCX = r"C:\Users\OOdou\Downloads\myreviews\Report_Battery_MG_Electrification_WestAfrica_SMGRev_Correction.docx"
pytestmark = pytest.mark.skipif(not os.path.exists(DOCX), reason="manuscript not on this machine")

def test_reads_22_charts():
    ch = read_charts(DOCX)
    assert sorted(ch) == list(range(1, 23))

def test_chart6_is_bfa_battery_kwh_in_family_order():
    s = read_charts(DOCX)[6]["series"][0]
    assert s["name"] == "Total"
    assert s["cats"][:5] == ["1", "2", "3", "4", "5"] and len(s["vals"]) == 20
    assert len(s["cats"]) == 20
    assert round(s["vals"][1] / 1000, 1) == 367.8      # leastcost/optimistic T2 (annex)
    assert round(s["vals"][11] / 1000, 1) == 1247.6    # restricted/optimistic T2 (annex)

def test_chart1_example_series():
    names = [s["name"] for s in read_charts(DOCX)[1]["series"]]
    assert names == ["Investment", "0&M", "Fuel"]
