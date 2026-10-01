public class Main {
    public static void main(String[] args) {
        // 1-4: the Javadoc examples.
        Check.eqLong(123456L, Solution.parseCents("$1,234.56"), "javadoc-dollar-grouped");
        Check.eqLong(-1230L, Solution.parseCents("(12.30)"), "javadoc-parenthesized");
        Check.eqLong(-1L, Solution.parseCents("-0.01"), "javadoc-negative-cent");
        Check.eqLong(4500L, Solution.parseCents("45"), "javadoc-no-decimals");

        // 5-7: whitespace and sign placement (not shown in the Javadoc examples).
        Check.eqLong(1000L, Solution.parseCents("  10.00  "), "surrounding-whitespace");
        Check.eqLong(-500L, Solution.parseCents("$-5.00"), "minus-after-dollar");
        Check.eqLong(-500L, Solution.parseCents("-$5.00"), "minus-before-dollar");

        // 8: zero.
        Check.eqLong(0L, Solution.parseCents("0.00"), "zero");

        // 9: multiple grouping commas.
        Check.eqLong(123456789L, Solution.parseCents("$1,234,567.89"), "two-groups");

        // 10: parentheses with a dollar sign inside.
        Check.eqLong(-100L, Solution.parseCents("($1.00)"), "parenthesized-dollar");

        // 11: a large value that still fits in a long.
        Check.eqLong(100000000000L, Solution.parseCents("1000000000.00"), "large-value");

        // 12-13: null and blank.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents(null), "null-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents("   "), "blank-throws");

        // 14-19: malformed input is rejected.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents("1.5"), "one-decimal-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents("1.234"), "three-decimals-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents("1,23.00"), "bad-grouping-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents("12.30)"), "unbalanced-paren-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents("(-1.00)"), "paren-and-minus-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents("USD 1.00"), "currency-word-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseCents("1.00.00"), "two-decimal-points-throws");

        Check.report();
    }
}
