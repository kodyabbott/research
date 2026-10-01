import java.util.LinkedHashMap;

public class Main {
    private static LinkedHashMap<String, String> map(String... pairs) {
        LinkedHashMap<String, String> out = new LinkedHashMap<String, String>();
        for (int i = 0; i < pairs.length; i += 2) {
            out.put(pairs[i], pairs[i + 1]);
        }
        return out;
    }

    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqMap(map("a", "1", "b", "2"), Solution.parse("a=1;b=2"), "javadoc-example");

        // 2-3: null and blank.
        Check.eqMap(new LinkedHashMap<String, String>(), Solution.parse(null), "null-input");
        Check.eqMap(new LinkedHashMap<String, String>(), Solution.parse("   "), "blank-input");

        // 4: empty values are allowed (not shown in the Javadoc).
        Check.eqMap(map("a", ""), Solution.parse("a="), "empty-value");

        // 5: percent decoding.
        Check.eqMap(map("full name", "a;b"), Solution.parse("full%20name=a%3Bb"),
                "percent-decoding");

        // 6: "+" stays a literal plus, unlike form encoding.
        Check.eqMap(map("a", "b+c"), Solution.parse("a=b+c"), "plus-is-literal");

        // 7: only the first "=" splits, so a value may contain "=".
        Check.eqMap(map("expr", "x=y=z"), Solution.parse("expr=x=y=z"), "first-equals-splits");

        // 8: last value wins, first position kept.
        Check.eqMapOrdered(map("a", "3", "b", "2"), Solution.parse("a=1;b=2;a=3"),
                "last-wins-first-position");

        // 9: trailing and doubled separators are skipped.
        Check.eqMap(map("a", "1"), Solution.parse("a=1;;"), "empty-segments-skipped");

        // 10: first-seen order, not sorted order.
        Check.eqMapOrdered(map("z", "1", "a", "2"), Solution.parse("z=1;a=2"), "insertion-order");

        // 11: a multi-byte UTF-8 escape.
        Check.eqMap(map("k", "é"), Solution.parse("k=%C3%A9"), "utf8-escape");

        // 12-14: rejections.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parse("novalue"), "missing-equals-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parse("=1"), "empty-key-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parse("a=%ZZ"), "bad-escape-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parse("a=%A"), "truncated-escape-throws");

        Check.report();
    }
}
