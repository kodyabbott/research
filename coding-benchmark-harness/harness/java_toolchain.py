"""JDK 8 toolchain: download, pin, verify, and drive `javac` / `java` inside the sandbox.

Azul Zulu 8 for macOS aarch64 is the primary toolchain, as a tarball with no installer and no
sudo. Eclipse Temurin publishes no aarch64 JDK 8 build (x64 only), which is why Zulu.

The SHA-256 comes from Azul's own per-package detail endpoint, not from the download: the package
*listing* endpoint returns an empty `sha256_hash`, while
`/metadata/v1/zulu/packages/{package_uuid}` carries it. Trust-on-first-download exists only as a
documented fallback for when that endpoint is unreachable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CACHE_ROOT = Path.home() / "Documents/Codex/model-cache/coding-benchmark"
JDK_DIR = CACHE_ROOT / "jdk"
TOOLCHAIN_JSON = Path(__file__).resolve().parents[1] / "toolchain.json"

AZUL_PACKAGE_UUID = "16811ca3-e48b-459d-abc4-f6b273023a54"
AZUL_DETAIL_URL = f"https://api.azul.com/metadata/v1/zulu/packages/{AZUL_PACKAGE_UUID}"
AZUL_LIST_URL = (
    "https://api.azul.com/metadata/v1/zulu/packages/?java_version=8&os=macos&arch=aarch64"
    "&java_package_type=jdk&javafx_bundled=false&release_status=ga&availability_types=CA"
    "&latest=true&archive_type=tar.gz")

# Pinned by the design, confirmed against AZUL_DETAIL_URL on 2026-09-30.
ZULU8 = {
    "vendor": "Azul Zulu",
    "product": "zulu",
    "distroVersion": "8.96.0.205",
    "javaVersion": "8.0.504",
    "filename": "zulu8.96.0.205-ca-jdk8.0.504-macosx_aarch64.tar.gz",
    "url": "https://cdn.azul.com/zulu/bin/zulu8.96.0.205-ca-jdk8.0.504-macosx_aarch64.tar.gz",
    "packageUuid": AZUL_PACKAGE_UUID,
    "sha256": "58bb3c08f2aa63d9743cf31899fa4b8c6c9effefce9479e7288c26621c3bb21b",
    "md5": "3005a491375d87d1473bcc78e7f3b0a2",
    "bytes": 103714000,
    "hashSource": AZUL_DETAIL_URL,
    "mode": "jdk8",
}

DOWNLOAD_TIMEOUT = 900
COMPILE_WALL_SECONDS = 60.0
RUN_WALL_SECONDS = 60.0
JAVA_CPU_SECONDS = 120

# Assertions on: HumanEval-X Java tests signal failure with `assert` / AssertionError.
JVM_FLAGS = ["-Xmx512m", "-Xss2m", "-XX:+UseSerialGC", "-XX:-UsePerfData",
             "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", "-ea"]
JAVAC_FLAGS = ["-J-Xmx512m", "-J-XX:-UsePerfData", "-encoding", "UTF-8", "-Xlint:none"]
JAVAC_SOURCE_FLAGS = ["-source", "1.8", "-target", "1.8"]

DIAGNOSTIC_CAP = 8 * 1024


class ToolchainError(RuntimeError):
    pass


@dataclass
class Toolchain:
    java_home: Path
    record: dict

    @property
    def javac(self) -> Path:
        return self.java_home / "bin/javac"

    @property
    def java(self) -> Path:
        return self.java_home / "bin/java"

    @property
    def mode(self) -> str:
        return self.record.get("mode", "jdk8")

    def describe(self) -> dict:
        """The `runtime.javaToolchain` block for the run record."""
        return {
            "vendor": self.record.get("vendor"),
            "version": self.record.get("javaVersion"),
            "distroVersion": self.record.get("distroVersion"),
            "javaHome": str(self.java_home),
            "sha256": self.record.get("sha256"),
            "mode": self.mode,
            "javaVersionOutput": self.record.get("javaVersionOutput"),
            "javacVersionOutput": self.record.get("javacVersionOutput"),
            "hashSource": self.record.get("hashSource"),
            "hashVerifiedAgainstPublishedValue": self.record.get(
                "hashVerifiedAgainstPublishedValue"),
        }

    def javac_argv(self, sources: list[str], classes_dir: str = "classes") -> list[str]:
        flags = list(JAVAC_FLAGS)
        if self.mode == "jdk8":
            flags += JAVAC_SOURCE_FLAGS
        else:  # pragma: no cover - the fallback toolchain is not used in this implementation
            flags += ["--release", "8"]
        return [str(self.javac), *flags, "-d", classes_dir, *sources]

    def java_argv(self, main_class: str = "Main", classes_dir: str = "classes",
                  workdir: str | None = None) -> list[str]:
        flags = list(JVM_FLAGS)
        if workdir:
            flags.append(f"-Djava.io.tmpdir={workdir}")
        return [str(self.java), *flags, "-cp", classes_dir, main_class]


# -- metadata and download ----------------------------------------------------------------------


def fetch_published_metadata(timeout: int = 60) -> dict:
    """Read Azul's per-package detail endpoint, which is the only one carrying `sha256_hash`."""
    with urllib.request.urlopen(AZUL_DETAIL_URL, timeout=timeout) as response:
        payload = json.load(response)
    if not payload.get("sha256_hash"):
        raise ToolchainError(f"{AZUL_DETAIL_URL} returned no sha256_hash")
    return {
        "filename": payload["name"],
        "url": payload["download_url"],
        "sha256": payload["sha256_hash"],
        "md5": payload.get("md5_hash"),
        "bytes": payload.get("size"),
        "javaVersion": ".".join(str(part) for part in payload.get("java_version", [])),
        "distroVersion": ".".join(str(part) for part in payload.get("distro_version", [])),
        "packageUuid": payload.get("package_uuid"),
        "hashSource": AZUL_DETAIL_URL,
    }


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def download_jdk(expected: dict, target: Path, force: bool = False) -> dict:
    """Fetch the tarball and verify it against the published SHA-256. Refuses on mismatch."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        digest = sha256_file(target)
        if digest != expected["sha256"]:
            raise ToolchainError(
                f"{target} is present but its SHA-256 is {digest}, not {expected['sha256']}. "
                f"Delete it and re-run.")
        return {"downloaded": False, "sha256": digest, "bytes": target.stat().st_size,
                "sizeMismatch": None}
    print(f"  downloading {expected['url']} ({expected.get('bytes', 0) / 1e6:.0f} MB)")
    with tempfile.NamedTemporaryFile(delete=False, dir=target.parent, suffix=".part") as handle:
        temporary = Path(handle.name)
        with urllib.request.urlopen(expected["url"], timeout=DOWNLOAD_TIMEOUT) as response:
            shutil.copyfileobj(response, handle, length=1024 * 1024)
    digest = sha256_file(temporary)
    size = temporary.stat().st_size
    if digest != expected["sha256"]:
        temporary.unlink(missing_ok=True)
        raise ToolchainError(
            f"SHA-256 mismatch for {expected['url']}: published {expected['sha256']}, "
            f"downloaded {digest}. Refusing to use it.")
    mismatch = None
    if expected.get("bytes") and size != expected["bytes"]:
        # Azul's metadata `size` is advisory and was observed 410 bytes short of the real file on
        # 2026-09-30. The published SHA-256 already matched, so the hash is the authority here and
        # a size difference is recorded rather than fatal.
        mismatch = {"advertised": expected["bytes"], "actual": size}
        print(f"  note: Azul advertises {expected['bytes']} bytes, file is {size}; "
              f"the published SHA-256 matched, so continuing")
    os.replace(temporary, target)
    return {"downloaded": True, "sha256": digest, "bytes": size, "sizeMismatch": mismatch}


def find_java_home(root: Path) -> Path:
    """Locate `Contents/Home` inside the unpacked macOS bundle."""
    for candidate in sorted(root.glob("*/zulu-*.jdk/Contents/Home")):
        if (candidate / "bin/javac").exists():
            return candidate
    for candidate in sorted(root.glob("*/Contents/Home")):
        if (candidate / "bin/javac").exists():
            return candidate
    for candidate in sorted(root.glob("*/bin/javac")):  # pragma: no cover - non-bundle layout
        return candidate.parents[1]
    raise ToolchainError(f"no JDK with bin/javac found under {root}")


def extract_jdk(tarball: Path, destination: Path) -> Path:
    """Unpack the tarball. Members are checked to stay inside the destination."""
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as archive:
        base = destination.resolve()
        for member in archive.getmembers():
            resolved = (base / member.name).resolve()
            if not str(resolved).startswith(str(base)):
                raise ToolchainError(f"refusing tar member outside the destination: {member.name}")
        archive.extractall(destination, filter="tar")
    return find_java_home(destination)


def tool_version(binary: Path) -> str:
    """`java -version` / `javac -version` output, unsandboxed (this is our own trusted JDK)."""
    result = subprocess.run([str(binary), "-version"], capture_output=True, text=True, timeout=120)
    return ((result.stderr or "") + (result.stdout or "")).strip()


def parse_java_version(text: str) -> dict:
    """Pull the version triple out of `java -version` output.

    JDK 8 prints `openjdk version "1.8.0_504"`; newer JDKs print `openjdk version "21.0.12"`.
    """
    quoted = re.search(r'version "([^"]+)"', text or "")
    version = quoted.group(1) if quoted else None
    major = None
    if version:
        if version.startswith("1."):
            parts = version.split(".")
            major = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        else:
            head = re.match(r"(\d+)", version)
            major = int(head.group(1)) if head else None
    return {"version": version, "major": major,
            "isJava8": major == 8,
            "vendor": "Zulu" if "Zulu" in (text or "") else None}


# -- toolchain.json -----------------------------------------------------------------------------


def write_toolchain(record: dict, path: Path = TOOLCHAIN_JSON) -> None:
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def read_toolchain(path: Path = TOOLCHAIN_JSON) -> dict:
    if not path.exists():
        raise ToolchainError(
            f"{path} is missing. Run: python3 coding-benchmark-harness/prepare.py --jdk")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load(path: Path = TOOLCHAIN_JSON, verify_hash: bool = True) -> Toolchain:
    """Load the pinned toolchain and refuse to proceed if the on-disk JDK changed."""
    record = read_toolchain(path)
    java_home = Path(record["javaHome"])
    if not (java_home / "bin/javac").exists():
        raise ToolchainError(f"javac missing under {java_home}; re-run prepare.py --jdk")
    if verify_hash:
        tarball = Path(record["tarball"])
        if not tarball.exists():
            raise ToolchainError(
                f"the pinned JDK tarball {tarball} is gone; cannot verify the toolchain. "
                f"Re-run prepare.py --jdk.")
        digest = sha256_file(tarball)
        if digest != record["sha256"]:
            raise ToolchainError(
                f"JDK hash mismatch: toolchain.json pins {record['sha256']} but {tarball} "
                f"hashes to {digest}. Refusing to run.")
    return Toolchain(java_home=java_home, record=record)


def prepare(force_download: bool = False, allow_trust_on_first_download: bool = False) -> dict:
    """Download, verify, unpack and pin the JDK. Returns the toolchain.json record."""
    JDK_DIR.mkdir(parents=True, exist_ok=True)
    expected = dict(ZULU8)
    published: dict | None = None
    try:
        published = fetch_published_metadata()
    except Exception as exc:
        if not allow_trust_on_first_download:
            raise ToolchainError(
                f"could not read the published SHA-256 from {AZUL_DETAIL_URL}: {exc!r}. "
                f"Pass --allow-unpinned-jdk to fall back to trust-on-first-download.") from exc
        print(f"  WARNING: {AZUL_DETAIL_URL} unreachable ({exc!r}); "
              f"falling back to the hash pinned in java_toolchain.ZULU8")
    verified_against_published = False
    if published:
        if published["sha256"] != expected["sha256"]:
            raise ToolchainError(
                f"Azul now publishes {published['filename']} with sha256 {published['sha256']}, "
                f"but this harness pins {expected['filename']} / {expected['sha256']}. "
                f"Update java_toolchain.ZULU8 deliberately rather than silently drifting.")
        verified_against_published = True
        print(f"  published sha256 confirmed against {AZUL_DETAIL_URL}")

    tarball = JDK_DIR / expected["filename"]
    info = download_jdk(expected, tarball, force=force_download)
    expected["bytesOnDisk"] = info["bytes"]
    expected["advertisedSizeMismatch"] = info.get("sizeMismatch")
    print(f"  tarball {'downloaded' if info['downloaded'] else 'already cached'}: {tarball} "
          f"({info['bytes']} bytes)")

    unpacked = JDK_DIR / "unpacked"
    java_home = None
    if unpacked.exists():
        try:
            java_home = find_java_home(unpacked)
        except ToolchainError:
            shutil.rmtree(unpacked, ignore_errors=True)
    if java_home is None:
        print("  unpacking")
        java_home = extract_jdk(tarball, unpacked)
    print(f"  JAVA_HOME {java_home}")

    java_text = tool_version(java_home / "bin/java")
    javac_text = tool_version(java_home / "bin/javac")
    parsed = parse_java_version(java_text)
    if not parsed["isJava8"]:
        raise ToolchainError(f"expected a Java 8 JDK, got {parsed['version']!r} from {java_home}")

    record = {
        **expected,
        "tarball": str(tarball),
        "javaHome": str(java_home),
        "javaVersionOutput": java_text,
        "javacVersionOutput": javac_text,
        "parsedVersion": parsed,
        "hashVerifiedAgainstPublishedValue": verified_against_published,
        "azulListEndpoint": AZUL_LIST_URL,
        "pinnedAt": "2026-09-30",
        "jvmFlags": JVM_FLAGS,
        "javacFlags": JAVAC_FLAGS + JAVAC_SOURCE_FLAGS,
        "note": "Temurin publishes no aarch64 JDK 8 build, which is why Zulu. The "
                "release8-on-21 fallback in DESIGN-JAVA.md was not needed and is not exercised.",
    }
    write_toolchain(record)
    print(f"  pinned in {TOOLCHAIN_JSON}")
    return record
