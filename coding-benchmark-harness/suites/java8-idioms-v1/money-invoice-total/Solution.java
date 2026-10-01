import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

public class Solution {

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

    public static BigDecimal total(List<Line> lines, BigDecimal taxRate) {
        if (taxRate == null || taxRate.signum() < 0) {
            throw new IllegalArgumentException("taxRate must not be null or negative");
        }
        BigDecimal subtotal = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_EVEN);
        if (lines != null) {
            for (Line line : lines) {
                if (line == null) {
                    continue;
                }
                if (line.quantity() < 0 || line.unitPrice() == null
                        || line.unitPrice().signum() < 0) {
                    throw new IllegalArgumentException("invalid line");
                }
                BigDecimal extended = line.unitPrice()
                        .multiply(BigDecimal.valueOf(line.quantity()))
                        .setScale(2, RoundingMode.HALF_EVEN);
                subtotal = subtotal.add(extended);
            }
        }
        BigDecimal tax = subtotal.multiply(taxRate).setScale(2, RoundingMode.HALF_EVEN);
        return subtotal.add(tax).setScale(2, RoundingMode.HALF_EVEN);
    }
}
