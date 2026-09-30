from pathlib import Path

from baseline import run_baseline
from data_io import load_customers, load_executives
from distance import DistanceContext
from metrics import compute_metrics
from optimizer import run_optimizer

DATA = Path(__file__).resolve().parent.parent / "data"


def test_optimizer_partition_and_score():
    executives, ei = load_executives(DATA / "executives.csv")
    customers, ci = load_customers(DATA / "customers.csv")
    assert not ei and not ci
    ctx = DistanceContext(executives, customers)
    plan = run_optimizer(executives, customers, ctx, lambda_value=2.0)
    all_ids = {c.customer_id for c in customers}
    scheduled = []
    for r in plan.routes:
        scheduled.extend(r.customer_ids)
    unvisited_ids = {u.customer_id for u in plan.unvisited}
    assert len(scheduled) == len(set(scheduled))
    assert set(scheduled) | unvisited_ids == all_ids
    assert set(scheduled).isdisjoint(unvisited_ids)
    metrics = compute_metrics(plan, customers, ctx, 2.0)
    assert metrics.scheduled_count == len(scheduled)


def test_baseline_runs():
    executives, _ = load_executives(DATA / "executives.csv")
    customers, _ = load_customers(DATA / "customers.csv")
    ctx = DistanceContext(executives, customers)
    plan = run_baseline(executives, customers, ctx)
    assert len(plan.routes) == len(executives)


def test_deterministic_optimizer():
    executives, _ = load_executives(DATA / "executives.csv")
    customers, _ = load_customers(DATA / "customers.csv")
    ctx = DistanceContext(executives, customers)
    p1 = run_optimizer(executives, customers, ctx, 2.0)
    p2 = run_optimizer(executives, customers, ctx, 2.0)
    s1 = [r.customer_ids for r in p1.routes]
    s2 = [r.customer_ids for r in p2.routes]
    assert s1 == s2
