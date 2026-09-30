import io

from data_io import has_blocking_errors, load_customers


def test_minimal_csv_id_lat_lon_only():
    csv = "visit_id,latitude,longitude\nV1,17.45,78.29\n"
    customers, issues = load_customers(io.BytesIO(csv.encode()))
    assert len(customers) == 1
    assert customers[0].customer_id == "V1"
    assert not has_blocking_errors(issues, len(customers))


def test_utf8_bom_and_semicolon():
    csv = "\ufeffid;lat;lon;priority;window\nC1;17.45;78.29;80;09:00-17:00\n"
    customers, issues = load_customers(io.BytesIO(csv.encode("utf-8")))
    assert len(customers) == 1
    assert customers[0].priority_score == 80.0
