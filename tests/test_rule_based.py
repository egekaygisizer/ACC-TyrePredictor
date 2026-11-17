"""
RuleBasedPredictor fizik mantığı testleri.
"""

from src.predictor.rule_based import RuleBasedPredictor

predictor = RuleBasedPredictor(target_hot_pressure=26.8)


def test_monza_vs_spa_base_delta_difference():
    """Düşük enerjili Monza ile yüksek enerjili Spa arasındaki taban basınç farkını test eder."""
    # Referans sıcaklıkta (20°C hava / 26°C pist)
    p_monza = predictor.predict("monza", "ferrari_296_gt3", 20.0, 26.0)
    p_spa = predictor.predict("spa", "ferrari_296_gt3", 20.0, 26.0)

    # Monza'da az şişer => soğuk basınç yüksek önerilmeli (~25.1 - 25.3)
    # Spa'da çok şişer => soğuk basınç düşük önerilmeli (~24.4 - 24.6)
    assert p_monza.fl > p_spa.fl
    assert 25.0 <= p_monza.fl <= 25.4
    assert 24.2 <= p_spa.fl <= 24.7


def test_clockwise_track_left_tyres_get_lower_cold_pressure():
    """Saat yönünde pistte sol lastikler daha çok şişer => daha düşük soğuk basınç."""
    p = predictor.predict("monza", "ferrari_296_gt3", 22.0, 28.0)
    assert p.fl < p.fr and p.rl < p.rr


def test_counter_clockwise_track_right_tyres_get_lower_cold_pressure():
    p = predictor.predict("imola", "ferrari_296_gt3", 22.0, 28.0)
    assert p.fr < p.fl and p.rr < p.rl


def test_rear_engine_car_rear_tyres_lower_cold_pressure():
    """Arka motorlu Porsche'de arka lastikler daha çok şişer."""
    p = predictor.predict("monza", "porsche_992_gt3_r", 22.0, 28.0)
    assert p.rl < p.fl and p.rr < p.fr


def test_front_engine_car_front_tyres_lower_cold_pressure():
    p = predictor.predict("monza", "bmw_m4_gt3", 22.0, 28.0)
    assert p.fl < p.rl and p.fr < p.rr


def test_hotter_weather_lowers_cold_pressure():
    cool = predictor.predict("monza", "ferrari_296_gt3", 18.0, 22.0)
    hot = predictor.predict("monza", "ferrari_296_gt3", 30.0, 42.0)
    assert hot.fl < cool.fl


def test_aggressive_driver_lowers_cold_pressure():
    calm = predictor.predict("spa", "ferrari_296_gt3", 22.0, 28.0, {"avg_lateral_g": 1.2})
    hard = predictor.predict("spa", "ferrari_296_gt3", 22.0, 28.0, {"avg_lateral_g": 1.8})
    assert hard.fl < calm.fl
