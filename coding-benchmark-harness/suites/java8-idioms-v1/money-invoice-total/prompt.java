import java.math.BigDecimal;
import java.util.List;

public class Solution {

    /** An invoice line. DO NOT MODIFY. */
    public static final class Line {
        private final int quantity;
        private final BigDecimal unitPrice;

        public Line(int quantity, BigDecimal unitPrice) {
            this.quantity = quantity;
            this.unitPrice = unitPrice;
        }

        public int quantity() {
            return quantity;
        }

        public BigDecimal unitPrice() {
            return unitPrice;
        }
    }

    /**
     * Totals an invoice.
     *
     * Each line extends to quantity * unitPrice, rounded to scale 2 with RoundingMode.HALF_EVEN
     * (banker's rounding). The line extensions are summed to a subtotal. Tax is then applied once
     * to that subtotal: tax = subtotal * taxRate, also rounded to scale 2 with HALF_EVEN. The
     * result is subtotal + tax, at scale 2.
     *
     * A null or empty lines list totals to 0.00. Null lines are ignored.
     *
     * Example: one line of 2 at 10.00 with taxRate 0 returns 20.00.
     *
     * @param lines   the invoice lines, may be null or contain nulls
     * @param taxRate the tax rate as a fraction, for example 0.0725; not negative
     * @return the invoice total at scale 2
     * @throws IllegalArgumentException if taxRate is null or negative, or a line has a negative
     *                                  quantity or a null or negative unit price
     */
    public static BigDecimal total(List<Line> lines, BigDecimal taxRate) {
        throw new UnsupportedOperationException("TODO");
    }
}
