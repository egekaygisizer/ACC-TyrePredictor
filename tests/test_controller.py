"""
SessionController testleri: sahte bir sağlayıcıyla oyun akışı simüle edilir.
"""

from src.app.controller import SessionController
from src.app.session import ConnectionStatus
from src.core.models import TelemetrySample, WheelSet
from src.predictor.ml_model import MLPressurePredictor
from src.storage.db_manager import DatabaseManager
from src.telemetry.base import ITelemetryProvider


# Test sırasında elle ayarlanan sahte telemetri kaynağı
class FakeProvider(ITelemetryProvider):
    def __init__(self):
        self.sample = None

    def is_connected(self) -> bool:
        return self.sample is not None

    def get_sample(self):
        return self.sample

    def close(self) -> None:
        pass


def make_sample(psi=24.0, laps=0, in_pit=False, last_lap=0, track="monza", car="ferrari_296_gt3", live=True):
    return TelemetrySample(
        packet_id=1, speed_kmh=150.0, gear=4, rpms=7000, steer_angle=0.1, gas=0.8, brake=0.0,
        acc_lateral_g=1.4, acc_longitudinal_g=0.2,
        pressures=WheelSet(psi, psi, psi, psi), temperatures=WheelSet(80, 80, 80, 80),
        wheel_slip=WheelSet(0.06, 0.06, 0.06, 0.06),
        track_name=track, car_model=car, ambient_temp=22.0, track_temp=28.0,
        is_in_pit=in_pit, completed_laps=laps, current_lap_time_ms=1000,
        last_lap_time_ms=last_lap, is_live=live,
    )


def make_controller(tmp_path):
    provider = FakeProvider()
    controller = SessionController(provider, DatabaseManager(db_path=tmp_path / "t.db"), MLPressurePredictor())
    return provider, controller


def step(provider, controller, sample):
    provider.sample = sample
    return controller.update()


def test_waiting_for_game_when_no_telemetry(tmp_path):
    provider, controller = make_controller(tmp_path)
    assert step(provider, controller, None).status == ConnectionStatus.WAITING_FOR_GAME


def test_not_live_does_not_feed_detector(tmp_path):
    provider, controller = make_controller(tmp_path)
    state = step(provider, controller, make_sample(live=False))
    assert state.status == ConnectionStatus.NOT_LIVE
    assert state.cold_pressures is None


def test_unknown_track_and_car_produce_warnings(tmp_path):
    provider, controller = make_controller(tmp_path)
    state = step(provider, controller, make_sample(track="bilinmeyen_pist", car="bilinmeyen_arac"))
    assert len(state.warnings) == 2


def test_two_stint_flow(tmp_path):
    """Garaj -> sürüş -> tur kaydı -> yarış içi pit stop -> yeni lastik -> ikinci stint."""
    provider, controller = make_controller(tmp_path)

    # Garajda: soğuk basınç izlenir ama henüz kilitli değil
    state = step(provider, controller, make_sample(psi=24.0, in_pit=True))
    assert state.status == ConnectionStatus.IN_PIT
    assert state.cold_pressures.fl == 24.0 and not state.cold_locked

    # Pistte: soğuk basınç kilitlenir
    for _ in range(12):
        state = step(provider, controller, make_sample(psi=26.5))
    assert state.status == ConnectionStatus.DRIVING
    assert state.cold_locked and state.cold_pressures.fl == 24.0

    # Çizgi geçilir: tur kaydedilir
    state = step(provider, controller, make_sample(psi=26.8, laps=1, last_lap=105000))
    assert len(state.session_laps) == 1
    assert state.session_laps[0].lap_time_ms == 105000
    assert state.session_laps[0].delta_pressures.fl == 2.8
    assert controller.db.get_lap_count("monza") == 1
    assert state.recommended is not None

    # Yarış içi pit stop (sıcak lastik, aynı basınç): soğuk basınç ezilmez
    state = step(provider, controller, make_sample(psi=26.8, laps=1, in_pit=True))
    assert state.cold_locked and state.cold_pressures.fl == 24.0

    # Yeni lastik / yeni basınç: kilit açılır, yeni soğuk basınç izlenir
    state = step(provider, controller, make_sample(psi=24.5, laps=1, in_pit=True))
    assert not state.cold_locked and state.cold_pressures.fl == 24.5

    # İkinci stint: yeni soğuk basınç kilitlenir
    state = step(provider, controller, make_sample(psi=24.5, laps=1))
    assert state.cold_locked and state.cold_pressures.fl == 24.5


def test_track_change_starts_new_session(tmp_path):
    provider, controller = make_controller(tmp_path)
    step(provider, controller, make_sample(psi=24.0, in_pit=True, track="monza"))
    state = step(provider, controller, make_sample(psi=25.0, in_pit=True, track="spa"))
    assert state.cold_pressures.fl == 25.0 and state.session_laps == []


def test_custom_target_hot_pressure_shifts_recommendation(tmp_path):
    """Kullanıcının başlangıçta girdiği özel hedef sıcak basınç öneriyi doğrudan kaydırmalı."""
    p1 = FakeProvider()
    c1 = SessionController(p1, DatabaseManager(db_path=tmp_path / "t1.db"), MLPressurePredictor(target_hot_pressure=26.5))
    s1 = step(p1, c1, make_sample(psi=24.0, in_pit=True, track="monza"))

    p2 = FakeProvider()
    c2 = SessionController(p2, DatabaseManager(db_path=tmp_path / "t2.db"), MLPressurePredictor(target_hot_pressure=27.0))
    s2 = step(p2, c2, make_sample(psi=24.0, in_pit=True, track="monza"))

    assert s1.target_hot_pressure == 26.5
    assert s2.target_hot_pressure == 27.0
    assert round(s2.recommended.fl - s1.recommended.fl, 1) == 0.5


def test_prompt_target_pressure_inputs(monkeypatch):
    """Başlangıç hedef basınç sorusunun Enter, virgül ve hatalı girişleri doğru işlediğini test eder."""
    from main import prompt_target_pressure

    # Boş Enter -> varsayılan 26.8
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompt_target_pressure() == 26.8

    # Virgüllü giriş -> 26.6
    monkeypatch.setattr("builtins.input", lambda _: "26,6")
    assert prompt_target_pressure() == 26.6

    # Önce hatalı, sonra geçerli giriş
    inputs = iter(["abc", "99.0", "27.1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert prompt_target_pressure() == 27.1
