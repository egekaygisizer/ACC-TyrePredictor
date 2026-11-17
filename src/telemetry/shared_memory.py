"""
ACC Windows Shared Memory (acpmf_*) okuyucusu.

Bellek alanları OpenFileMapping ile açılır: ACC kapalıysa alan YOKTUR ve bağlantı başarısız olur.
(mmap.mmap + tagname alanı sessizce oluşturur ve ACC kapalıyken bile "bağlı" gibi görünürdü.)
"""

import sys
import ctypes
from typing import Optional

from src.telemetry.base import ITelemetryProvider
from src.core.models import TelemetrySample, WheelSet

FILE_MAP_READ = 0x0004
ACC_STATUS_LIVE = 2  # graphics.status: 0=OFF, 1=REPLAY, 2=LIVE, 3=PAUSE


# ACC "Local\acpmf_physics" yapısı (alan sırası Kunos tanımıyla birebir aynı olmak zorunda)
class SPageFilePhysics(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("gas", ctypes.c_float),
        ("brake", ctypes.c_float),
        ("fuel", ctypes.c_float),
        ("gear", ctypes.c_int),
        ("rpms", ctypes.c_int),
        ("steerAngle", ctypes.c_float),
        ("speedKmh", ctypes.c_float),
        ("velocity", ctypes.c_float * 3),
        ("accG", ctypes.c_float * 3),                  # [0]: yanal, [1]: dikey, [2]: boyuna
        ("wheelSlip", ctypes.c_float * 4),
        ("wheelLoad", ctypes.c_float * 4),
        ("wheelsPressure", ctypes.c_float * 4),        # PSI
        ("wheelAngularSpeed", ctypes.c_float * 4),
        ("tyreWear", ctypes.c_float * 4),
        ("tyreDirtyLevel", ctypes.c_float * 4),
        ("tyreCoreTemperature", ctypes.c_float * 4),   # °C
        ("camberRAD", ctypes.c_float * 4),
        ("suspensionTravel", ctypes.c_float * 4),
        ("drs", ctypes.c_float),
        ("tc", ctypes.c_float),
        ("heading", ctypes.c_float),
        ("pitch", ctypes.c_float),
        ("roll", ctypes.c_float),
        ("cgHeight", ctypes.c_float),
        ("carDamage", ctypes.c_float * 5),
        ("numberOfTyresOut", ctypes.c_int),
        ("pitLimiterOn", ctypes.c_int),
        ("abs", ctypes.c_float),
        ("kersCharge", ctypes.c_float),
        ("kersInput", ctypes.c_float),
        ("autoShifterOn", ctypes.c_int),
        ("rideHeight", ctypes.c_float * 2),
        ("turboBoost", ctypes.c_float),
        ("ballast", ctypes.c_float),
        ("airDensity", ctypes.c_float),
        ("airTemp", ctypes.c_float),                   # Hava sıcaklığı (°C) - physics sayfasında!
        ("roadTemp", ctypes.c_float),                  # Pist sıcaklığı (°C) - physics sayfasında!
    ]


# ACC "Local\acpmf_graphics" yapısı (yalnızca ihtiyaç duyduğumuz kısma kadar)
class SPageFileGraphic(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("status", ctypes.c_int),
        ("session", ctypes.c_int),
        ("currentTime", ctypes.c_wchar * 15),
        ("lastTime", ctypes.c_wchar * 15),
        ("bestTime", ctypes.c_wchar * 15),
        ("split", ctypes.c_wchar * 15),
        ("completedLaps", ctypes.c_int),
        ("position", ctypes.c_int),
        ("iCurrentTime", ctypes.c_int),                # ms
        ("iLastTime", ctypes.c_int),                   # ms
        ("iBestTime", ctypes.c_int),
        ("sessionTimeLeft", ctypes.c_float),
        ("distanceTraveled", ctypes.c_float),
        ("isInPit", ctypes.c_int),
        ("currentSectorIndex", ctypes.c_int),
        ("lastSectorTime", ctypes.c_int),
        ("numberOfLaps", ctypes.c_int),
        ("tyreCompound", ctypes.c_wchar * 33),
        ("replayTimeMultiplier", ctypes.c_float),
        ("normalizedCarPosition", ctypes.c_float),
        ("activeCars", ctypes.c_int),
        ("carCoordinates", (ctypes.c_float * 3) * 60),
        ("carID", ctypes.c_int * 60),
        ("playerCarID", ctypes.c_int),
        ("penaltyTime", ctypes.c_float),
        ("flag", ctypes.c_int),
        ("penalty", ctypes.c_int),
        ("idealLineOn", ctypes.c_int),
        ("isInPitLane", ctypes.c_int),
    ]


# ACC "Local\acpmf_static" yapısı (yalnızca araç ve pist adı için gereken kısım)
class SPageFileStatic(ctypes.Structure):
    _fields_ = [
        ("smVersion", ctypes.c_wchar * 15),
        ("acVersion", ctypes.c_wchar * 15),
        ("numberOfSessions", ctypes.c_int),
        ("numCars", ctypes.c_int),
        ("carModel", ctypes.c_wchar * 33),
        ("track", ctypes.c_wchar * 33),
        ("playerName", ctypes.c_wchar * 33),
        ("playerSurname", ctypes.c_wchar * 33),
        ("playerNick", ctypes.c_wchar * 33),
    ]


# Adlandırılmış bir Windows bellek alanını salt-okunur açan küçük sarmalayıcı
class _MappedPage:
    def __init__(self, name: str, struct_type):
        k32 = ctypes.windll.kernel32
        k32.OpenFileMappingW.restype = ctypes.c_void_p
        k32.OpenFileMappingW.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p]
        k32.MapViewOfFile.restype = ctypes.c_void_p
        k32.MapViewOfFile.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_size_t]
        k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        k32.CloseHandle.argtypes = [ctypes.c_void_p]

        handle = k32.OpenFileMappingW(FILE_MAP_READ, False, name)
        if not handle:
            raise OSError(f"{name} bulunamadı (ACC kapalı olabilir)")
        view = k32.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, ctypes.sizeof(struct_type))
        if not view:
            k32.CloseHandle(handle)
            raise OSError(f"{name} belleğe eşlenemedi")

        self._k32, self._handle, self._view, self._type = k32, handle, view, struct_type

    def read(self):
        """Anlık görüntüyü kopyalayarak döner (oyun yazarken tutarlı veri için)."""
        copy = self._type()
        ctypes.memmove(ctypes.byref(copy), self._view, ctypes.sizeof(self._type))
        return copy

    def close(self) -> None:
        self._k32.UnmapViewOfFile(self._view)
        self._k32.CloseHandle(self._handle)


# Windows üzerinde ACC'nin paylaşılan belleğini okuyan sağlayıcı
class SharedMemoryProvider(ITelemetryProvider):
    def __init__(self):
        self._physics: Optional[_MappedPage] = None
        self._graphics: Optional[_MappedPage] = None
        self._static: Optional[_MappedPage] = None

    def is_connected(self) -> bool:
        """3 bellek alanı da açılabiliyorsa ACC çalışıyordur."""
        if not sys.platform.startswith("win"):
            return False
        if self._physics:
            return True
        try:
            self._physics = _MappedPage("Local\\acpmf_physics", SPageFilePhysics)
            self._graphics = _MappedPage("Local\\acpmf_graphics", SPageFileGraphic)
            self._static = _MappedPage("Local\\acpmf_static", SPageFileStatic)
            return True
        except OSError:
            self.close()
            return False

    def get_sample(self) -> Optional[TelemetrySample]:
        """Üç bellek sayfasını okuyup TelemetrySample'a çevirir; ACC kapalıysa None döner."""
        if not self.is_connected():
            return None
        try:
            phys = self._physics.read()
            gfx = self._graphics.read()
            stat = self._static.read()
        except OSError:
            return None

        def wheels(values, digits):
            return WheelSet.from_iterable(round(float(v), digits) for v in values)

        return TelemetrySample(
            packet_id=phys.packetId,
            speed_kmh=round(float(phys.speedKmh), 1),
            gear=phys.gear - 1,  # ACC: 0=R, 1=N, 2=1. vites -> 0=N yapılır
            rpms=phys.rpms,
            steer_angle=round(float(phys.steerAngle), 3),
            gas=round(float(phys.gas), 2),
            brake=round(float(phys.brake), 2),
            acc_lateral_g=round(float(phys.accG[0]), 2),
            acc_longitudinal_g=round(float(phys.accG[2]), 2),
            pressures=wheels(phys.wheelsPressure, 2),
            temperatures=wheels(phys.tyreCoreTemperature, 1),
            wheel_slip=wheels(phys.wheelSlip, 3),
            track_name=stat.track.strip(),
            car_model=stat.carModel.strip(),
            ambient_temp=round(float(phys.airTemp), 1),
            track_temp=round(float(phys.roadTemp), 1),
            is_in_pit=bool(gfx.isInPit or gfx.isInPitLane),
            completed_laps=gfx.completedLaps,
            current_lap_time_ms=gfx.iCurrentTime,
            last_lap_time_ms=gfx.iLastTime,
            is_live=(gfx.status == ACC_STATUS_LIVE),
        )

    def close(self) -> None:
        """Açık bellek eşlemelerini kapatır."""
        for page in (self._physics, self._graphics, self._static):
            if page:
                page.close()
        self._physics = self._graphics = self._static = None
