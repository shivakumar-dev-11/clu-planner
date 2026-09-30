from constraints import simulate_route
from distance import DistanceContext
from models import Customer, Executive


def _exec():
    return Executive(
        executive_id="E01",
        office_name="CLU Test Office",
        office_address="Test address",
        home_lat=17.4586,
        home_lon=78.2836,
        shift_start_min=570,
        shift_end_min=1080,
        max_visits=10,
        max_km=70.0,
    )


def _customer(cid, lat, lon, ws, we, svc, ptp=False):
    return Customer(
        customer_id=cid,
        area=None,
        address=None,
        lat=lat,
        lon=lon,
        dpd=None,
        overdue_amount=None,
        priority_score=50.0,
        ptp_today=ptp,
        window_start_min=ws,
        window_end_min=we,
        service_min=svc,
    )


def test_early_arrival_waits():
    ex = _exec()
    cu = _customer("C1", 17.452, 78.29, 600, 780, 20)
    ctx = DistanceContext([ex], [cu])
    res = simulate_route(ex, ["C1"], {cu.customer_id: cu}, ctx)
    assert res.valid
    assert res.stops[0].wait_min >= 0
    assert res.stops[0].visit_start_min >= 600


def test_service_overflow_invalid():
    ex = _exec()
    cu = _customer("C1", 17.452, 78.29, 570, 580, 20)
    ctx = DistanceContext([ex], [cu])
    res = simulate_route(ex, ["C1"], {cu.customer_id: cu}, ctx)
    assert not res.valid
    assert res.rejection_reason == "TIME_WINDOW"


def test_return_leg_included_in_total_km():
    ex = _exec()
    cu = _customer("C1", 17.452, 78.29, 570, 780, 15)
    ctx = DistanceContext([ex], [cu])
    res = simulate_route(ex, ["C1"], {cu.customer_id: cu}, ctx)
    assert res.valid
    leg = res.stops[0].leg_km
    assert res.total_km > leg
