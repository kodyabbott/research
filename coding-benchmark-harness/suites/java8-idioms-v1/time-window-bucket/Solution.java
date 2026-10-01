import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class Solution {

    public static LinkedHashMap<Long, Integer> bucketCounts(List<Instant> instants, ZoneId zone) {
        if (zone == null) {
            throw new IllegalArgumentException("zone must not be null");
        }
        TreeMap<Long, Integer> sorted = new TreeMap<Long, Integer>();
        if (instants != null) {
            for (Instant instant : instants) {
                if (instant == null) {
                    continue;
                }
                ZonedDateTime local = instant.atZone(zone).truncatedTo(ChronoUnit.MINUTES);
                ZonedDateTime floored = local.withMinute(local.getMinute() / 15 * 15);
                long key = floored.toEpochSecond();
                Integer current = sorted.get(key);
                sorted.put(key, current == null ? 1 : current + 1);
            }
        }
        LinkedHashMap<Long, Integer> out = new LinkedHashMap<Long, Integer>();
        for (Map.Entry<Long, Integer> entry : sorted.entrySet()) {
            out.put(entry.getKey(), entry.getValue());
        }
        return out;
    }
}
