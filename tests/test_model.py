"""The Python model must give the same answers as the Excel model (Jaybird_Capacity_Control_Model.xlsx)."""
import os, sys
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import solve_row

PRICES = {"member": 22, "classpass": 19, "dropin": 32, "dropin_happy_hour": 25}
DATA = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "demand_data.csv"))

# (day, time, instructor) -> (member limit, ClassPass protection, expected revenue) from the Excel model
EXCEL = {
    ("Monday", "6:30 PM", "Instructor A"): (21, 19, 962.60),
    ("Friday", "12:00 PM", "Instructor D"): (38, 6, 637.99),
    ("Saturday", "10:45 AM", "Instructor A"): (8, 33, 1055.65),
    ("Sunday", "4:30 PM", "Instructor C"): (38, 12, 769.10),
}


@pytest.mark.parametrize("key,expected", EXCEL.items())
def test_matches_excel(key, expected):
    day, time, inst = key
    row = DATA[(DATA.day == day) & (DATA.time == time) & (DATA.instructor == inst)].iloc[0]
    res = solve_row(row, PRICES)
    assert res.member_limit == expected[0]
    assert res.classpass_protect == expected[1]
    assert res.expected_revenue == pytest.approx(expected[2], abs=0.01)
