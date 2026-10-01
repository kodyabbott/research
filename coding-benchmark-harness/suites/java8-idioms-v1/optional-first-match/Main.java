import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.function.Predicate;

public class Main {
    private static final Predicate<Integer> EVEN = n -> n % 2 == 0;

    public static void main(String[] args) {
        List<Integer> oneToFour = Arrays.asList(1, 2, 3, 4);

        // 1: the Javadoc example.
        Check.eq(Optional.of(2), Solution.firstMatch(oneToFour, EVEN), "javadoc-example");

        // 2: first of several matches, not the last.
        Check.eq(Optional.of(2), Solution.firstMatch(Arrays.asList(1, 2, 4, 6), EVEN),
                "first-of-several");

        // 3: no match.
        Check.eq(Optional.empty(), Solution.firstMatch(Arrays.asList(1, 3, 5), EVEN), "no-match");

        // 4-5: empty and null lists.
        Check.eq(Optional.empty(), Solution.firstMatch(new ArrayList<Integer>(), EVEN), "empty");
        Check.eq(Optional.empty(), Solution.firstMatch(null, EVEN), "null-list");

        // 6: nulls are skipped, not passed to the predicate (a predicate that would NPE proves it).
        Check.eq(Optional.of(4), Solution.firstMatch(Arrays.asList(null, 3, null, 4), EVEN),
                "nulls-skipped");

        // 7: an always-true predicate returns the first non-null element.
        Check.eq(Optional.of(7), Solution.firstMatch(Arrays.asList(null, 7, 8), n -> true),
                "always-true-first-non-null");

        // 8: an always-false predicate returns empty.
        Check.eq(Optional.empty(), Solution.firstMatch(oneToFour, n -> false), "always-false");

        // 9: negative values match normally.
        Check.eq(Optional.of(-2), Solution.firstMatch(Arrays.asList(-3, -2, -1), EVEN),
                "negative-even");

        // 10: the predicate contract.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.firstMatch(oneToFour, null), "null-predicate-throws");

        Check.report();
    }
}
