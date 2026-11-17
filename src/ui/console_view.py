"""
Rich ile canlı terminal paneli. Yalnızca SessionState'i çizer, iş mantığı içermez.
"""

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.app.session import ConnectionStatus, SessionState
from src.core.config import MAX_OPTIMAL_PRESSURE, MIN_OPTIMAL_PRESSURE, TARGET_HOT_PRESSURE_GT3

WHEELS = (("fl", "Ön Sol (FL)"), ("fr", "Ön Sağ (FR)"), ("rl", "Arka Sol (RL)"), ("rr", "Arka Sağ (RR)"))
STATUS_STYLE = {
    ConnectionStatus.WAITING_FOR_GAME: "yellow",
    ConnectionStatus.NOT_LIVE: "yellow",
    ConnectionStatus.IN_PIT: "cyan",
    ConnectionStatus.DRIVING: "green",
}


def _pressure_style(psi: float) -> str:
    """İdeal sıcak aralıkta yeşil, altında mavi, üstünde kırmızı."""
    if psi < MIN_OPTIMAL_PRESSURE:
        return "blue"
    return "green" if psi <= MAX_OPTIMAL_PRESSURE else "red"


def _fmt_lap_time(ms: int) -> str:
    """ACC geçersiz süreyi çok büyük sayıyla bildirir; onu '-' göster."""
    if ms <= 0 or ms > 3_600_000:
        return "-"
    minutes, seconds = divmod(ms / 1000, 60)
    return f"{int(minutes)}:{seconds:06.3f}"


# Terminal arayüzünü çizen sınıf
class ConsoleView:
    def __init__(self):
        self.console = Console()

    def render(self, s: SessionState) -> Group:
        return Group(self._header(s), self._tyres(s), self._recommendation(s), self._laps(s), self._events(s))

    def _header(self, s: SessionState) -> Panel:
        text = Text()
        text.append("Durum: ", style="bold")
        text.append(s.status.value, style=f"bold {STATUS_STYLE[s.status]}")
        if s.track_name:
            text.append(f"\nPist: {s.track_name}    Araç: {s.car_model}")
            text.append(f"\nHava: {s.ambient_temp:.1f} °C    Pist: {s.track_temp:.1f} °C")
            text.append(f"\nTahmin modeli: {s.model_name}")
            text.append(f"\nBu pistte kayıtlı temiz tur: {s.valid_track_laps}/{s.laps_needed_for_ml} "
                        "(ML için gerekli)")
        for warning in s.warnings:
            text.append(f"\n! {warning}", style="yellow")
        return Panel(text, title="ACC Lastik Basıncı Asistanı", border_style="blue")

    def _tyres(self, s: SessionState) -> Panel:
        if s.sample is None:
            return Panel("Telemetri bekleniyor...", title="Lastikler")

        if s.cold_pressures is None:
            cold_note = "Soğuk basınç henüz belirlenmedi"
        elif s.cold_locked:
            cold_note = "Soğuk basınç KİLİTLİ (bu stint için belirlendi)"
        else:
            cold_note = "Garajda izleniyor, piste çıkınca kilitlenecek"

        table = Table(expand=True, caption=cold_note)
        for column in ("Lastik", "Anlık (PSI)", "Sıcaklık (°C)", "Soğuk (PSI)", "Şişme ΔP"):
            table.add_column(column, justify="right" if column != "Lastik" else "left")

        for key, label in WHEELS:
            now = getattr(s.sample.pressures, key)
            temp = getattr(s.sample.temperatures, key)
            cold = getattr(s.cold_pressures, key) if s.cold_pressures else None
            table.add_row(
                label,
                Text(f"{now:.2f}", style=_pressure_style(now)),
                f"{temp:.0f}",
                f"{cold:.2f}" if cold is not None else "-",
                f"{now - cold:+.2f}" if cold is not None else "-",
            )
        return Panel(table, title="Lastikler")

    def _recommendation(self, s: SessionState) -> Panel:
        title = f"Garajda girilecek SOĞUK basınç (hedef sıcak: {TARGET_HOT_PRESSURE_GT3} PSI)"
        if s.recommended is None:
            return Panel("Öneri için oyun verisi bekleniyor...", title=title, border_style="green")
        table = Table(expand=True)
        for _, label in WHEELS:
            table.add_column(label, justify="center")
        table.add_row(*(Text(f"{getattr(s.recommended, key):.1f}", style="bold green") for key, _ in WHEELS))
        return Panel(table, title=title, border_style="green")

    def _laps(self, s: SessionState) -> Panel:
        if not s.session_laps:
            return Panel("Bu seansta henüz tamamlanan tur yok.", title="Turlar")
        table = Table(expand=True)
        for column in ("Tur", "Süre", "Yanal G", "ΔP FL", "ΔP FR", "ΔP RL", "ΔP RR"):
            table.add_column(column, justify="right")
        for lap in s.session_laps[-5:]:
            d = lap.delta_pressures
            table.add_row(str(lap.lap_number), _fmt_lap_time(lap.lap_time_ms), f"{lap.avg_lateral_g:.2f}",
                          f"{d.fl:+.2f}", f"{d.fr:+.2f}", f"{d.rl:+.2f}", f"{d.rr:+.2f}")
        return Panel(table, title="Son turlar (bu seans)")

    def _events(self, s: SessionState) -> Panel:
        body = Text("\n".join(s.events) if s.events else "Henüz olay yok")
        return Panel(body, title="Olaylar", border_style="dim")
