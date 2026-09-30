from auth import authenticate


def test_authenticate_demo_executive():
    assert authenticate("E01", "clu_exec_01")
    assert not authenticate("E01", "wrong")


def test_authenticate_admin():
    assert authenticate("admin", "clu_admin_planner")
