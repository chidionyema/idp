class _Meter:
    def create_counter(self, *a, **kw):
        pass


meter = _Meter()


def make():
    meter.create_counter("agent_turn_total", unit="1", description="turns")
    meter.create_counter(
        "agent_undeclared_total",
        unit="1",
        description="a metric nobody wrote a row for",
    )
