import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class Main {
    private static Map<String, String> form(String... pairs) {
        Map<String, String> out = new LinkedHashMap<String, String>();
        for (int i = 0; i < pairs.length; i += 2) {
            out.put(pairs[i], pairs[i + 1]);
        }
        return out;
    }

    private static TreeMap<String, String> expect(String... pairs) {
        TreeMap<String, String> out = new TreeMap<String, String>();
        for (int i = 0; i < pairs.length; i += 2) {
            out.put(pairs[i], pairs[i + 1]);
        }
        return out;
    }

    private static List<String> errorsOf(Map<String, String> form, List<String> required) {
        try {
            Solution.validate(form, required);
            return null;
        } catch (Solution.ValidationException expected) {
            return expected.getErrors();
        }
    }

    public static void main(String[] args) throws Exception {
        // 1: the Javadoc example.
        Check.eqMap(expect("name", "ann"),
                Solution.validate(form("name", " ann "), Arrays.asList("name")),
                "javadoc-example");

        // 2-3: no required fields, and a null form with nothing required.
        Check.eqMap(expect("a", "b"), Solution.validate(form("a", " b "), null), "nothing-required");
        Check.eqMap(new TreeMap<String, String>(), Solution.validate(null, null), "null-form");

        // 4: all errors are collected, not just the first (the point of the task).
        Check.eqList(Arrays.asList("age is required", "email is blank", "name is blank"),
                errorsOf(form("name", "  ", "email", null), Arrays.asList("name", "email", "age")),
                "collects-all-errors");

        // 5: messages are sorted by field name, not by rule or input order.
        Check.eqList(Arrays.asList("aaa is required", "zzz is required"),
                errorsOf(form(), Arrays.asList("zzz", "aaa")), "sorted-by-field");

        // 6: absent and blank produce different messages.
        Check.eqList(Arrays.asList("gone is required"),
                errorsOf(form("here", "x"), Arrays.asList("gone")), "absent-message");
        Check.eqList(Arrays.asList("here is blank"),
                errorsOf(form("here", "\t "), Arrays.asList("here")), "blank-message");

        // 7: a present null value is "blank", not "required".
        Check.eqList(Arrays.asList("k is blank"),
                errorsOf(form("k", null), Arrays.asList("k")), "null-value-is-blank");

        // 8: the exception message reports the count.
        try {
            Solution.validate(form(), Arrays.asList("a", "b"));
            Check.eqBool(true, false, "should-have-thrown");
        } catch (Solution.ValidationException thrown) {
            Check.eqStr("validation failed with 2 error(s)", thrown.getMessage(),
                    "exception-message");
        }

        // 9: it is a checked exception, so it must be declared.
        Check.eqBool(true, Exception.class.isAssignableFrom(Solution.ValidationException.class)
                && !RuntimeException.class.isAssignableFrom(Solution.ValidationException.class),
                "is-a-checked-exception");

        // 10: unrequired fields are kept and trimmed too.
        Check.eqMap(expect("extra", "e", "name", "ann"),
                Solution.validate(form("name", " ann ", "extra", " e "), Arrays.asList("name")),
                "extra-fields-trimmed");

        // 11: output is key-ordered, not insertion-ordered.
        Check.eqMapOrdered(expect("a", "1", "m", "2", "z", "3"),
                Solution.validate(form("z", "3", "a", "1", "m", "2"), null), "output-key-order");

        Check.report();
    }
}
