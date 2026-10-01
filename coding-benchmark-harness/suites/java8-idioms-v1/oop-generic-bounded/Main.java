import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Optional;

public class Main {
    /** A Comparable whose ordering is not its natural field order, to prove compareTo is used. */
    static final class Reversed implements Comparable<Reversed> {
        final int value;

        Reversed(int value) {
            this.value = value;
        }

        public int compareTo(Reversed other) {
            return Integer.compare(other.value, this.value);
        }

        public boolean equals(Object o) {
            return o instanceof Reversed && ((Reversed) o).value == value;
        }

        public int hashCode() {
            return value;
        }

        public String toString() {
            return "Reversed(" + value + ")";
        }
    }

    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eq(Optional.of(9), Solution.maxOf(Arrays.asList(3, 9, 7)), "javadoc-example");

        // 2-3: empty and null.
        Check.eq(Optional.empty(), Solution.maxOf(new ArrayList<Integer>()), "empty");
        Check.eq(Optional.empty(), Solution.maxOf(null), "null-collection");

        // 4: all elements null (not shown in the Javadoc).
        Check.eq(Optional.empty(), Solution.maxOf(Arrays.<Integer>asList(null, null)), "all-null");

        // 5: nulls are ignored around a real maximum.
        Check.eq(Optional.of(5), Solution.maxOf(Arrays.<Integer>asList(null, 5, null, 1)), "nulls-ignored");

        // 6: a single element.
        Check.eq(Optional.of(42), Solution.maxOf(Arrays.asList(42)), "single-element");

        // 7: Strings, using natural String ordering.
        Check.eq(Optional.of("pear"), Solution.maxOf(Arrays.asList("apple", "pear", "fig")),
                "strings");

        // 8: BigDecimal, where compareTo differs from equals.
        Check.eq(Optional.of(new BigDecimal("2.50")),
                Solution.maxOf(Arrays.asList(new BigDecimal("1.00"), new BigDecimal("2.50"))),
                "bigdecimal");

        // 9: a type whose compareTo reverses the numeric order.
        Check.eq(Optional.of(new Reversed(1)),
                Solution.maxOf(Arrays.asList(new Reversed(5), new Reversed(1))),
                "uses-compareto-not-fields");

        // 10: the first of several equal maxima is returned.
        BigDecimal first = new BigDecimal("2.5");
        BigDecimal second = new BigDecimal("2.50");
        Check.eqBool(true, Solution.maxOf(Arrays.asList(first, second)).get() == first,
                "first-of-equal-maxima");

        // 11: a Set input works, not just a List.
        Check.eq(Optional.of(8),
                Solution.maxOf(new LinkedHashSet<Integer>(Arrays.asList(8, 2))), "set-input");

        // 12: negative values.
        Check.eq(Optional.of(-1), Solution.maxOf(Arrays.asList(-9, -1, -5)), "negatives");

        Check.report();
    }
}
