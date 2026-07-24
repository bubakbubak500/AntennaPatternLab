from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[1]


def test_release_version_is_040_everywhere():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = (
        ROOT / "src" / "antenna_pattern_lab" / "__init__.py"
    ).read_text(encoding="utf-8")
    installer = (
        ROOT / "installer" / "AntennaPatternLab.iss"
    ).read_text(encoding="utf-8")
    assert metadata["project"]["version"] == "0.40.0"
    assert '__version__ = "0.40.0"' in package
    assert '#define MyAppVersion "0.40.0"' in installer


def test_installer_preserves_user_data_and_can_sign_uninstaller():
    script = (ROOT / "installer" / "AntennaPatternLab.iss").read_text(encoding="utf-8")
    assert "SignedUninstaller=yes" in script
    assert "SignTool=aplsign" in script
    assert "PrivilegesRequired=lowest" in script
    assert "AppData" not in "\n".join(
        line for line in script.splitlines() if line.startswith("[UninstallDelete]")
    )


def test_dependencies_are_delegated_to_the_verified_first_run_assistant():
    script = (ROOT / "installer" / "AntennaPatternLab.iss").read_text(encoding="utf-8")
    run_section = script.split("[Run]", 1)[1].split("[Code]", 1)[0]
    assert "github.com/Hamlib" not in run_section
    assert "wsjtx.github.io" not in run_section
    assert "SHA-256" in script
    assert "two separate confirmations" in script


def test_installer_recognizes_previous_version_and_updates_in_place():
    script = (ROOT / "installer" / "AntennaPatternLab.iss").read_text(encoding="utf-8")
    assert "AppId={{B7DDF2C6-503F-4A6D-A8DA-B1E28EE54163}" in script
    assert "UsePreviousAppDir=yes" in script
    assert "UsePreviousTasks=yes" in script
    assert "DisableDirPage=auto" in script
    assert "ExistingInstallationVersion" in script
    assert "UpgradeDetected" in script


def test_installer_uses_application_icon_and_fills_dependency_memo():
    script = (ROOT / "installer" / "AntennaPatternLab.iss").read_text(encoding="utf-8")
    assert "SetupIconFile=..\\src\\antenna_pattern_lab\\assets\\app-icon.ico" in script
    assert "CustomMessage('DependencyResults')" in script
    assert "Summary);" in script
    assert "Summary,\n    '');" not in script
    assert (ROOT / "src" / "antenna_pattern_lab" / "assets" / "app-icon.ico").is_file()
    spec = (ROOT / "AntennaPatternLab.spec").read_text(encoding="utf-8")
    assert 'icon="src/antenna_pattern_lab/assets/app-icon.ico"' in spec
    assert "assets/app-icon.png" in spec
    assert 'AppUserModelID: "OK7PS.AntennaPatternLab"' in script
    assert 'IconFilename: "{app}\\AntennaPatternLab.ico"' in script


def test_release_workflow_uses_notes_for_the_project_version():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    assert '--notes-file "docs\\RELEASE_NOTES_$version.md"' in workflow
    assert "RELEASE_NOTES_0.35.0.md" not in workflow
