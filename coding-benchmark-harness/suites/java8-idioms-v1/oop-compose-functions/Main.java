import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.function.Function;

public class Main {
    private static final Function<String, String> TRIM = String::trim;
    private static final Function<String, String> UPPER = String::toUpperCase;
    private static final Function<String, String> BANG = s -> s + "!";
    private static final Function<String, String> FIRST_TWO =
            s -> s.length() <= 2 ? s : s.substring(0, 2);

    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqStr("AB", Solution.composeAll(Arrays.asList(TRIM, UPPER)).apply(" ab "),
                "javadoc-example");

        // 2-3: null and empty lists compose to identity.
        Check.eqStr(" x ", Solution.composeAll(null).apply(" x "), "null-list-is-identity");
        Check.eqStr(" x ",
                Solution.composeAll(new ArrayList<Function<String, String>>()).apply(" x "),
                "empty-list-is-identity");

        // 4-5: order matters (not shown in the Javadoc).
        Check.eqStr("AB!", Solution.composeAll(Arrays.asList(TRIM, UPPER, BANG)).apply(" ab "),
                "three-in-order");
        Check.eqStr("AB!", Solution.composeAll(Arrays.asList(UPPER, TRIM, BANG)).apply(" ab "),
                "upper-then-trim");

        // 6: the same functions in the opposite order give a different answer.
        Check.eqStr("ab", Solution.composeAll(Arrays.asList(FIRST_TWO, TRIM)).apply("ab cd"),
                "truncate-then-trim");
        Check.eqStr("ab", Solution.composeAll(Arrays.asList(TRIM, FIRST_TWO)).apply(" abcd"),
                "trim-then-truncate");

        // 7: null elements are skipped.
        Check.eqStr("AB", Solution.composeAll(Arrays.asList(null, TRIM, null, UPPER)).apply(" ab "),
                "null-elements-skipped");

        // 8: a list of only nulls is identity.
        Check.eqStr(" y ", Solution.composeAll(Arrays.asList(null, null)).apply(" y "),
                "all-null-is-identity");

        // 9: a single function.
        Check.eqStr("ab", Solution.composeAll(Arrays.asList(TRIM)).apply(" ab "), "single");

        // 10: the composed function is reusable.
        Function<String, String> composed = Solution.composeAll(Arrays.asList(TRIM, BANG));
        Check.eqStr("a!", composed.apply(" a "), "reusable-first-call");
        Check.eqStr("b!", composed.apply(" b "), "reusable-second-call");

        // 11: never returns null.
        Check.eqBool(true, Solution.composeAll(null) != null, "never-null");

        Check.report();
    }
}
