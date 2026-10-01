import java.util.Collection;
import java.util.Optional;

public class Solution {

    public static <T extends Comparable<? super T>> Optional<T> maxOf(Collection<T> values) {
        if (values == null) {
            return Optional.empty();
        }
        T best = null;
        for (T value : values) {
            if (value == null) {
                continue;
            }
            if (best == null || value.compareTo(best) > 0) {
                best = value;
            }
        }
        return Optional.ofNullable(best);
    }
}
