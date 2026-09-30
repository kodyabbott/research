# Java 8 coding benchmarks: design

Status: design, September 30, 2026, by Claude Fable 5.1. Extends [DESIGN.md](DESIGN.md) (the Python harness); implementation is delegated to the same Opus agent after the Python deliverable lands, so the shared modules (`record.py`, `backends.py`, `sandbox.py`, `run.py`, `summarize.py`) are extended rather than forked. Everything in DESIGN.md's Constraints and Revisions sections applies here too, including: the implementing agent never contacts a model server.

## Why Java 8

Kody's day job is moving Python OOP to Java OOP on a Java 8 codebase. The question is not "can a model write Java" but "can it write Java that compiles and runs on JDK 8 without leaking newer syntax or APIs" (`var`, records, `List.of`, text blocks, switch expressions, `String.isBlank`, `Optional.isEmpty`, `Stream.toList`). Compiling with a real JDK 8 makes that the pass/fail line. Nothing published breaks coding scores out by Java (SWE-bench Multilingual has 43 Java tasks but no per-language rows for local models), so this is the measurement we will own.

## Toolchain

- **Primary: Azul Zulu JDK 8 for macOS aarch64**, tarball, no installer or sudo. The Azul metadata API lists `zulu8.96.0.205-ca-jdk8.0.504-macosx_aarch64.tar.gz` at `https://cdn.azul.com/zulu/bin/` as the latest GA (checked Sep 30, 2026). `prepare.py --jdk` downloads it to `~/Documents/Codex/model-cache/coding-benchmark/jdk/`, computes SHA-256, and pins it in `toolchain.json` (URL, filename, size, sha256, `java -version` output). Later runs refuse to proceed if the on-disk JDK hash differs. Eclipse Temurin has no aarch64 JDK 8 build (x64 only), which is why Zulu.
- **Fallback, only if the Zulu download fails:** Temurin 21 aarch64 (`jdk-21.0.12.1+1`, sha256 `3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998`) with `javac --release 8`, which enforces Java 8 language level and public API via `ct.sym` but executes on a 21 JVM. The record must say which toolchain ran (`runtime.javaToolchain: {vendor, version, javaHome, sha256, mode: "jdk8" | "release8-on-21"}`). Do not mix toolchains inside one run.
- JVM flags for every sandboxed invocation: `-Xmx512m -Xss2m -XX:+UseSerialGC -XX:-UsePerfData -Djava.io.tmpdir=$WORKDIR -Djava.awt.headless=true -Dfile.encoding=UTF-8 -ea` (assertions on: HumanEval-X tests use `assert`). `javac` flags: `-source 1.8 -target 1.8 -encoding UTF-8 -Xlint:none -d $WORKDIR/classes` on JDK 8 (`--release 8` on the fallback), with `-J-Xmx512m -J-XX:-UsePerfData`.
- `mvn`/`gradle`/JUnit are not used; tests are plain `Main` classes with a tiny `Check` helper (below), so the sandbox has one dependency: the JDK.

## Sandbox additions

Same `sandbox-exec` deny-default approach as DESIGN.md. New allow rules: `process-exec` and `file-read*` for the JDK directory; `file-write*` only under WORKDIR (the JVM writes nothing else once `-XX:-UsePerfData` and `java.io.tmpdir` are set). Network stays denied. Self-tests extend the Python set: (1) a Java program that opens a socket to 127.0.0.1:11436 must fail, (2) a Java program writing to `$HOME/x` must fail, (3) `while(true){}` is killed by the wall timeout, (4) a hello-world compiles and runs, (5) a class using `List.of` fails to compile on the JDK 8 toolchain with the expected diagnostic. Document every allow rule in `notes.md`.

Timeouts: compile wall 60 s, run wall 60 s, `RLIMIT_CPU` 120 s per phase; JVM startup on this Mac is well under a second, so these are generous.

## Suites

### `humaneval-x-java` (standardized, 164 tasks)

Source: Hugging Face dataset `zai-org/humaneval-x` (formerly `THUDM/humaneval-x`), file `data/java/data/humaneval.jsonl` (475 KB), pinned at revision `62c78627f3072a1454fa0cb0184737cafe5e4198`; record URL, revision, and SHA-256 in `datasets.json`. Fields expected: `task_id`, `prompt` (imports + `class Solution` with Javadoc and method signature, open brace), `declaration`, `canonical_solution` (method body), `test` (a `Main` class with `assert`s), `example_test`. Verify field names against the file and note any adaptation.

`prepare.py --suite humaneval-x-java`: for each task, compile `prompt + canonical_solution + "}"` together with `test` on the JDK 8 toolchain and run `Main`. Tasks whose canonical solution fails to compile or run on Java 8 go to `_skipped.json` with the compiler diagnostic and are excluded from scoring; report the count. (This also tells us how Java-8-clean the dataset itself is.)

Prompting: one user message:
```
Complete the following Java class. Target Java 8: do not use var, records, text blocks, switch expressions, List.of/Map.of/Set.of, or any API newer than Java 8. Return the complete Solution class (imports, class, and the finished method) in a single ```java code block and nothing else.

{prompt}
```
Grading: the extracted class replaces `Solution`; the hidden `Main` is the dataset `test`; pass = compiles and `Main` exits 0 with no `AssertionError`. Base/plus distinction does not exist here; `basePassed == plusPassed == passed`.

### `java8-idioms-v1` (authored, 24 tasks, 8 categories x 3)

Purpose: enterprise-flavored Java 8 idioms with hidden tests, in the same spirit as the repository's `practical-json-v1`. Each task ships as `suites/java8-idioms-v1/<id>/` with `prompt.java` (the skeleton the model sees), `Main.java` (hidden tests), `Solution.java` (canonical, must pass on JDK 8), and `task.json` (title, category, java8Features, testCount). `prepare.py --suite java8-idioms` compiles and runs every canonical solution against its tests on JDK 8 and refuses to ship a suite with a failing canonical. Suite digest = SHA-256 over all four files per task in id order.

Skeleton convention: `public class Solution` with `public static` methods, Javadoc stating the contract, edge cases, and exceptions; bodies contain `throw new UnsupportedOperationException("TODO");`. Prompts state Java 8 and the "single ```java block, complete class" rule exactly as above. Tests use the `Check` helper (below), never JUnit, and print a one-line JSON summary as the last stdout line: `{"passed": n, "total": m, "failures": [{"name": ..., "expected": ..., "actual": ...}]}`. Minimum 6 checks per task including edge cases; expected values are computed by hand or by the canonical solution and reviewed, not copied from a model.

Tasks (id: title; Java 8 features under test; what the hidden tests probe):

streams-collections
1. `streams-groupcount`: count records per key with `Collectors.groupingBy` + `counting`, return a `TreeMap<String, Long>`; empty input, null-safe key extractor contract.
2. `streams-topn`: top-N by score desc then name asc using `Comparator.comparing(...).reversed().thenComparing(...)`, stable for ties; N larger than list; N = 0.
3. `streams-flatten`: flatten `List<List<String>>`, trim, drop blanks, distinct, sorted case-insensitively; nested empties; duplicate case variants.

optional-null-safety
4. `optional-chain`: `Optional`-based navigation over nullable `Patient -> Provider -> Address -> zip` returning `"UNKNOWN"` default; every null position.
5. `optional-first-match`: `findFirst` with predicate returning `Optional<Record>`; empty; no match; first-of-several.
6. `optional-merge`: combine two `Optional<Integer>` with a `BinaryOperator`; both present, one present, none.

datetime
7. `time-business-days`: business days between two `LocalDate`s exclusive/inclusive contract, skipping weekends and a `Set<LocalDate>` of holidays; reversed order; same day; holiday on weekend.
8. `time-parse-mixed`: normalize `yyyy-MM-dd`, `MM/dd/yyyy`, `dd-MMM-yyyy` (English) to ISO with `DateTimeFormatter`; invalid input throws `IllegalArgumentException`.
9. `time-window-bucket`: floor `Instant`s to 15-minute buckets in a `ZoneId`, return counts per bucket in order; DST transition day in `America/Denver`.

money
10. `money-allocate`: split a `BigDecimal` amount across N parties in given ratios, largest-remainder distribution of leftover cents, sums exactly; ratios with zeros.
11. `money-invoice-total`: sum `quantity * unitPrice` lines with `RoundingMode.HALF_EVEN` at scale 2 per line then total; tax rate applied once; banker's rounding cases (`x.xx5`).
12. `money-parse-cents`: parse `"$1,234.56"`, `"(12.30)"` negatives, `"-0.01"`, whitespace to long cents; reject malformed.

text-parsing
13. `text-csv-line`: RFC 4180 single-line parser with quoted fields, doubled quotes, commas inside quotes; trailing empty field; unterminated quote throws.
14. `text-kv-tokens`: parse `k=v;k2=v2` with percent-decoding and duplicate-key last-wins into `LinkedHashMap`; empty values; malformed pair throws.
15. `text-word-freq`: top-k word frequency, case-insensitive, punctuation stripped, ties by word asc; k > distinct words.

oop-interfaces
16. `oop-value-object`: implement `equals`/`hashCode`/`compareTo` for an `Mrn` (medical record number) value type; `HashSet` dedupe, `TreeSet` order, `equals` symmetry with `null` and other types.
17. `oop-generic-bounded`: `<T extends Comparable<? super T>> Optional<T> maxOf(Collection<T>)`; empty; mixed subclass comparables.
18. `oop-compose-functions`: compose `List<Function<String,String>>` left-to-right with `Function.identity()` seed; empty list; order sensitivity.

exceptions-validation
19. `exc-collect-errors`: validate a `Map<String,String>` form against rules, collect all messages (not fail-fast), throw one checked `ValidationException` carrying the list; zero errors returns normalized map.
20. `exc-retry`: retry a `Callable<T>` up to N attempts only for exceptions matching a `Predicate<Exception>`, rethrow the last failure wrapped with attempt count; success on attempt k; non-retryable on attempt 1.
21. `exc-try-with-resources`: count non-blank lines from a `Reader` using try-with-resources; verify `close()` called via a test `Reader` subclass; IOException propagates.

algorithms
22. `algo-lru-cache`: LRU with `LinkedHashMap(accessOrder=true)` + `removeEldestEntry`; get promotes; capacity 1; capacity 0 rejected.
23. `algo-toposort`: Kahn's algorithm with lexical tie-break on a `Map<String, List<String>>` graph; cycle throws `IllegalArgumentException` naming a node in the cycle; isolated nodes.
24. `algo-merge-intervals`: merge `List<int[]>` intervals given unsorted input, touching intervals merge; single; empty.

Hidden tests must not be guessable from the prompt's examples: at least half of each task's checks use inputs not shown in the Javadoc.

### `Check` helper (shipped with every suite, not sent to the model)

```java
public final class Check {
    private static int passed = 0, total = 0;
    private static final java.util.List<String> failures = new java.util.ArrayList<>();
    public static void eq(Object expected, Object actual, String name) { total++; if (java.util.Objects.deepEquals(expected, actual)) passed++; else failures.add(json(name, expected, actual)); }
    public static void throwsType(Class<? extends Throwable> type, Runnable r, String name) { ... }
    public static void report() { System.out.println("{\"passed\":" + passed + ",\"total\":" + total + ",\"failures\":[" + String.join(",", failures) + "]}"); }
    ...
}
```
`Main.main` calls `Check.report()` last. `deepEquals` handles arrays; BigDecimal comparisons use `compareTo == 0` via a dedicated `Check.eqDecimal`. The harness parses the last stdout line as JSON; anything else (exception trace, no output) is classified from stderr/exit code.

## Extraction and failure classes

Extraction (in `extract.py`, new `extract_java`): choose the first ```java (or unlabeled) fenced block containing `class Solution`; else the last fenced block; else raw content if it contains `class Solution`. Strip any `package ...;` line (record `packageStripped: true`). If no `class Solution` after that, `failureClass: wrong-class`. Cap 256 KiB. Never modify anything else.

Failure classes (superset of the Python set): `none | no-code | wrong-class | compile-error | java9plus-usage | runtime-exception | assertion-failed | wrong-answer | timeout | sandbox-error | truncated`. `java9plus-usage` is a sub-classification of `compile-error` applied when the javac diagnostics match a curated pattern list (e.g. `cannot find symbol ... method of(` on `List`/`Map`/`Set`, `'var' is not allowed`, `records are not supported in -source 8`, `text blocks are not supported`, `switch expressions`, `isBlank()`, `toList()` on `Stream`, `Optional.isEmpty`, `strip()`, `repeat(`). Keep the raw diagnostics (capped 8 KiB) in the record so the classification can be audited. Report both the total compile-error rate and the java9plus share; that share is the headline "Java 8 discipline" number.

## Record and summary

Per task adds: `language: "java"`, `compile: {ok, seconds, diagnostics}`, `run: {exitCode, seconds, stdoutTail, stderrTail}`, `checks: {passed, total, failures}`. Run-level adds `runtime.javaToolchain`. Summarizer adds columns: compile-error, java9plus, assertion-failed, and for `java8-idioms` a per-category breakdown table (8 rows) like the Sep 27 report.

## CLI

```
python3 coding-benchmark-harness/prepare.py --jdk
python3 coding-benchmark-harness/prepare.py --suite humaneval-x-java --suite java8-idioms
python3 coding-benchmark-harness/run.py --backend ollama --endpoint http://127.0.0.1:11436 \
    --model qwen3.8:27b-q8_0 --suite java8-idioms --think false --label qwen3.8-27b-q8_0-java8-off
python3 coding-benchmark-harness/run.py --backend replay --suite java8-idioms --replay-file tests/fixtures/java8-replay.json ...
```

## Tests

- `test_java_toolchain.py`: pinned hash check, `java -version` parse, refuses mismatched JDK.
- `test_sandbox_java.py`: the five Java self-tests above (skipped with a message if no JDK is prepared).
- `test_extract_java.py`: fences, package stripping, wrong-class, multiple classes.
- `test_java_grader.py`: `Check` JSON parsing, classification including `java9plus-usage` from real captured diagnostics (fixtures), `-ea` assertion failure detection.
- `test_java8_idioms_suite.py`: every canonical solution compiles and passes its own tests on the prepared JDK (this is the suite's own acceptance test); digest stability.

## Acceptance

1. `prepare.py --jdk` installs Zulu 8 (or documents the fallback), and all Java sandbox self-tests pass.
2. `prepare.py --suite humaneval-x-java` reports task count and skipped-on-Java-8 count with diagnostics.
3. All 24 `java8-idioms-v1` canonical solutions pass their hidden tests on JDK 8; each task has at least 6 checks; the authored-suite test is green.
4. Replay-backend end-to-end run on both Java suites writes valid records and the summarizer renders them, including the java9plus column and per-category table.
5. Full unittest discovery green. `notes.md` documents allow rules, dataset field adaptations, skipped tasks, and deviations. README gains a Java section and keeps the "not yet run against a live model" status; live runs are done by the designing session.

## Open questions for Kody (defaults taken)

- Should prompts state the Java 8 constraint (measures instruction-following under a known constraint) or omit it (measures default habits)? Default: state it, because that is how the constraint reaches a model in real use. A `--no-java8-hint` flag flips the prompt so both can be measured later.
- HumanEval-X Java is a translation of Python problems and says little about enterprise Java; it is here as the standardized anchor. The authored suite carries the Java 8 signal.
