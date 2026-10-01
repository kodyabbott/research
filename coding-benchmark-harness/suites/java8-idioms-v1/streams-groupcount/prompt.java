import java.util.List;
import java.util.TreeMap;
import java.util.function.Function;

public class Solution {

    /**
     * Counts how many records fall under each key.
     *
     * The key of a record is produced by keyExtractor. Records whose extracted key is null are
     * ignored. A null or empty records list produces an empty map. The returned map is sorted by
     * key in natural String order.
     *
     * Example: records ["ann", "abe", "bob"] with a first-letter key extractor returns
     * {"a"=2, "b"=1}.
     *
     * @param records      the records to count, may be null or contain nulls
     * @param keyExtractor produces the grouping key for a record; never null
     * @return counts per key, ascending by key
     * @throws IllegalArgumentException if keyExtractor is null
     */
    public static TreeMap<String, Long> countByKey(List<String> records,
                                                   Function<String, String> keyExtractor) {
        throw new UnsupportedOperationException("TODO");
    }
}
