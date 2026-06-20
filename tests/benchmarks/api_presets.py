from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DATASET_DIR = Path(__file__).resolve().parent / "datasets"
SERVICES = (
    "auth-service",
    "concert-service",
    "reservation-service",
    "payment-service",
    "ticket-service",
    "notification-service",
)
USER_GROUPS = ("normal", "repeat", "heavy")


@dataclass(frozen=True)
class ApiBenchmarkPreset:
    name: str
    path: Path
    raw: dict[str, Any]

    @property
    def service_period_days(self) -> int:
        return int(self.raw["servicePeriodDays"])

    @property
    def active_users(self) -> int:
        return int(self.raw["users"]["active"])

    @property
    def user_distribution(self) -> dict[str, float]:
        return {key: float(value) for key, value in self.raw["users"]["distribution"].items()}

    @property
    def catalog(self) -> dict[str, int]:
        return {key: int(value) for key, value in self.raw["catalog"].items()}

    @property
    def targets(self) -> dict[str, int]:
        return {key: int(value) for key, value in self.raw["targets"].items()}

    @property
    def reservation_status_counts(self) -> dict[str, int]:
        return {key: int(value) for key, value in self.raw["reservationStatusCounts"].items()}

    @property
    def payment_status_counts(self) -> dict[str, int]:
        return {key: int(value) for key, value in self.raw["paymentStatusCounts"].items()}

    @property
    def notification_retention_days(self) -> int:
        return int(self.raw["notificationRetentionDays"])

    def service_tables(self, service_name: str) -> dict[str, int]:
        return {key: int(value) for key, value in self.raw["services"][service_name]["tables"].items()}

    def seed_summary(self, service_name: str) -> dict[str, Any]:
        return {
            "servicePeriodDays": self.service_period_days,
            "activeUsers": self.active_users,
            "catalog": self.catalog,
            "targets": self.targets,
            "userDistribution": self.user_distribution,
            "reservationStatusCounts": self.reservation_status_counts,
            "paymentStatusCounts": self.payment_status_counts,
            "notificationRetentionDays": self.notification_retention_days,
            "tables": self.service_tables(service_name),
        }


def load_preset(name: str) -> ApiBenchmarkPreset:
    path = DATASET_DIR / f"{name}.yaml"
    if not path.exists():
        available = ", ".join(sorted(item.stem for item in DATASET_DIR.glob("*.yaml")))
        raise ValueError(f"unknown API benchmark preset {name!r}; available presets: {available}")
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    preset = ApiBenchmarkPreset(name=str(raw.get("name", "")), path=path, raw=raw)
    validate_preset(preset)
    if preset.name != name:
        raise ValueError(f"{path} name must be {name!r}, got {preset.name!r}")
    return preset


def validate_preset(preset: ApiBenchmarkPreset) -> None:
    raw = preset.raw
    _require_positive_int(raw, "servicePeriodDays")
    _require_mapping(raw, "users")
    _require_positive_int(raw["users"], "registered")
    _require_positive_int(raw["users"], "active")
    if raw["users"]["active"] > raw["users"]["registered"]:
        raise ValueError("users.active must be less than or equal to users.registered")
    _require_ratio_mapping(raw["users"], "distribution", USER_GROUPS)

    _require_mapping(raw, "catalog")
    for key in ("concerts", "showtimes", "seats"):
        _require_positive_int(raw["catalog"], key)

    _require_mapping(raw, "targets")
    for key in ("reservations", "payments", "tickets", "notifications"):
        _require_non_negative_int(raw["targets"], key)

    _require_mapping(raw, "reservationStatusCounts")
    for key in ("paid", "canceled", "expired", "pending"):
        _require_non_negative_int(raw["reservationStatusCounts"], key)
    reservation_status_total = sum(int(raw["reservationStatusCounts"][key]) for key in ("paid", "canceled", "expired", "pending"))
    if reservation_status_total != int(raw["targets"]["reservations"]):
        raise ValueError("reservationStatusCounts must sum to targets.reservations")

    _require_mapping(raw, "paymentStatusCounts")
    for key in ("approved", "failed"):
        _require_non_negative_int(raw["paymentStatusCounts"], key)
    payment_status_total = sum(int(raw["paymentStatusCounts"][key]) for key in ("approved", "failed"))
    if payment_status_total != int(raw["targets"]["payments"]):
        raise ValueError("paymentStatusCounts must sum to targets.payments")

    _require_positive_int(raw, "notificationRetentionDays")
    if int(raw["notificationRetentionDays"]) > int(raw["servicePeriodDays"]):
        raise ValueError("notificationRetentionDays must be less than or equal to servicePeriodDays")

    _require_mapping(raw, "services")
    for service_name in SERVICES:
        _require_mapping(raw["services"], service_name)
        _require_mapping(raw["services"][service_name], "tables")
        for table, value in raw["services"][service_name]["tables"].items():
            if not isinstance(table, str) or not table:
                raise ValueError(f"services.{service_name}.tables contains an invalid table name")
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"services.{service_name}.tables.{table} must be a non-negative integer")

    service_tables = raw["services"]
    _require_table_total(service_tables, "auth-service", "users", raw["users"]["registered"])
    _require_table_total(service_tables, "auth-service", "audit_logs", raw["users"]["registered"] * 2)
    _require_table_total(service_tables, "auth-service", "refresh_tokens", raw["users"]["active"] // 2)
    _require_table_total(service_tables, "auth-service", "revoked_tokens", 0)
    _require_table_total(service_tables, "concert-service", "venues", raw["catalog"]["concerts"])
    _require_table_total(service_tables, "concert-service", "concerts", raw["catalog"]["concerts"])
    _require_table_total(service_tables, "concert-service", "showtimes", raw["catalog"]["showtimes"])
    _require_table_total(service_tables, "concert-service", "seats", raw["catalog"]["seats"])
    _require_table_total(service_tables, "concert-service", "seat_grades", raw["catalog"]["showtimes"] * 4)
    _require_table_total(service_tables, "reservation-service", "reservations", raw["targets"]["reservations"])
    _require_table_total(service_tables, "payment-service", "payments", raw["targets"]["payments"])
    _require_table_total(service_tables, "payment-service", "payment_events", raw["targets"]["payments"])
    _require_table_total(service_tables, "ticket-service", "tickets", raw["targets"]["tickets"])
    _require_table_total(service_tables, "ticket-service", "processed_events", raw["targets"]["tickets"])
    _require_table_total(service_tables, "notification-service", "notifications", raw["targets"]["notifications"])
    _require_table_total(service_tables, "notification-service", "processed_events", raw["targets"]["notifications"])


def user_id_for(service_name: str, group: str, index: int = 0) -> str:
    return f"bench-{service_name}-{group}-{index:05d}"


def user_group_for_index(index: int, total: int, distribution: dict[str, float]) -> str:
    if total <= 0:
        return "normal"
    heavy_cutoff = max(1, int(total * distribution["heavy"]))
    repeat_cutoff = heavy_cutoff + max(1, int(total * distribution["repeat"]))
    if index < heavy_cutoff:
        return "heavy"
    if index < repeat_cutoff:
        return "repeat"
    return "normal"


def distributed_user_id(service_name: str, index: int, total: int, distribution: dict[str, float]) -> str:
    group = user_group_for_index(index, total, distribution)
    if group == "heavy":
        return user_id_for(service_name, group)
    if group == "repeat":
        repeat_users = max(1, int(total * distribution["repeat"] / 8))
        return user_id_for(service_name, group, index % repeat_users)
    normal_users = max(1, int(total * distribution["normal"]))
    return user_id_for(service_name, group, index % normal_users)


def status_for_index(index: int, counts: dict[str, int]) -> str:
    cursor = 0
    for status, count in counts.items():
        cursor += count
        if index < cursor:
            return status
    raise ValueError(f"status index {index} is outside configured counts")


def chunked(rows: Iterable[dict[str, Any]], size: int = 5000) -> Iterator[list[dict[str, Any]]]:
    chunk: list[dict[str, Any]] = []
    for row in rows:
        chunk.append(row)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _require_mapping(raw: dict[str, Any], key: str) -> None:
    if key not in raw or not isinstance(raw[key], dict):
        raise ValueError(f"{key} must be present and must be a mapping")


def _require_positive_int(raw: dict[str, Any], key: str) -> None:
    if key not in raw or not isinstance(raw[key], int) or raw[key] <= 0:
        raise ValueError(f"{key} must be a positive integer")


def _require_non_negative_int(raw: dict[str, Any], key: str) -> None:
    if key not in raw or not isinstance(raw[key], int) or raw[key] < 0:
        raise ValueError(f"{key} must be a non-negative integer")


def _require_ratio_mapping(raw: dict[str, Any], key: str, expected_keys: tuple[str, ...]) -> None:
    _require_mapping(raw, key)
    ratios = raw[key]
    missing = [item for item in expected_keys if item not in ratios]
    if missing:
        raise ValueError(f"{key} is missing required keys: {', '.join(missing)}")
    total = 0.0
    for item in expected_keys:
        value = ratios[item]
        if not isinstance(value, int | float) or value < 0:
            raise ValueError(f"{key}.{item} must be a non-negative number")
        total += float(value)
    if abs(total - 1.0) > 0.000001:
        raise ValueError(f"{key} ratios must sum to 1.0")


def _require_table_total(services: dict[str, Any], service_name: str, table: str, expected: int) -> None:
    actual = services[service_name]["tables"].get(table)
    if actual != expected:
        raise ValueError(f"services.{service_name}.tables.{table} must equal {expected}, got {actual}")
