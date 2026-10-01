import java.math.BigDecimal;
import java.util.List;

public class Solution {

    /**
     * Splits a money amount across parties in the given integer ratios, in whole cents.
     *
     * The amount is first converted to whole cents; it must have at most two decimal places.
     * Each party receives floor(amountCents * ratio / totalRatio) cents, and the cents left over
     * are handed out one each, to the parties with the largest fractional remainder first. Equal
     * remainders are broken by lowest index first. The returned amounts always sum exactly to the
     * input amount.
     *
     * A ratio of zero receives nothing and never takes a leftover cent.
     *
     * Example: 10.00 split 1:1:1 returns [3.34, 3.33, 3.33].
     *
     * @param amount the total to split; at most two decimal places, not negative
     * @param ratios the weights, one per party; none negative, at least one positive
     * @return one amount per party, scale 2, summing exactly to amount
     * @throws IllegalArgumentException if amount is null or negative, has more than two decimal
     *                                  places, or ratios is null, empty, contains a negative, or
     *                                  sums to zero
     */
    public static List<BigDecimal> allocate(BigDecimal amount, List<Integer> ratios) {
        throw new UnsupportedOperationException("TODO");
    }
}
