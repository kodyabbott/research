import java.util.ArrayList;
import java.util.Arrays;
import java.util.TreeMap;
import java.util.function.Function;

public class Main {
    private static final Function<String, String> FIRST_LETTER =
            s -> s == null ? null : s.substring(0, 1);

    private static TreeMap<String, Long> map(Object... pairs) {
        TreeMap<String, Long> out = new TreeMap<String, Long>();
        for (int i = 0; i < pairs.length; i += 2) {
            out.put((String) pairs[i], (Long) pairs[i + 1]);
        }
        return out;
    }

    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqMap(map("a", 2L, "b", 1L),
                Solution.countByKey(Arrays.asList("ann", "abe", "bob"), FIRST_LETTER),
                "javadoc-example");

        // 2-3: empty and null inputs.
        Check.eqMap(new TreeMap<String, Long>(),
                Solution.countByKey(new ArrayList<String>(), FIRST_LETTER), "empty-list");
        Check.eqMap(new TreeMap<String, Long>(), Solution.countByKey(null, FIRST_LETTER),
                "null-list");

        // 4: keys that extract to null are dropped (not in the Javadoc examples).
        Check.eqMap(map("z", 1L),
                Solution.countByKey(Arrays.asList("zed", null), FIRST_LETTER), "null-key-ignored");

        // 5: ascending key order, and it must be String order not insertion order.
        Check.eqMapOrdered(map("a", 1L, "m", 1L, "z", 2L),
                Solution.countByKey(Arrays.asList("zoe", "mia", "abe", "zac"), FIRST_LETTER),
                "sorted-by-key");

        // 6: values are Long, not Integer.
        Object first = Solution.countByKey(Arrays.asList("ann"), FIRST_LETTER).get("a");
        Check.eqStr("java.lang.Long", first.getClass().getName(), "counts-are-long");

        // 7: a different extractor entirely.
        Check.eqMap(map("3", 2L, "5", 1L),
                Solution.countByKey(Arrays.asList("abc", "xyz", "hello"),
                        s -> String.valueOf(s.length())), "length-extractor");

        // 8: single record.
        Check.eqMap(map("q", 1L), Solution.countByKey(Arrays.asList("qi"), FIRST_LETTER),
                "single-record");

        // 9: the keyExtractor contract.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.countByKey(Arrays.asList("a"), null), "null-extractor-throws");

        Check.report();
    }
}
