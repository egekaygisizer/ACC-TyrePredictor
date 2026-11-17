"""
ACC'deki tüm GT3 araçlarının motor yerleşimi ve aks yükü bilgi bankası.
Arka motor (Porsche): Arka lastikler daha çok şişer (+).
Ön motor (BMW, Aston, Bentley, Mercedes, Nissan, Mustang, Lexus): Ön lastikler daha çok şişer (-).
Orta motor (Ferrari, Audi, Lamborghini, McLaren, Honda): Dengeli şişer (0.0).
"""

from typing import Dict


# Araç modeline göre arka aks şişme ofseti (PSI)
# Pozitif (+): Arka lastikler öne göre daha çok şişer (daha düşük soğuk basınç gerekir)
# Negatif (-): Ön lastikler arkaya göre daha çok şişer
ACC_CARS_DATABASE: Dict[str, float] = {
    # --- PORSCHE (ARKA MOTOR / REAR ENGINE) ---
    "porsche_991_gt3_r": 0.20,
    "porsche_991ii_gt3_r": 0.20,
    "porsche_992_gt3_r": 0.20,

    # --- ÖN MOTORLU ARAÇLAR (FRONT ENGINE) ---
    "amr_v12_vantage_gt3": -0.15,
    "amr_v8_vantage_gt3": -0.15,
    "aston_martin_vantage_v8": -0.15,
    "bentley_continental_gt3_2015": -0.20,
    "bentley_continental_gt3_2018": -0.20,
    "bmw_m6_gt3": -0.15,
    "bmw_m4_gt3": -0.15,
    "jaguar_g3": -0.15,
    "lexus_rc_f_gt3": -0.15,
    "mercedes_amg_gt3": -0.15,
    "mercedes_amg_gt3_evo": -0.15,
    "nissan_gt_r_gt3_2015": -0.15,
    "nissan_gt_r_gt3_2018": -0.15,
    "ford_mustang_gt3": -0.15,

    # --- ORTA MOTORLU ARAÇLAR (MID ENGINE) ---
    "audi_r8_lms": 0.0,
    "audi_r8_lms_evo": 0.0,
    "audi_r8_lms_evo_ii": 0.0,
    "ferrari_488_gt3": 0.0,
    "ferrari_488_gt3_evo": 0.0,
    "ferrari_296_gt3": 0.0,
    "honda_nsx_gt3": 0.0,
    "honda_nsx_gt3_evo": 0.0,
    "lamborghini_huracan_gt3": 0.0,
    "lamborghini_huracan_gt3_evo": 0.0,
    "lamborghini_huracan_gt3_evo2": 0.0,
    "mclaren_650s_gt3": 0.0,
    "mclaren_720s_gt3": 0.0,
    "mclaren_720s_gt3_evo": 0.0,
    "reiter_engineering_r_ex_gt3": 0.0,
}


# Araç adına göre arka aks bias değerini getiren yardımcı fonksiyon
def get_rear_bias(car_model: str) -> float:
    """Bilinmeyen bir araç gelirse dengeli (0.0) kabul eder."""
    normalized = car_model.lower().strip().replace(" ", "_")
    return ACC_CARS_DATABASE.get(normalized, 0.0)


# Aracın veritabanında tanımlı olup olmadığını döner (arayüzde uyarı göstermek için)
def is_known_car(car_model: str) -> bool:
    return car_model.lower().strip().replace(" ", "_") in ACC_CARS_DATABASE
