import java.util.List;
import java.util.Optional;
import java.util.function.Predicate;

public class Solution {

    public static Optional<Integer> firstMatch(List<Integer> values,
                                               Predicate<Integer> predicate) {
        if (predicate == null) {
            throw new IllegalArgumentException("predicate must not be null");
        }
        if (values == null) {
            return Optional.empty();
        }
        return values.stream()
                .filter(value -> value != null)
                .filter(predicate)
                .findFirst();
    }
}
