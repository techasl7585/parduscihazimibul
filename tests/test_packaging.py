from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_clean_install_dependencies_are_declared(self) -> None:
        control = (
            PROJECT_ROOT / "packaging" / "rootfs" / "DEBIAN" / "control"
        ).read_text(encoding="utf-8")
        required = (
            "python3",
            "python3-gi",
            "gir1.2-gtk-3.0",
            "geoclue-2.0",
            "gir1.2-geoclue-2.0",
            "glib-networking",
            "network-manager",
            "adduser",
            "ca-certificates",
            "systemd",
        )
        for package in required:
            with self.subTest(package=package):
                self.assertIn(package, control)

    def test_install_enables_service_and_creates_runtime_user(self) -> None:
        postinst = (
            PROJECT_ROOT / "packaging" / "rootfs" / "DEBIAN" / "postinst"
        ).read_text(encoding="utf-8")
        self.assertIn('SERVICE_USER="pardus-find"', postinst)
        self.assertIn("adduser", postinst)
        self.assertIn("systemctl enable pardus-cihazimi-bul.service", postinst)
        self.assertIn("systemctl restart pardus-cihazimi-bul.service", postinst)

    def test_desktop_launcher_starts_native_application(self) -> None:
        desktop = (
            PROJECT_ROOT
            / "packaging"
            / "rootfs"
            / "usr"
            / "share"
            / "applications"
            / "pardus-cihazimi-bul.desktop"
        ).read_text(encoding="utf-8")
        launcher = (
            PROJECT_ROOT
            / "packaging"
            / "rootfs"
            / "usr"
            / "bin"
            / "pardus-cihazimi-bul"
        ).read_text(encoding="utf-8")
        self.assertIn("Exec=pardus-cihazimi-bul", desktop)
        self.assertIn("/opt/pardus-cihazimi-bul/native_app.py", launcher)

    def test_native_copy_uses_web_panel_and_has_no_footer_notice(self) -> None:
        native = (PROJECT_ROOT / "src" / "native_app.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Bilgisayarınızı kolayca bulun.", native)
        self.assertIn("konumunu web panelinden görüntüleyin.", native)
        self.assertIn("WEB PANELİNDE GÖRÜNTÜLE", native)
        self.assertNotIn("telefonunuzdan görüntüleyin", native)
        self.assertNotIn('"privacy-row"', native)

    def test_beacondb_is_configured_without_submission(self) -> None:
        config = (
            PROJECT_ROOT
            / "packaging"
            / "rootfs"
            / "etc"
            / "geoclue"
            / "conf.d"
            / "91-pardus-cihazimi-bul-wifi.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("[wifi]", config)
        self.assertIn(
            "url=https://api.beacondb.net/v1/geolocate", config
        )
        self.assertIn("submit-data=false", config)

    def test_package_installs_https_backend(self) -> None:
        control = (
            PROJECT_ROOT / "packaging" / "rootfs" / "DEBIAN" / "control"
        ).read_text(encoding="utf-8")
        self.assertIn("glib-networking", control)
        self.assertIn("network-manager", control)


if __name__ == "__main__":
    unittest.main()
