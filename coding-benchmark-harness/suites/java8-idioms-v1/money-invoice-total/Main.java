import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Expected values computed independently in Python (Decimal, ROUND_HALF_EVEN, quantize to 0.01):
 *   3 x 1.005 -> 3.02   (3.015 rounds to even: 3.02)
 *   1 x 2.345 -> 2.34   (ties to even: 4)
 *   1 x 2.355 -> 2.36   (ties to even: 6)
 *   7 x 0.155 -> 1.08   (1.085 -> 1.08)
 *   2 x 1.125 -> 2.25
 *   lines [3x1.005, 1x2.345, 2x10.00]: subtotal 25.36, tax@7.25% 1.84, total 27.20
 */
public class Main {
    private static Solution.Line line(int quantity, String price) {
        return new Solution.Line(quantity, new BigDecimal(price));
    }

    private static final BigDecimal ZERO_TAX = new BigDecimal("0");

    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqDecimalScaled("20.00",
                Solution.total(Arrays.asList(line(2, "10.00")), ZERO_TAX), "javadoc-example");

        // 2-3: empty and null lists.
        Check.eqDecimalScaled("0.00",
                Solution.total(new ArrayList<Solution.Line>(), ZERO_TAX), "empty-lines");
        Check.eqDecimalScaled("0.00", Solution.total(null, ZERO_TAX), "null-lines");

        // 4-8: banker's rounding per line (none of these are in the Javadoc).
        Check.eqDecimalScaled("3.02",
                Solution.total(Arrays.asList(line(3, "1.005")), ZERO_TAX), "half-even-3.015-up");
        Check.eqDecimalScaled("2.34",
                Solution.total(Arrays.asList(line(1, "2.345")), ZERO_TAX), "half-even-2.345-down");
        Check.eqDecimalScaled("2.36",
                Solution.total(Arrays.asList(line(1, "2.355")), ZERO_TAX), "half-even-2.355-up");
        Check.eqDecimalScaled("1.08",
                Solution.total(Arrays.asList(line(7, "0.155")), ZERO_TAX), "half-even-1.085-down");
        Check.eqDecimalScaled("2.25",
                Solution.total(Arrays.asList(line(2, "1.125")), ZERO_TAX), "exact-2.25");

        // 9: rounding happens per line, then the subtotal is summed.
        Check.eqDecimalScaled("25.36", Solution.total(Arrays.asList(
                line(3, "1.005"), line(1, "2.345"), line(2, "10.00")), ZERO_TAX),
                "per-line-then-sum");

        // 10: tax is applied once to the subtotal, not per line.
        Check.eqDecimalScaled("27.20", Solution.total(Arrays.asList(
                line(3, "1.005"), line(1, "2.345"), line(2, "10.00")),
                new BigDecimal("0.0725")), "tax-applied-once");

        // 11: a zero-quantity line contributes nothing.
        Check.eqDecimalScaled("10.00", Solution.total(Arrays.asList(
                line(0, "99.99"), line(1, "10.00")), ZERO_TAX), "zero-quantity");

        // 12: null lines are ignored.
        Check.eqDecimalScaled("10.00", Solution.total(Arrays.asList(
                null, line(1, "10.00"), null), ZERO_TAX), "null-line-ignored");

        // 13: the result always has scale 2, even for a whole number.
        Check.eqInt(2, Solution.total(Arrays.asList(line(1, "5")), ZERO_TAX).scale(),
                "scale-is-two");

        // 14-17: the rejection contract.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.total(Arrays.asList(line(1, "1.00")), null), "null-tax-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.total(Arrays.asList(line(1, "1.00")), new BigDecimal("-0.01")),
                "negative-tax-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.total(Arrays.asList(line(-1, "1.00")), ZERO_TAX),
                "negative-quantity-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.total(Arrays.asList(new Solution.Line(1, null)), ZERO_TAX),
                "null-price-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.total(Arrays.asList(line(1, "-2.00")), ZERO_TAX),
                "negative-price-throws");

        Check.report();
    }
}
