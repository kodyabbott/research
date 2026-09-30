"""Capture JDK 8's own diagnostics for post-Java-8 syntax and APIs.

    python3 coding-benchmark-harness/tests/fixtures/java9plus/capture.py

Writes `<name>.java` and `<name>.txt` (the raw `javac` output) per case, plus `index.json`. The
`java9plus-usage` pattern list in `harness/java_grader.py` is built from these files, not guessed:
JDK 8 javac has no idea what `var` or a record is, so it emits generic parse errors rather than
anything mentioning Java versions. Compiled on the pinned Zulu 8 inside the sandbox.

`control-typo` and `control-missing-import` are deliberately *not* Java 9+ problems; they exist so
the classifier can be tested for false positives.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from harness import java_sandbox  # noqa: E402

CASES = {
    "var-local": ("Java 10 local-variable type inference", """public class Main {
    public static void main(String[] args) {
        var total = 0;
        System.out.println(total);
    }
}
"""),
    "record-declaration": ("Java 16 records", """public class Main {
    record Point(int x, int y) {}
    public static void main(String[] args) {
        System.out.println(new Point(1, 2));
    }
}
"""),
    "text-block": ("Java 15 text blocks", '''public class Main {
    public static void main(String[] args) {
        String s = """
            hello
            """;
        System.out.println(s);
    }
}
'''),
    "switch-expression": ("Java 14 switch expressions", """public class Main {
    public static void main(String[] args) {
        int day = 3;
        String name = switch (day) {
            case 1 -> "Mon";
            default -> "other";
        };
        System.out.println(name);
    }
}
"""),
    "list-of": ("Java 9 List.of", """import java.util.*;
public class Main {
    public static void main(String[] args) {
        List<String> xs = List.of("a", "b");
        System.out.println(xs);
    }
}
"""),
    "map-of": ("Java 9 Map.of", """import java.util.*;
public class Main {
    public static void main(String[] args) {
        Map<String, Integer> m = Map.of("a", 1);
        System.out.println(m);
    }
}
"""),
    "set-of": ("Java 9 Set.of", """import java.util.*;
public class Main {
    public static void main(String[] args) {
        Set<String> s = Set.of("a", "b");
        System.out.println(s);
    }
}
"""),
    "string-isblank": ("Java 11 String.isBlank", """public class Main {
    public static void main(String[] args) {
        System.out.println("  ".isBlank());
    }
}
"""),
    "string-strip": ("Java 11 String.strip", """public class Main {
    public static void main(String[] args) {
        System.out.println(" x ".strip());
    }
}
"""),
    "string-repeat": ("Java 11 String.repeat", """public class Main {
    public static void main(String[] args) {
        System.out.println("ab".repeat(3));
    }
}
"""),
    "string-lines": ("Java 11 String.lines", """import java.util.stream.*;
public class Main {
    public static void main(String[] args) {
        System.out.println("a\\nb".lines().collect(Collectors.toList()));
    }
}
"""),
    "stream-tolist": ("Java 16 Stream.toList", """import java.util.*;
import java.util.stream.*;
public class Main {
    public static void main(String[] args) {
        List<String> xs = Stream.of("a", "b").toList();
        System.out.println(xs);
    }
}
"""),
    "optional-isempty": ("Java 11 Optional.isEmpty", """import java.util.*;
public class Main {
    public static void main(String[] args) {
        System.out.println(Optional.empty().isEmpty());
    }
}
"""),
    "optional-orelsethrow": ("Java 10 Optional.orElseThrow() with no argument", """import java.util.*;
public class Main {
    public static void main(String[] args) {
        System.out.println(Optional.of(1).orElseThrow());
    }
}
"""),
    "collectors-teeing": ("Java 12 Collectors.teeing", """import java.util.*;
import java.util.stream.*;
public class Main {
    public static void main(String[] args) {
        Object r = Stream.of(1, 2).collect(Collectors.teeing(
                Collectors.counting(), Collectors.counting(), (a, b) -> a));
        System.out.println(r);
    }
}
"""),
    "private-interface-method": ("Java 9 private interface methods", """public class Main {
    interface Greeter {
        private String hidden() { return "hi"; }
        default String greet() { return hidden(); }
    }
    public static void main(String[] args) {
        System.out.println(((Greeter) new Greeter() {}).greet());
    }
}
"""),
    "twr-effectively-final": ("Java 9 try-with-resources on an existing variable",
                              """import java.io.*;
public class Main {
    public static void main(String[] args) throws Exception {
        Reader r = new StringReader("x");
        try (r) {
            System.out.println(r.read());
        }
    }
}
"""),
    "diamond-anonymous": ("Java 9 diamond with anonymous classes", """import java.util.*;
public class Main {
    public static void main(String[] args) {
        Comparator<String> c = new Comparator<>() {
            public int compare(String a, String b) { return a.compareTo(b); }
        };
        System.out.println(c.compare("a", "b"));
    }
}
"""),
    "switch-arrow-label": ("Java 14 arrow labels in a statement switch", """import java.util.*;
public class Main {
    public static void main(String[] args) {
        List<Integer> out = new ArrayList<>();
        String k = "o";
        switch (k) {
            case "o" -> out.add(4);
            case "p" -> out.add(2);
        }
        System.out.println(out);
    }
}
"""),
    "instanceof-pattern": ("Java 16 pattern matching for instanceof", """public class Main {
    public static void main(String[] args) {
        Object o = "text";
        if (o instanceof String s && s.length() > 2) {
            System.out.println(s);
        }
    }
}
"""),
    "static-in-inner-class": ("Java 16 static members in inner classes", """public class Main {
    class Helper {
        public static boolean isPrime(int n) { return n == 2; }
    }
    public static void main(String[] args) {
        System.out.println("x");
    }
}
"""),
    "string-escape-s": ("Java 15 `\\s` escape in a string literal", """public class Main {
    public static void main(String[] args) {
        String[] parts = "a b".split("[.?!]\\s*");
        System.out.println(parts.length);
    }
}
"""),
    "string-strip-on-variable": ("Java 11 String.strip called on a variable, not a literal",
                                 """public class Main {
    public static void main(String[] args) {
        String date = "  2026-01-01  ";
        System.out.println(date.strip());
    }
}
"""),
    "optional-isempty-on-variable": ("Java 11 Optional.isEmpty on a variable",
                                     """import java.util.*;
public class Main {
    public static void main(String[] args) {
        Optional<String> maybe = Optional.of("x");
        System.out.println(maybe.isEmpty());
    }
}
"""),
    # Controls: ordinary Java 8 mistakes that must NOT be classified as java9plus-usage.
    "control-typo": ("CONTROL: a plain typo in a method name (not a Java 9+ feature)",
                     """import java.util.*;
public class Main {
    public static void main(String[] args) {
        List<String> xs = new ArrayList<>();
        xs.addd("a");
        System.out.println(xs);
    }
}
"""),
    "control-missing-import": ("CONTROL: a missing import (not a Java 9+ feature)",
                               """public class Main {
    public static void main(String[] args) {
        List<String> xs = new ArrayList<String>();
        System.out.println(xs);
    }
}
"""),
    "control-type-mismatch": ("CONTROL: an ordinary type error (not a Java 9+ feature)",
                              """public class Main {
    public static void main(String[] args) {
        int x = "not an int";
        System.out.println(x);
    }
}
"""),
}


def main() -> int:
    if not java_sandbox.available():
        print("no prepared JDK; run: python3 coding-benchmark-harness/prepare.py --jdk",
              file=sys.stderr)
        return 2
    box = java_sandbox.load()
    index = {
        "capturedAt": __import__("datetime").datetime.now().astimezone().isoformat(
            timespec="seconds"),
        "toolchain": box.toolchain.describe(),
        "cases": {},
    }
    for name, (description, source) in sorted(CASES.items()):
        compiled, _ran = box.compile_and_run({"Main.java": source})
        (HERE / f"{name}.java").write_text(source, encoding="utf-8")
        (HERE / f"{name}.txt").write_text(compiled.diagnostics, encoding="utf-8")
        index["cases"][name] = {
            "description": description,
            "isJava9Plus": not name.startswith("control-"),
            "compiled": compiled.ok,
            "errorCount": compiled.error_count,
            "filesWithErrors": compiled.files_with_errors,
            "firstErrorLine": next(
                (line for line in compiled.diagnostics.splitlines() if ": error:" in line), None),
        }
        flag = "compiled!" if compiled.ok else f"{compiled.error_count} error(s)"
        print(f"  {name:28s} {flag}")
    (HERE / "index.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    unexpected = [name for name, info in index["cases"].items()
                  if info["isJava9Plus"] and info["compiled"]]
    if unexpected:
        print(f"WARNING: these Java 9+ cases compiled on JDK 8: {unexpected}", file=sys.stderr)
    print(f"wrote {len(index['cases'])} cases to {HERE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
