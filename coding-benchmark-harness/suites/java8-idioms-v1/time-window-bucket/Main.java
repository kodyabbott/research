import java.time.Instant;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;

/**
 * Expected epoch seconds computed independently in Python with zoneinfo("America/Denver"):
 *   2026-06-15 12:37 MDT  -> epoch 1781548620, bucket 1781548200
 *   2026-03-08 01:50 MST  -> epoch 1772959800, bucket 1772959500  (before spring-forward)
 *   2026-03-08 03:05 MDT  -> epoch 1772960700, bucket 1772960400  (after spring-forward)
 *   2026-11-01 01:05 (first, MDT) -> epoch 1793516700, bucket 1793516400
 */
public class Main {
    private static final ZoneId DENVER = ZoneId.of("America/Denver");

    private static LinkedHashMap<Long, Integer> map(Object... pairs) {
        LinkedHashMap<Long, Integer> out = new LinkedHashMap<Long, Integer>();
        for (int i = 0; i < pairs.length; i += 2) {
            out.put((Long) pairs[i], (Integer) pairs[i + 1]);
        }
        return out;
    }

    public static void main(String[] args) {
        // 1: a plain instant floors to its 15-minute window.
        Check.eqMap(map(1781548200L, 1),
                Solution.bucketCounts(Arrays.asList(Instant.ofEpochSecond(1781548620L)), DENVER),
                "floors-to-window");

        // 2: several instants in one window collapse to one entry.
        Check.eqMap(map(1781548200L, 3), Solution.bucketCounts(Arrays.asList(
                Instant.ofEpochSecond(1781548200L), Instant.ofEpochSecond(1781548620L),
                Instant.ofEpochSecond(1781549099L)), DENVER), "same-window-counts");

        // 3: the window start itself belongs to its own bucket.
        Check.eqMap(map(1781548200L, 1),
                Solution.bucketCounts(Arrays.asList(Instant.ofEpochSecond(1781548200L)), DENVER),
                "boundary-belongs-to-own-bucket");

        // 4: one second later than the window end starts a new bucket.
        Check.eqMap(map(1781548200L, 1, 1781549100L, 1), Solution.bucketCounts(Arrays.asList(
                Instant.ofEpochSecond(1781548620L), Instant.ofEpochSecond(1781549100L)), DENVER),
                "next-window");

        // 5: the DST spring-forward day in Denver, either side of the 02:00 gap.
        Check.eqMap(map(1772959500L, 1, 1772960400L, 1), Solution.bucketCounts(Arrays.asList(
                Instant.ofEpochSecond(1772959800L), Instant.ofEpochSecond(1772960700L)), DENVER),
                "dst-spring-forward");

        // 6: the fall-back day, where local 01:05 happens twice; epoch seconds stay unique.
        Check.eqMap(map(1793516400L, 1),
                Solution.bucketCounts(Arrays.asList(Instant.ofEpochSecond(1793516700L)), DENVER),
                "dst-fall-back");

        // 7: ascending key order regardless of input order.
        Check.eqMapOrdered(map(1781548200L, 1, 1781549100L, 1), Solution.bucketCounts(
                Arrays.asList(Instant.ofEpochSecond(1781549100L),
                        Instant.ofEpochSecond(1781548620L)), DENVER), "ascending-keys");

        // 8-9: empty and null input.
        Check.eqMap(new LinkedHashMap<Long, Integer>(),
                Solution.bucketCounts(new ArrayList<Instant>(), DENVER), "empty");
        Check.eqMap(new LinkedHashMap<Long, Integer>(),
                Solution.bucketCounts(null, DENVER), "null-list");

        // 10: null elements are ignored.
        Check.eqMap(map(1781548200L, 1), Solution.bucketCounts(
                Arrays.asList(null, Instant.ofEpochSecond(1781548620L), null), DENVER),
                "null-elements-ignored");

        // 11: UTC alignment differs from Denver alignment only by offset, so the bucket for an
        // instant already on a 15-minute boundary is the same in both zones.
        Check.eqMap(map(1781548200L, 1), Solution.bucketCounts(
                Arrays.asList(Instant.ofEpochSecond(1781548200L)), ZoneId.of("UTC")),
                "utc-zone");

        // 12: the zone contract.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.bucketCounts(new ArrayList<Instant>(), null), "null-zone-throws");

        Check.report();
    }
}
