"""Haversine distance, road correction, travel time, distance matrices."""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

from models import Customer, Executive

EARTH_RADIUS_KM = 6371.0
ROAD_FACTOR = 1.3
AVERAGE_SPEED_KMH = 25.0
EPS_KM = 1e-9


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    a = max(0.0, min(1.0, a))
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


def road_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return haversine_km(lat1, lon1, lat2, lon2) * ROAD_FACTOR


def travel_minutes(distance_km: float) -> float:
    if distance_km <= 0:
        return 0.0
    return distance_km / AVERAGE_SPEED_KMH * 60.0


class DistanceContext:
    """Precomputed road distances between executives, customers, and points."""

    def __init__(
        self,
        executives: List[Executive],
        customers: List[Customer],
    ):
        self.executives = executives
        self.customers = customers
        self.customer_by_id = {c.customer_id: c for c in customers}
        self.exec_by_id = {e.executive_id: e for e in executives}

        n_e = len(executives)
        n_c = len(customers)
        self._exec_customer = np.zeros((n_e, n_c))
        self._customer_customer = np.zeros((n_c, n_c))
        self._exec_index = {e.executive_id: i for i, e in enumerate(executives)}
        self._cust_index = {c.customer_id: i for i, c in enumerate(customers)}

        for i, ex in enumerate(executives):
            for j, cu in enumerate(customers):
                self._exec_customer[i, j] = road_km(
                    ex.home_lat, ex.home_lon, cu.lat, cu.lon
                )

        for i, c1 in enumerate(customers):
            for j, c2 in enumerate(customers):
                if i == j:
                    self._customer_customer[i, j] = 0.0
                else:
                    self._customer_customer[i, j] = road_km(
                        c1.lat, c1.lon, c2.lat, c2.lon
                    )

    def km_exec_to_customer(self, executive_id: str, customer_id: str) -> float:
        ei = self._exec_index[executive_id]
        ci = self._cust_index[customer_id]
        return float(self._exec_customer[ei, ci])

    def km_customer_to_customer(self, from_id: str, to_id: str) -> float:
        if from_id == to_id:
            return 0.0
        fi = self._cust_index[from_id]
        ti = self._cust_index[to_id]
        return float(self._customer_customer[fi, ti])

    def km_point_to_customer(
        self,
        lat: float,
        lon: float,
        customer_id: str,
    ) -> float:
        cu = self.customer_by_id[customer_id]
        return road_km(lat, lon, cu.lat, cu.lon)

    def km_customer_to_point(
        self,
        customer_id: str,
        lat: float,
        lon: float,
    ) -> float:
        cu = self.customer_by_id[customer_id]
        return road_km(cu.lat, cu.lon, lat, lon)

    def km_exec_home_to_point(
        self, executive_id: str, lat: float, lon: float
    ) -> float:
        ex = self.exec_by_id[executive_id]
        return road_km(ex.home_lat, ex.home_lon, lat, lon)
