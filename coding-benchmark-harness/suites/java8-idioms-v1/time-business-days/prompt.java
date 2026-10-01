import java.time.LocalDate;
import java.util.Set;

public class Solution {

    /**
     * Counts business days in the half-open range [start, end): start is counted, end is not.
     *
     * A business day is a day that is neither Saturday nor Sunday and is not in holidays. If end
     * is before start the two are swapped, so the result is never negative. If start equals end
     * the result is zero. A null holidays set is treated as empty. A holiday that falls on a
     * weekend changes nothing, since that day was already excluded.
     *
     * Example: 2026-06-01 (a Monday) to 2026-06-08 with no holidays is 5.
     *
     * @param start    the inclusive start
     * @param end      the exclusive end
     * @param holidays dates to exclude, may be null
     * @return the number of business days
     * @throws IllegalArgumentException if start or end is null
     */
    public static int businessDaysBetween(LocalDate start, LocalDate end,
                                          Set<LocalDate> holidays) {
        throw new UnsupportedOperationException("TODO");
    }
}
