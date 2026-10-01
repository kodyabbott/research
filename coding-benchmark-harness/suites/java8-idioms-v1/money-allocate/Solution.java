import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class Solution {

    public static List<BigDecimal> allocate(BigDecimal amount, List<Integer> ratios) {
        if (amount == null || amount.signum() < 0 || amount.stripTrailingZeros().scale() > 2) {
            throw new IllegalArgumentException("invalid amount: " + amount);
        }
        if (ratios == null || ratios.isEmpty()) {
            throw new IllegalArgumentException("ratios must not be null or empty");
        }
        long totalRatio = 0;
        for (Integer ratio : ratios) {
            if (ratio == null || ratio < 0) {
                throw new IllegalArgumentException("ratios must not be null or negative");
            }
            totalRatio += ratio;
        }
        if (totalRatio == 0) {
            throw new IllegalArgumentException("ratios must not sum to zero");
        }
        long cents = amount.movePointRight(2).longValueExact();
        long[] share = new long[ratios.size()];
        long[] remainder = new long[ratios.size()];
        long handed = 0;
        for (int i = 0; i < ratios.size(); i++) {
            long exact = cents * ratios.get(i);
            share[i] = exact / totalRatio;
            remainder[i] = exact % totalRatio;
            handed += share[i];
        }
        List<Integer> order = new ArrayList<Integer>();
        for (int i = 0; i < ratios.size(); i++) {
            order.add(i);
        }
        final long[] rem = remainder;
        order.sort(Comparator.<Integer, Long>comparing(i -> rem[i]).reversed()
                .thenComparing(Comparator.naturalOrder()));
        long leftover = cents - handed;
        for (int k = 0; k < leftover; k++) {
            share[order.get(k)]++;
        }
        List<BigDecimal> out = new ArrayList<BigDecimal>();
        for (long value : share) {
            out.add(BigDecimal.valueOf(value, 2));
        }
        return out;
    }
}
