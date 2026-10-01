import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Tiny assertion helper for the java8-idioms-v1 hidden tests. Never sent to the model.
 *
 * No JUnit: the sandbox has exactly one dependency, the JDK. Every Main.main ends with
 * Check.report(), which prints a single line of JSON as the last line of stdout:
 *
 *   {"passed":6,"total":7,"failures":[{"name":"...","expected":"...","actual":"..."}]}
 *
 * Typed helpers exist so that a boxing mismatch (Integer vs Long) cannot cause a false failure:
 * eqInt/eqLong/eqDecimal take primitives or compare by value, and the expected literal in each
 * test must match the declared return type exactly (DESIGN-JAVA.md revisions item 4).
 *
 * Java 8 only -- this file is compiled by the same javac as the tasks.
 */
public final class Check {
    private static int passed = 0;
    private static int total = 0;
    private static final List<String> failures = new ArrayList<String>();

    private Check() {
    }

    /** Generic deep equality. Handles arrays, which Objects.equals does not. */
    public static void eq(Object expected, Object actual, String name) {
        record(Objects.deepEquals(expected, actual), name, expected, actual);
    }

    public static void eqInt(int expected, int actual, String name) {
        record(expected == actual, name, Integer.valueOf(expected), Integer.valueOf(actual));
    }

    public static void eqLong(long expected, long actual, String name) {
        record(expected == actual, name, Long.valueOf(expected), Long.valueOf(actual));
    }

    public static void eqBool(boolean expected, boolean actual, String name) {
        record(expected == actual, name, Boolean.valueOf(expected), Boolean.valueOf(actual));
    }

    public static void eqStr(String expected, String actual, String name) {
        record(expected == null ? actual == null : expected.equals(actual), name, expected, actual);
    }

    /** BigDecimal by value, so 1.50 and 1.5 compare equal; scale is checked separately. */
    public static void eqDecimal(String expected, BigDecimal actual, String name) {
        boolean ok = actual != null && new BigDecimal(expected).compareTo(actual) == 0;
        record(ok, name, expected, actual);
    }

    /** BigDecimal by value *and* scale, for the tasks whose contract fixes the scale. */
    public static void eqDecimalScaled(String expected, BigDecimal actual, String name) {
        BigDecimal want = new BigDecimal(expected);
        boolean ok = actual != null && want.compareTo(actual) == 0
                && want.scale() == actual.scale();
        record(ok, name, expected + " (scale " + want.scale() + ")",
                actual == null ? null : actual.toPlainString() + " (scale " + actual.scale() + ")");
    }

    public static void eqList(List<?> expected, List<?> actual, String name) {
        record(Objects.equals(expected, actual), name, expected, actual);
    }

    public static void eqMap(Map<?, ?> expected, Map<?, ?> actual, String name) {
        record(Objects.equals(expected, actual), name, expected, actual);
    }

    /** Map equality plus key iteration order, for LinkedHashMap/TreeMap contracts. */
    public static void eqMapOrdered(Map<?, ?> expected, Map<?, ?> actual, String name) {
        boolean ok = Objects.equals(expected, actual)
                && actual != null
                && new ArrayList<Object>(expected.keySet())
                        .equals(new ArrayList<Object>(actual.keySet()));
        record(ok, name, keysOf(expected), actual == null ? null : keysOf(actual));
    }

    private static String keysOf(Map<?, ?> map) {
        return map == null ? "null" : new ArrayList<Object>(map.keySet()).toString();
    }

    /** Asserts that `body` throws `type` (or a subclass). Any other outcome fails. */
    public static void throwsType(Class<? extends Throwable> type, ThrowingRunnable body,
                                  String name) {
        String actual;
        try {
            body.run();
            actual = "no exception";
        } catch (Throwable thrown) {
            if (type.isInstance(thrown)) {
                record(true, name, type.getName(), thrown.getClass().getName());
                return;
            }
            actual = thrown.getClass().getName() + ": " + thrown.getMessage();
        }
        record(false, name, type.getName(), actual);
    }

    /**
     * Asserts that `body` throws `type` and that its message mentions at least one of `anyOf`.
     * Used where a contract fixes the exception type but not the wording.
     */
    public static void throwsTypeMentioning(Class<? extends Throwable> type, String[] anyOf,
                                            ThrowingRunnable body, String name) {
        try {
            body.run();
            record(false, name, type.getName() + " mentioning one of " + Arrays.toString(anyOf),
                    "no exception");
            return;
        } catch (Throwable thrown) {
            if (!type.isInstance(thrown)) {
                record(false, name, type.getName(), thrown.getClass().getName());
                return;
            }
            String message = thrown.getMessage() == null ? "" : thrown.getMessage();
            for (String needle : anyOf) {
                if (message.contains(needle)) {
                    record(true, name, "message mentioning " + needle, message);
                    return;
                }
            }
            record(false, name, type.getName() + " mentioning one of " + Arrays.toString(anyOf),
                    type.getName() + ": " + message);
        }
    }

    /** Runnable that may throw a checked exception, so tests need no wrapper lambdas. */
    public interface ThrowingRunnable {
        void run() throws Exception;
    }

    private static void record(boolean ok, String name, Object expected, Object actual) {
        total++;
        if (ok) {
            passed++;
        } else {
            failures.add("{\"name\":" + json(name) + ",\"expected\":" + json(str(expected))
                    + ",\"actual\":" + json(str(actual)) + "}");
        }
    }

    private static String str(Object value) {
        if (value == null) {
            return "null";
        }
        if (value instanceof Object[]) {
            return Arrays.deepToString((Object[]) value);
        }
        if (value instanceof int[]) {
            return Arrays.toString((int[]) value);
        }
        if (value instanceof long[]) {
            return Arrays.toString((long[]) value);
        }
        if (value instanceof char[]) {
            return Arrays.toString((char[]) value);
        }
        return String.valueOf(value);
    }

    /** JSON string escaping. A quote or backslash in a value must not break the summary line. */
    private static String json(String text) {
        if (text == null) {
            return "null";
        }
        StringBuilder out = new StringBuilder(text.length() + 2);
        out.append('"');
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            switch (c) {
                case '"':
                    out.append("\\\"");
                    break;
                case '\\':
                    out.append("\\\\");
                    break;
                case '\n':
                    out.append("\\n");
                    break;
                case '\r':
                    out.append("\\r");
                    break;
                case '\t':
                    out.append("\\t");
                    break;
                case '\b':
                    out.append("\\b");
                    break;
                case '\f':
                    out.append("\\f");
                    break;
                default:
                    if (c < 0x20 || c == 0x7f) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
            }
        }
        out.append('"');
        return out.toString();
    }

    /** Must be the last thing Main.main does. Prints the one-line JSON summary. */
    public static void report() {
        StringBuilder out = new StringBuilder();
        out.append("{\"passed\":").append(passed).append(",\"total\":").append(total)
                .append(",\"failures\":[");
        for (int i = 0; i < failures.size(); i++) {
            if (i > 0) {
                out.append(',');
            }
            out.append(failures.get(i));
        }
        out.append("]}");
        System.out.println(out.toString());
    }
}
