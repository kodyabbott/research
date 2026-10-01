import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.Collections;
import java.util.Set;

public class Solution {

    public static int businessDaysBetween(LocalDate start, LocalDate end,
                                          Set<LocalDate> holidays) {
        if (start == null || end == null) {
            throw new IllegalArgumentException("start and end must not be null");
        }
        LocalDate from = start;
        LocalDate to = end;
        if (to.isBefore(from)) {
            LocalDate swap = from;
            from = to;
            to = swap;
        }
        Set<LocalDate> skip = holidays == null ? Collections.<LocalDate>emptySet() : holidays;
        int count = 0;
        for (LocalDate day = from; day.isBefore(to); day = day.plusDays(1)) {
            if (day.getDayOfWeek() == DayOfWeek.SATURDAY
                    || day.getDayOfWeek() == DayOfWeek.SUNDAY) {
                continue;
            }
            if (skip.contains(day)) {
                continue;
            }
            count++;
        }
        return count;
    }
}
