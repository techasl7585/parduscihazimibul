#!/usr/bin/python3
from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from typing import Any

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402


API_ROOT = "http://127.0.0.1:8765"


class LocalApi:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({})
        )

    def request(
        self, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = None
        headers: dict[str, str] = {}
        method = "GET"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
            method = "POST"
        request = urllib.request.Request(
            API_ROOT + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with self.opener.open(request, timeout=25) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                message = json.load(exc).get("error", str(exc))
            except (ValueError, AttributeError):
                message = str(exc)
            raise RuntimeError(message) from exc
        except (OSError, urllib.error.URLError) as exc:
            raise RuntimeError(
                "Pardus Cihazımı Bul servisine ulaşılamıyor."
            ) from exc
        if not result.get("ok"):
            raise RuntimeError(
                str(result.get("error") or result.get("message") or "İşlem başarısız")
            )
        return result


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application):
        super().__init__(application=application)
        self.api = LocalApi()
        self.config: dict[str, Any] = {}
        self.server_local_ip: str | None = None
        self.location_status: dict[str, str] = {}
        self.devices: list[dict[str, Any]] = []
        self.sharing = False
        self.busy = False
        self.refresh_running = False

        self.set_title("Pardus Cihazımı Bul")
        self.set_icon_name("pardus-cihazimi-bul")
        self.set_default_size(760, 720)
        self.set_size_request(560, 600)
        self.set_position(Gtk.WindowPosition.CENTER)

        self._load_styles()
        self._build_ui()
        self.show_all()
        self.phone_card.set_visible(False)
        self._run_background(self._load_state, self._state_loaded)
        GLib.timeout_add_seconds(5, self._periodic_refresh)

    def _load_styles(self) -> None:
        css = b"""
        window {
          background: #071723;
          color: #f4fbff;
          font-family: Inter, "Noto Sans", sans-serif;
        }
        .page { padding: 34px; }
        .brand { color: #f4fbff; font-size: 17px; font-weight: 800; }
        .brand-mark {
          min-width: 46px;
          min-height: 46px;
          border: 1px solid #66e6dc;
          border-radius: 15px;
          color: #062128;
          background: #66e6dc;
          font-size: 21px;
          font-weight: 900;
        }
        .version-chip, .privacy-chip {
          border: 1px solid #294b5e;
          border-radius: 99px;
          color: #9bb4c2;
          background: #0b2130;
          font-size: 10px;
          font-weight: 700;
          padding: 6px 10px;
        }
        .muted { color: #8fa8b7; }
        .eyebrow {
          color: #52d9d0;
          font-size: 11px;
          font-weight: 800;
        }
        .title {
          color: #f4fbff;
          font-size: 32px;
          font-weight: 800;
        }
        .status-card, .phone-card {
          background: #0c2638;
          border: 1px solid #2a5264;
          border-radius: 22px;
          padding: 26px;
          box-shadow: 0 16px 45px alpha(#000000, 0.28);
        }
        .status-card { border-top: 3px solid #45d8cf; }
        .status-badge {
          border: 1px solid #356071;
          border-radius: 99px;
          color: #9db7c5;
          background: #102f42;
          font-size: 10px;
          font-weight: 800;
          padding: 6px 11px;
        }
        .status-badge.active {
          border-color: #377759;
          color: #a7f1c1;
          background: #123b31;
        }
        .locator {
          color: #56ddd5;
          font-size: 68px;
          font-weight: 400;
        }
        .status-title {
          color: #f4fbff;
          font-size: 22px;
          font-weight: 800;
        }
        .status-detail { color: #91a9b8; font-size: 13px; }
        .share-button {
          min-height: 58px;
          border: 0;
          border-radius: 16px;
          color: #062128;
          background: #66e6dc;
          font-size: 16px;
          font-weight: 800;
          padding: 0 28px;
          box-shadow: 0 10px 28px alpha(#3dd8ce, 0.18);
        }
        .share-button:hover { background: #7df1e8; }
        .share-button.stop {
          color: #ffeef0;
          background: #713444;
        }
        .share-button.stop:hover { background: #834052; }
        .code {
          color: #c9fff9;
          font-family: monospace;
          font-size: 34px;
          font-weight: 800;
        }
        .address {
          color: #68ddd6;
          font-family: monospace;
          font-size: 13px;
        }
        .copy-button {
          min-height: 38px;
          border: 1px solid #31576a;
          border-radius: 11px;
          color: #eefcff;
          background: #123248;
          padding: 0 15px;
        }
        .future-note {
          border: 1px solid #24485a;
          border-radius: 13px;
          color: #9bb5c3;
          background: #091f2e;
          font-size: 11px;
          padding: 13px;
        }
        .error { color: #ff93a0; }
        .success { color: #7be5a6; }
        """
        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(css)
        except GLib.Error:
            provider.load_from_data(
                b"""
                window { background: #071723; color: #f4fbff; }
                .page { padding: 30px; }
                .title { color: #f4fbff; font-size: 30px; font-weight: 800; }
                .muted { color: #8fa8b7; }
                .share-button {
                  min-height: 58px;
                  color: #062128;
                  background: #66e6dc;
                  font-size: 16px;
                  font-weight: 800;
                }
                """
            )
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    @staticmethod
    def _style(widget: Gtk.Widget, *classes: str) -> Gtk.Widget:
        context = widget.get_style_context()
        for class_name in classes:
            context.add_class(class_name)
        return widget

    def _label(
        self,
        text: str,
        *classes: str,
        xalign: float = 0,
        wrap: bool = False,
    ) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=xalign)
        label.set_line_wrap(wrap)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._style(label, *classes)
        return label

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        self._style(root, "page")
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        viewport = Gtk.Viewport()
        viewport.add(root)
        scroller.add(viewport)
        self.add(scroller)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mark = self._label("P", xalign=0.5)
        mark.set_size_request(46, 46)
        self._style(mark, "brand-mark")
        header_copy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        header_copy.pack_start(
            self._label("Pardus", "brand"), False, False, 0
        )
        header_copy.pack_start(
            self._label("Cihazımı Bul", "muted"), False, False, 0
        )
        header.pack_start(mark, False, False, 0)
        header.pack_start(header_copy, False, False, 0)
        header.pack_end(
            self._label("SÜRÜM 0.1.7", "version-chip", xalign=0.5),
            False,
            False,
            0,
        )
        root.pack_start(header, False, False, 0)

        intro = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        intro.pack_start(
            self._label("KONUM PAYLAŞIMI", "eyebrow"), False, False, 0
        )
        intro.pack_start(
            self._label("Bilgisayarınızı kolayca bulun.", "title"),
            False,
            False,
            0,
        )
        intro.pack_start(
            self._label(
                "Tek düğmeyle konum paylaşımını açın ve bilgisayarınızın "
                "konumunu web panelinden görüntüleyin.",
                "muted",
                wrap=True,
            ),
            False,
            False,
            0,
        )
        root.pack_start(intro, False, False, 0)

        status_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._style(status_card, "status-card")
        status_top = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        self.status_badge = self._label(
            "HAZIRLANIYOR", "status-badge", xalign=0.5
        )
        status_top.pack_start(self.status_badge, False, False, 0)
        status_top.pack_end(
            self._label(
                "Konum denetimi sizde", "privacy-chip", xalign=0.5
            ),
            False,
            False,
            0,
        )
        self.locator = self._label("⌖", "locator", xalign=0.5)
        self.status_title = self._label(
            "Servise bağlanıyor…", "status-title", xalign=0.5
        )
        self.status_detail = self._label(
            "Lütfen kısa bir süre bekleyin.",
            "status-detail",
            xalign=0.5,
            wrap=True,
        )
        self.share_button = Gtk.Button(label="Hazırlanıyor…")
        self._style(self.share_button, "share-button")
        self.share_button.set_sensitive(False)
        self.share_button.connect("clicked", self._on_share_clicked)
        status_card.pack_start(status_top, False, False, 0)
        status_card.pack_start(self.locator, False, False, 0)
        status_card.pack_start(self.status_title, False, False, 0)
        status_card.pack_start(self.status_detail, False, False, 0)
        status_card.pack_start(self.share_button, False, False, 8)
        root.pack_start(status_card, False, False, 0)

        self.phone_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=9
        )
        self._style(self.phone_card, "phone-card")
        self.phone_card.pack_start(
            self._label("WEB PANELİNDE GÖRÜNTÜLE", "eyebrow"),
            False,
            False,
            0,
        )
        self.phone_card.pack_start(
            self._label(
                "Aynı Wi-Fi ağına bağlı bir cihazın web tarayıcısında "
                "bu adresi açın:",
                "muted",
                wrap=True,
            ),
            False,
            False,
            0,
        )
        address_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=10
        )
        self.address_label = self._label("—", "address", wrap=True)
        self.address_label.set_selectable(True)
        self.copy_button = Gtk.Button(label="Adresi Kopyala")
        self._style(self.copy_button, "copy-button")
        self.copy_button.connect("clicked", self._copy_address)
        address_row.pack_start(self.address_label, True, True, 0)
        address_row.pack_start(self.copy_button, False, False, 0)
        self.phone_card.pack_start(address_row, False, False, 0)
        self.phone_card.pack_start(
            self._label("Erişim kodu", "muted"), False, False, 0
        )
        self.code_label = self._label("••••••••", "code")
        self.code_label.set_selectable(True)
        self.phone_card.pack_start(self.code_label, False, False, 0)
        self.phone_card.pack_start(
            self._label(
                "Bu ilk sürüm aynı Wi-Fi ağında çalışır. Proje "
                "geliştirildiğinde güvenli merkez sunucusu sayesinde "
                "web paneli ve bilgisayar farklı ağlarda olsa da konum "
                "görüntülenebilecektir.",
                "future-note",
                wrap=True,
            ),
            False,
            False,
            5,
        )
        root.pack_start(self.phone_card, False, False, 0)

        self.message_label = self._label("", "muted", xalign=0.5, wrap=True)
        root.pack_start(self.message_label, False, False, 0)

    def _run_background(self, function, callback) -> None:
        def worker() -> None:
            try:
                result = function()
                GLib.idle_add(callback, result, None)
            except Exception as exc:  # boundary between worker and UI
                GLib.idle_add(callback, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _load_state(self) -> dict[str, Any]:
        bootstrap = self.api.request("/api/bootstrap")
        devices = self.api.request("/api/devices").get("devices", [])
        return {"bootstrap": bootstrap, "devices": devices}

    def _state_loaded(
        self, result: dict[str, Any] | None, error: str | None
    ) -> bool:
        self.refresh_running = False
        if error or result is None:
            self._show_error(error or "Servise bağlanılamadı.")
            return False
        bootstrap = result["bootstrap"]
        self.config = bootstrap["config"]
        self.location_status = bootstrap.get("location_status") or {}
        self.server_local_ip = bootstrap.get("server_local_ip")
        self.devices = result["devices"]
        self.sharing = bool(self.config.get("location_enabled"))
        self._render()
        return False

    def _render(self) -> None:
        self.share_button.set_sensitive(not self.busy)
        self.share_button.get_style_context().remove_class("stop")
        self.status_badge.get_style_context().remove_class("active")
        if self.busy:
            self.status_badge.set_text("KONUM HAZIRLANIYOR")
            self.share_button.set_label("Konum hazırlanıyor…")
            self.status_title.set_text("Pardus Konum Servisi çalışıyor")
            self.status_detail.set_text(
                "Bilgisayarın konumu belirleniyor. Bu işlem kısa sürebilir."
            )
            return

        if not self.sharing:
            self.status_badge.set_text("PAYLAŞIM KAPALI")
            self.status_title.set_text("Konum paylaşımı kapalı")
            self.status_detail.set_text(
                "Siz düğmeye basana kadar hiçbir konum paylaşılmaz."
            )
            self.share_button.set_label("Konumumu Paylaş")
            self.phone_card.set_visible(False)
            self.message_label.set_text("")
            return

        self.share_button.get_style_context().add_class("stop")
        self.share_button.set_label("Paylaşımı Durdur")
        device = next(
            (
                item
                for item in self.devices
                if item.get("device_id") == self.config.get("device_id")
            ),
            None,
        )
        if device and device.get("latitude") is not None:
            self.status_badge.set_text("KONUM AKTİF")
            self.status_badge.get_style_context().add_class("active")
            accuracy = device.get("accuracy_m")
            suffix = (
                f" · yaklaşık {round(float(accuracy))} m hassasiyet"
                if accuracy
                else ""
            )
            self.status_title.set_text("Konum paylaşılıyor")
            source = device.get("location_source")
            if source == "pardus-positon":
                detail = (
                    f"Bilgisayarın Wi-Fi ağlarıyla konumu bulundu{suffix}."
                )
            elif source == "pardus-wifi":
                detail = f"Wi-Fi ağlarıyla yaklaşık konum bulundu{suffix}."
            elif source == "pardus-network":
                detail = f"Ağ bağlantısıyla yaklaşık konum bulundu{suffix}."
            else:
                detail = f"Pardus Konum Servisi konumu buldu{suffix}."
            self.status_detail.set_text(detail)
        else:
            location_state = self.location_status.get("state")
            if location_state == "unavailable":
                self.status_badge.set_text("KONUM ALINAMADI")
                self.status_title.set_text("Konum kaynağı bulunamadı")
                self.status_detail.set_text(
                    self.location_status.get("message")
                    or "Pardus Konum Servisi konum üretemedi."
                )
            else:
                self.status_badge.set_text("KONUM ARANIYOR")
                self.status_title.set_text("Konum aranıyor")
                self.status_detail.set_text(
                    "Pardus Konum Servisi uygun konum kaynağını bekliyor."
                )
        self._show_phone_details()

    def _show_phone_details(self) -> None:
        host = self.server_local_ip or "BU-BİLGİSAYARIN-IP-ADRESİ"
        viewer_code = str(self.config.get("viewer_code") or "")
        phone_url = f"http://{host}:8765/"
        self.address_label.set_text(phone_url)
        self.address_label.set_tooltip_text(
            f"{phone_url}#code={viewer_code}"
        )
        self.code_label.set_text(viewer_code or "••••••••")
        self.phone_card.set_visible(True)
        self.phone_card.show_all()

    def _on_share_clicked(self, _button: Gtk.Button) -> None:
        if self.busy:
            return
        desired = not self.sharing
        self.busy = True
        self.message_label.set_text("")
        self._render()

        def change_sharing() -> dict[str, Any]:
            settings = self.api.request(
                "/api/settings", {"location_enabled": desired}
            )
            send_result = None
            if desired:
                send_result = self.api.request("/api/send-now", {})
            return {"settings": settings, "send": send_result}

        self._run_background(
            change_sharing,
            lambda result, error: self._sharing_changed(
                desired, result, error
            ),
        )

    def _sharing_changed(
        self,
        desired: bool,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> bool:
        self.busy = False
        if error or result is None:
            self._show_error(error or "Konum paylaşımı değiştirilemedi.")
            return False
        self.config.update(result["settings"]["config"])
        self.sharing = desired
        self.message_label.get_style_context().remove_class("error")
        self.message_label.get_style_context().add_class("success")
        self.message_label.set_text(
            "Konum paylaşımı açıldı."
            if desired
            else "Konum paylaşımı durduruldu."
        )
        self._render()
        self._start_refresh()
        return False

    def _copy_address(self, _button: Gtk.Button) -> None:
        host = self.server_local_ip or ""
        viewer_code = str(self.config.get("viewer_code") or "")
        if not host or not viewer_code:
            self._show_error("Telefon bağlantısı henüz hazır değil.")
            return
        full_url = f"http://{host}:8765/#code={viewer_code}"
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(full_url, -1)
        clipboard.store()
        self.message_label.get_style_context().remove_class("error")
        self.message_label.get_style_context().add_class("success")
        self.message_label.set_text("Telefon adresi kopyalandı.")

    def _show_error(self, message: str) -> None:
        self.busy = False
        self.share_button.set_sensitive(False if not self.config else True)
        self.status_title.set_text("Bir sorun oluştu")
        self.status_detail.set_text(message)
        self.message_label.get_style_context().remove_class("success")
        self.message_label.get_style_context().add_class("error")
        self.message_label.set_text(message)

    def _start_refresh(self) -> None:
        if self.refresh_running:
            return
        self.refresh_running = True
        self._run_background(self._load_state, self._state_loaded)

    def _periodic_refresh(self) -> bool:
        self._start_refresh()
        return True


class PardusFindApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="tr.org.pardus.CihazimiBul")

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = MainWindow(self)
        window.present()


def main() -> int:
    application = PardusFindApplication()
    return application.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
