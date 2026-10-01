import java.time.LocalDate;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/** Expected values independently computed in Python (datetime + weekday()), not by Solution. */
public class Main {
    private static Set<LocalDate> set(String... dates) {
        Set<LocalDate> out = new HashSet<LocalDate>();
        for (String d : dates) {
            out.add(LocalDate.parse(d));
        }
        return out;
    }

    public static void main(String[] args) {
        LocalDate jun1 = LocalDate.parse("2026-06-01");
        LocalDate jun8 = LocalDate.parse("2026-06-08");

        // 1: the Javadoc example. Python: bdays(2026-06-01, 2026-06-08, {}) == 5
        Check.eqInt(5, Solution.businessDaysBetween(jun1, jun8, null), "javadoc-example");

        // 2: same day is zero (half-open range).
        Check.eqInt(0, Solution.businessDaysBetween(jun1, jun1, null), "same-day-zero");

        // 3: reversed order is swapped, not negative. Python: 5
        Check.eqInt(5, Solution.businessDaysBetween(jun8, jun1, null), "reversed-order");

        // 4: a mid-week holiday removes one day. Python: bdays(2026-06-29, 2026-07-06, {07-03}) == 4
        Check.eqInt(4, Solution.businessDaysBetween(LocalDate.parse("2026-06-29"),
                LocalDate.parse("2026-07-06"), set("2026-07-03")), "holiday-on-weekday");

        // 5: 2026-07-04 is a Saturday, so a holiday there changes nothing. Python: 0
        Check.eqInt(0, Solution.businessDaysBetween(LocalDate.parse("2026-07-04"),
                LocalDate.parse("2026-07-06"), set("2026-07-04")), "holiday-on-weekend");

        // 6: a Friday-to-Tuesday span skips the weekend. Python: bdays(06-05, 06-09, {}) == 2
        Check.eqInt(2, Solution.businessDaysBetween(LocalDate.parse("2026-06-05"),
                LocalDate.parse("2026-06-09"), null), "weekend-skipped");

        // 7: empty holidays set behaves like null.
        Check.eqInt(5, Solution.businessDaysBetween(jun1, jun8,
                Collections.<LocalDate>emptySet()), "empty-holidays");

        // 8: a Saturday-to-Sunday span is zero.
        Check.eqInt(0, Solution.businessDaysBetween(LocalDate.parse("2026-06-06"),
                LocalDate.parse("2026-06-07"), null), "weekend-only-span");

        // 9: every day of a full week except the weekend, across a month boundary.
        Check.eqInt(3, Solution.businessDaysBetween(LocalDate.parse("2026-06-30"),
                LocalDate.parse("2026-07-03"), null), "across-month-boundary");

        // 10-11: the null contract.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.businessDaysBetween(null, jun8, null), "null-start-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.businessDaysBetween(jun1, null, null), "null-end-throws");

        Check.report();
    }
}
