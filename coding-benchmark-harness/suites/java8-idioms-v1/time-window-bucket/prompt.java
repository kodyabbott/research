import java.time.Instant;
import java.time.ZoneId;
import java.util.List;
import java.util.LinkedHashMap;

public class Solution {

    /**
     * Buckets instants into 15-minute windows and counts them.
     *
     * Each instant is floored to the start of the 15-minute window it falls in, as seen in the
     * given zone: minutes are truncated to 0, 15, 30 or 45 and seconds and nanoseconds to zero.
     * The bucket key is that window start expressed as epoch seconds, so it is unambiguous across
     * daylight-saving transitions; the zone only decides the alignment.
     *
     * The returned map is ordered by bucket key ascending. A null or empty list gives an empty map.
     * Null elements are ignored.
     *
     * Example: one instant at 12:37 in a zone whose offset is a whole number of hours falls in the
     * 12:30 bucket, so the map has one entry with count 1.
     *
     * @param instants the instants to bucket, may be null or contain nulls
     * @param zone     the zone deciding the 15-minute alignment; never null
     * @return counts per bucket start (epoch seconds), ascending
     * @throws IllegalArgumentException if zone is null
     */
    public static LinkedHashMap<Long, Integer> bucketCounts(List<Instant> instants, ZoneId zone) {
        throw new UnsupportedOperationException("TODO");
    }
}
