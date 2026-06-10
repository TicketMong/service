from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from prometheus_client import Counter, Histogram


@dataclass(frozen=True)
class CounterMetricSpec:
    name: str
    description: str
    label_fields: Mapping[str, str]


@dataclass(frozen=True)
class HistogramMetricSpec:
    name: str
    description: str
    label_fields: Mapping[str, str]
    value_field: str


MetricSpec = CounterMetricSpec | HistogramMetricSpec


class MetricLabelEvent(Protocol):
    @classmethod
    def metric_specs(cls) -> Sequence[MetricSpec]:
        """event class가 기록할 metric spec 목록을 반환한다."""
        ...


EventT = TypeVar("EventT", bound=MetricLabelEvent)
MetricSpecT = TypeVar("MetricSpecT", bound=MetricSpec)
MetricHandleMap = dict[tuple[type[MetricLabelEvent], str], Any]
CounterRecordCallback = Callable[[Any, dict[str, str], MetricLabelEvent], None]
HistogramRecordCallback = Callable[[Any, dict[str, str], float, MetricLabelEvent], None]


def metric_label_names_from_fields(fields: Mapping[str, str]) -> tuple[str, ...]:
    """metric label field mapping에서 label 이름을 반환한다."""
    return tuple(fields)


def metric_label_names_for_spec(spec: MetricSpec) -> tuple[str, ...]:
    """metric spec이 선언한 label 이름을 반환한다."""
    return metric_label_names_from_fields(spec.label_fields)


def metric_spec_for(event_type: type, spec_type: type[MetricSpecT]) -> MetricSpecT:
    """event class에서 요청한 종류의 metric spec 하나를 찾는다."""
    specs = metric_specs_for(event_type)
    matches = [spec for spec in specs if isinstance(spec, spec_type)]
    if len(matches) != 1:
        raise ValueError(f"{event_type.__name__} must define exactly one {spec_type.__name__}")
    return matches[0]


def metric_specs_for(event_type: type) -> tuple[MetricSpec, ...]:
    """event class가 선언한 metric spec 목록을 반환한다."""
    specs = getattr(event_type, "metric_specs", ())
    if callable(specs):
        specs = specs()
    return tuple(specs)


def metric_labels_from_fields(event: object, fields: Mapping[str, str]) -> dict[str, str]:
    """event field 값을 Prometheus label 문자열로 변환한다."""
    return {label: _metric_label_value(getattr(event, field_name)) for label, field_name in fields.items()}


def metric_labels_for_event(event: object, spec: MetricSpec) -> dict[str, str]:
    """event가 제공하는 custom label 변환을 우선 사용한다."""
    custom_labels = getattr(event, "metric_labels_for", None)
    if callable(custom_labels):
        return custom_labels(spec)
    return metric_labels_from_fields(event, spec.label_fields)


def connect_counter(
    signal: Any,
    metric: Any,
    service_labels: Mapping[str, str],
    event_type: type[EventT],
    *,
    label_fields: Mapping[str, str] | None = None,
    spec: MetricSpec | None = None,
    record: CounterRecordCallback | None = None,
) -> None:
    """Blinker signal을 counter 증가 함수에 연결한다."""
    fields = label_fields
    record_metric_value = record or _increment_counter

    def record_metric(sender: object, *, event: EventT) -> None:
        if not isinstance(event, event_type):
            return
        labels = _metric_labels_for_recording(event, fields, spec)
        record_metric_value(metric, {**service_labels, **labels}, event)

    signal.connect(record_metric, weak=False)


def connect_histogram(
    signal: Any,
    metric: Any,
    service_labels: Mapping[str, str],
    event_type: type[EventT],
    *,
    value_field: str,
    label_fields: Mapping[str, str] | None = None,
    spec: MetricSpec | None = None,
    record: HistogramRecordCallback | None = None,
) -> None:
    """Blinker signal을 histogram 관측 함수에 연결한다."""
    fields = label_fields
    record_metric_value = record or _observe_histogram

    def record_metric(sender: object, *, event: EventT) -> None:
        if not isinstance(event, event_type):
            return
        labels = _metric_labels_for_recording(event, fields, spec)
        record_metric_value(metric, {**service_labels, **labels}, float(getattr(event, value_field)), event)

    signal.connect(record_metric, weak=False)


def connect_metric(
    signal: Any,
    metric: Any,
    service_labels: Mapping[str, str],
    event_type: type[EventT],
    spec: MetricSpec,
    *,
    counter_record: CounterRecordCallback | None = None,
    histogram_record: HistogramRecordCallback | None = None,
) -> None:
    """metric spec 종류에 맞춰 signal과 metric 기록 함수를 연결한다."""
    if isinstance(spec, CounterMetricSpec):
        connect_counter(
            signal,
            metric,
            service_labels,
            event_type,
            label_fields=spec.label_fields,
            spec=spec,
            record=counter_record,
        )
        return
    connect_histogram(
        signal,
        metric,
        service_labels,
        event_type,
        value_field=spec.value_field,
        label_fields=spec.label_fields,
        spec=spec,
        record=histogram_record,
    )


def create_metrics_for_events(
    registry: Any,
    *,
    service_label_names: Sequence[str],
    event_types: Sequence[type[MetricLabelEvent]],
) -> MetricHandleMap:
    """event class의 metric spec으로 Prometheus metric handle을 생성한다."""
    metrics: MetricHandleMap = {}
    for event_type in event_types:
        for spec in metric_specs_for(event_type):
            label_names = (*service_label_names, *metric_label_names_for_spec(spec))
            _assert_label_names(label_names)
            if isinstance(spec, CounterMetricSpec):
                metrics[(event_type, spec.name)] = Counter(
                    spec.name,
                    spec.description,
                    label_names,
                    registry=registry,
                )
                continue
            metrics[(event_type, spec.name)] = Histogram(
                spec.name,
                spec.description,
                label_names,
                registry=registry,
            )
    return metrics


def connect_metrics_for_events(
    signal: Any,
    metrics: MetricHandleMap,
    service_labels: Mapping[str, str],
    event_types: Sequence[type[EventT]],
    *,
    counter_record: CounterRecordCallback | None = None,
    histogram_record: HistogramRecordCallback | None = None,
) -> None:
    """event class의 metric spec 목록을 signal에 일괄 연결한다."""
    for event_type in event_types:
        for spec in metric_specs_for(event_type):
            connect_metric(
                signal,
                metrics[(event_type, spec.name)],
                service_labels,
                event_type,
                spec,
                counter_record=counter_record,
                histogram_record=histogram_record,
            )


def _increment_counter(metric: Any, labels: dict[str, str], event: MetricLabelEvent) -> None:
    """기본 counter 기록 동작을 수행한다."""
    metric.labels(**labels).inc()


def _observe_histogram(metric: Any, labels: dict[str, str], value: float, event: MetricLabelEvent) -> None:
    """기본 histogram 기록 동작을 수행한다."""
    metric.labels(**labels).observe(value)


def _metric_labels_for_recording(
    event: object,
    fields: Mapping[str, str] | None,
    spec: MetricSpec | None,
) -> dict[str, str]:
    """recording에 사용할 label 값을 계산한다."""
    if spec is not None:
        return metric_labels_for_event(event, spec)
    if fields is not None:
        return metric_labels_from_fields(event, fields)
    legacy_labels = getattr(event, "metric_labels", None)
    if callable(legacy_labels):
        return legacy_labels()
    raise ValueError(f"{type(event).__name__} must define metric_labels() or provide a metric spec")


def _assert_label_names(label_names: Sequence[str]) -> None:
    from metrics.labels import assert_safe_metric_label_names

    assert_safe_metric_label_names(label_names)


def _metric_label_value(value: object) -> str:
    """enum 또는 문자열 값을 Prometheus label 문자열로 정규화한다."""
    enum_value = getattr(value, "value", value)
    return str(enum_value)
