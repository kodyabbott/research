import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Expected allocations computed independently in Python (largest remainder, ties by lowest index):
 *   1000c 1:1:1   -> [334, 333, 333]
 *   1001c 1:1:1   -> [334, 334, 333]
 *   10c   1x7     -> [2, 2, 2, 1, 1, 1, 1]
 *   100c  1:0:1   -> [50, 0, 50]
 *   5c    2:1     -> [3, 2]
 *   1c    1:1     -> [1, 0]
 *   1234c 3:2:1   -> [617, 411, 206]
 */
public class Main {
    private static List<BigDecimal> money(String... values) {
        List<BigDecimal> out = new ArrayList<BigDecimal>();
        for (String v : values) {
            out.add(new BigDecimal(v));
        }
        return out;
    }

    private static List<Integer> ratios(int... values) {
        List<Integer> out = new ArrayList<Integer>();
        for (int v : values) {
            out.add(v);
        }
        return out;
    }

    private static void sumsExactly(String amount, List<BigDecimal> parts, String name) {
        BigDecimal total = BigDecimal.ZERO;
        for (BigDecimal part : parts) {
            total = total.add(part);
        }
        Check.eqDecimal(amount, total, name);
    }

    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqList(money("3.34", "3.33", "3.33"),
                Solution.allocate(new BigDecimal("10.00"), ratios(1, 1, 1)), "javadoc-example");

        // 2: two leftover cents go to the first two (not shown in the Javadoc).
        Check.eqList(money("3.34", "3.34", "3.33"),
                Solution.allocate(new BigDecimal("10.01"), ratios(1, 1, 1)), "two-leftover-cents");

        // 3: seven-way split of ten cents.
        Check.eqList(money("0.02", "0.02", "0.02", "0.01", "0.01", "0.01", "0.01"),
                Solution.allocate(new BigDecimal("0.10"), ratios(1, 1, 1, 1, 1, 1, 1)),
                "seven-way-split");

        // 4: a zero ratio receives nothing and takes no leftover cent.
        Check.eqList(money("0.50", "0.00", "0.50"),
                Solution.allocate(new BigDecimal("1.00"), ratios(1, 0, 1)), "zero-ratio");

        // 5: unequal ratios.
        Check.eqList(money("0.03", "0.02"),
                Solution.allocate(new BigDecimal("0.05"), ratios(2, 1)), "unequal-ratios");

        // 6: one cent, two parties: lowest index wins the tie.
        Check.eqList(money("0.01", "0.00"),
                Solution.allocate(new BigDecimal("0.01"), ratios(1, 1)), "single-cent-tie");

        // 7: a larger three-way split.
        Check.eqList(money("6.17", "4.11", "2.06"),
                Solution.allocate(new BigDecimal("12.34"), ratios(3, 2, 1)), "three-two-one");

        // 8: zero amount.
        Check.eqList(money("0.00", "0.00"),
                Solution.allocate(BigDecimal.ZERO, ratios(1, 1)), "zero-amount");

        // 9: the sum is exact, which is the point of the algorithm.
        sumsExactly("10.01", Solution.allocate(new BigDecimal("10.01"), ratios(1, 1, 1)),
                "sums-exactly");

        // 10: every returned amount has scale 2.
        Check.eqInt(2, Solution.allocate(new BigDecimal("1.00"), ratios(1, 1)).get(0).scale(),
                "scale-is-two");

        // 11-15: the rejection contract.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.allocate(null, ratios(1)), "null-amount-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.allocate(new BigDecimal("-1.00"), ratios(1)),
                "negative-amount-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.allocate(new BigDecimal("1.005"), ratios(1)),
                "three-decimals-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.allocate(new BigDecimal("1.00"), new ArrayList<Integer>()),
                "empty-ratios-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.allocate(new BigDecimal("1.00"), ratios(0, 0)),
                "zero-sum-ratios-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.allocate(new BigDecimal("1.00"), ratios(1, -1)),
                "negative-ratio-throws");

        Check.report();
    }
}
