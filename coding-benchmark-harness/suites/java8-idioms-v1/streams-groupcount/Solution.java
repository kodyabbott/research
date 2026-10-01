import java.util.List;
import java.util.TreeMap;
import java.util.function.Function;
import java.util.stream.Collectors;

public class Solution {

    public static TreeMap<String, Long> countByKey(List<String> records,
                                                   Function<String, String> keyExtractor) {
        if (keyExtractor == null) {
            throw new IllegalArgumentException("keyExtractor must not be null");
        }
        TreeMap<String, Long> empty = new TreeMap<String, Long>();
        if (records == null) {
            return empty;
        }
        return records.stream()
                .map(keyExtractor)
                .filter(key -> key != null)
                .collect(Collectors.groupingBy(Function.identity(), TreeMap::new,
                        Collectors.counting()));
    }
}
