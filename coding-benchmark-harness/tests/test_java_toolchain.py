"""JDK toolchain: the pinned hash, `java -version` parsing, and refusal on a changed JDK."""

import json
import tempfile
import unittest
from pathlib import Path

import context  # noqa: F401

from harness import java_toolchain as jt

PREPARED = jt.TOOLCHAIN_JSON.exists()
HINT = "no prepared JDK; run: python3 coding-benchmark-harness/prepare.py --jdk"


class PinCase(unittest.TestCase):
    def test_pinned_package_matches_the_design(self):
        self.assertEqual(jt.ZULU8["filename"],
                         "zulu8.96.0.205-ca-jdk8.0.504-macosx_aarch64.tar.gz")
        self.assertEqual(jt.ZULU8["javaVersion"], "8.0.504")
        self.assertEqual(len(jt.ZULU8["sha256"]), 64)
        self.assertEqual(jt.ZULU8["mode"], "jdk8")

    def test_hash_source_is_the_per_package_detail_endpoint(self):
        # The package *listing* endpoint returns an empty sha256_hash; only the detail endpoint
        # carries it, which is why the URL is per-uuid.
        self.assertEqual(jt.ZULU8["hashSource"], jt.AZUL_DETAIL_URL)
        self.assertIn(jt.AZUL_PACKAGE_UUID, jt.AZUL_DETAIL_URL)
        self.assertTrue(jt.AZUL_DETAIL_URL.startswith(
            "https://api.azul.com/metadata/v1/zulu/packages/"))

    def test_download_url_is_the_azul_cdn(self):
        self.assertTrue(jt.ZULU8["url"].startswith("https://cdn.azul.com/zulu/bin/"))
        self.assertTrue(jt.ZULU8["url"].endswith(jt.ZULU8["filename"]))

    def test_jvm_flags_match_the_design(self):
        for flag in ("-Xmx512m", "-Xss2m", "-XX:+UseSerialGC", "-XX:-UsePerfData",
                     "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", "-ea"):
            self.assertIn(flag, jt.JVM_FLAGS)

    def test_javac_flags_pin_the_source_level(self):
        self.assertEqual(jt.JAVAC_SOURCE_FLAGS, ["-source", "1.8", "-target", "1.8"])
        self.assertIn("-encoding", jt.JAVAC_FLAGS)
        self.assertIn("-J-XX:-UsePerfData", jt.JAVAC_FLAGS)


class VersionParseCase(unittest.TestCase):
    JDK8 = ('openjdk version "1.8.0_504"\n'
            'OpenJDK Runtime Environment (Zulu 8.96.0.205-CA-macos-aarch64) (build 1.8.0_504-b01)\n'
            'OpenJDK 64-Bit Server VM (Zulu 8.96.0.205-CA-macos-aarch64) (build 25.504-b01, '
            'mixed mode)')

    def test_parses_a_jdk8_version(self):
        parsed = jt.parse_java_version(self.JDK8)
        self.assertEqual(parsed["version"], "1.8.0_504")
        self.assertEqual(parsed["major"], 8)
        self.assertTrue(parsed["isJava8"])
        self.assertEqual(parsed["vendor"], "Zulu")

    def test_parses_a_modern_version_and_rejects_it_as_java8(self):
        parsed = jt.parse_java_version('openjdk version "21.0.12" 2024-07-16 LTS')
        self.assertEqual(parsed["major"], 21)
        self.assertFalse(parsed["isJava8"])

    def test_handles_unparseable_output(self):
        parsed = jt.parse_java_version("not a version banner")
        self.assertIsNone(parsed["version"])
        self.assertIsNone(parsed["major"])
        self.assertFalse(parsed["isJava8"])

    def test_handles_empty_output(self):
        self.assertFalse(jt.parse_java_version("")["isJava8"])


class ToolchainJsonCase(unittest.TestCase):
    def test_missing_toolchain_json_raises_with_the_fix(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(jt.ToolchainError) as caught:
                jt.read_toolchain(Path(directory) / "toolchain.json")
            self.assertIn("prepare.py --jdk", str(caught.exception))

    def test_load_refuses_a_changed_jdk_tarball(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            java_home = root / "Contents/Home"
            (java_home / "bin").mkdir(parents=True)
            (java_home / "bin/javac").write_text("#!/bin/sh\n", encoding="utf-8")
            tarball = root / "jdk.tar.gz"
            tarball.write_bytes(b"different bytes than were pinned")
            path = root / "toolchain.json"
            path.write_text(json.dumps({
                "javaHome": str(java_home), "tarball": str(tarball),
                "sha256": "0" * 64, "mode": "jdk8"}), encoding="utf-8")
            with self.assertRaises(jt.ToolchainError) as caught:
                jt.load(path)
            self.assertIn("hash mismatch", str(caught.exception))

    def test_load_refuses_when_the_tarball_is_gone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            java_home = root / "Contents/Home"
            (java_home / "bin").mkdir(parents=True)
            (java_home / "bin/javac").write_text("#!/bin/sh\n", encoding="utf-8")
            path = root / "toolchain.json"
            path.write_text(json.dumps({
                "javaHome": str(java_home), "tarball": str(root / "gone.tar.gz"),
                "sha256": "0" * 64, "mode": "jdk8"}), encoding="utf-8")
            with self.assertRaises(jt.ToolchainError) as caught:
                jt.load(path)
            self.assertIn("cannot verify", str(caught.exception))

    def test_load_refuses_when_javac_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toolchain.json"
            path.write_text(json.dumps({
                "javaHome": str(Path(directory) / "nope"), "tarball": "x",
                "sha256": "0" * 64}), encoding="utf-8")
            with self.assertRaises(jt.ToolchainError) as caught:
                jt.load(path)
            self.assertIn("javac missing", str(caught.exception))

    def test_download_refuses_a_cached_file_with_the_wrong_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "jdk.tar.gz"
            target.write_bytes(b"wrong")
            with self.assertRaises(jt.ToolchainError) as caught:
                jt.download_jdk({"sha256": "0" * 64, "url": "https://example/x"}, target)
            self.assertIn("SHA-256", str(caught.exception))

    def test_extract_refuses_a_tar_member_escaping_the_destination(self):
        import io
        import tarfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "evil.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                data = b"pwned"
                info = tarfile.TarInfo("../escaped.txt")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            with self.assertRaises(jt.ToolchainError) as caught:
                jt.extract_jdk(archive_path, root / "dest")
            self.assertIn("outside the destination", str(caught.exception))


@unittest.skipUnless(PREPARED, HINT)
class PreparedToolchainCase(unittest.TestCase):
    """Checks against the JDK this machine actually prepared."""

    @classmethod
    def setUpClass(cls):
        cls.toolchain = jt.load()

    def test_toolchain_is_java_8(self):
        parsed = self.toolchain.record["parsedVersion"]
        self.assertTrue(parsed["isJava8"], parsed)
        self.assertEqual(parsed["major"], 8)
        self.assertEqual(self.toolchain.mode, "jdk8")

    def test_hash_was_verified_against_the_published_value(self):
        self.assertTrue(self.toolchain.record["hashVerifiedAgainstPublishedValue"])
        self.assertEqual(self.toolchain.record["sha256"], jt.ZULU8["sha256"])

    def test_on_disk_tarball_still_matches_the_pin(self):
        tarball = Path(self.toolchain.record["tarball"])
        self.assertTrue(tarball.exists())
        self.assertEqual(jt.sha256_file(tarball), jt.ZULU8["sha256"])

    def test_binaries_exist(self):
        self.assertTrue(self.toolchain.javac.exists())
        self.assertTrue(self.toolchain.java.exists())

    def test_javac_argv_pins_source_and_target(self):
        argv = self.toolchain.javac_argv(["Solution.java", "Main.java"])
        self.assertEqual(argv[0], str(self.toolchain.javac))
        self.assertIn("-source", argv)
        self.assertEqual(argv[argv.index("-source") + 1], "1.8")
        self.assertEqual(argv[argv.index("-target") + 1], "1.8")
        self.assertEqual(argv[-2:], ["Solution.java", "Main.java"])
        self.assertNotIn("--release", argv)

    def test_java_argv_carries_the_jvm_flags_and_tmpdir(self):
        argv = self.toolchain.java_argv("Main", workdir="/tmp/w")
        self.assertEqual(argv[0], str(self.toolchain.java))
        self.assertIn("-ea", argv)
        self.assertIn("-XX:-UsePerfData", argv)
        self.assertIn("-Djava.io.tmpdir=/tmp/w", argv)
        self.assertEqual(argv[-1], "Main")

    def test_describe_is_the_record_block(self):
        described = self.toolchain.describe()
        self.assertEqual(described["mode"], "jdk8")
        self.assertEqual(described["vendor"], "Azul Zulu")
        self.assertEqual(described["sha256"], jt.ZULU8["sha256"])
        self.assertIn("1.8.0", described["javaVersionOutput"])


if __name__ == "__main__":
    unittest.main()
