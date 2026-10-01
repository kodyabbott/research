import java.util.List;
import java.util.Optional;
import java.util.function.Predicate;

public class Solution {

    /**
     * Returns the first value satisfying the predicate, in list order.
     *
     * Null elements are skipped and never passed to the predicate. A null list yields an empty
     * Optional. The returned Optional is empty when nothing matches.
     *
     * Example: [1, 2, 3, 4] with "even" returns Optional[2].
     *
     * @param values    the values to search, may be null or contain nulls
     * @param predicate the test to apply; never null
     * @return the first match, or empty
     * @throws IllegalArgumentException if predicate is null
     */
    public static Optional<Integer> firstMatch(List<Integer> values,
                                               Predicate<Integer> predicate) {
        throw new UnsupportedOperationException("TODO");
    }
}
