import java.util.Optional;
import java.util.function.BinaryOperator;

public class Solution {

    public static Optional<Integer> merge(Optional<Integer> left, Optional<Integer> right,
                                          BinaryOperator<Integer> merger) {
        if (merger == null) {
            throw new IllegalArgumentException("merger must not be null");
        }
        Optional<Integer> a = left == null ? Optional.<Integer>empty() : left;
        Optional<Integer> b = right == null ? Optional.<Integer>empty() : right;
        if (a.isPresent() && b.isPresent()) {
            return Optional.ofNullable(merger.apply(a.get(), b.get()));
        }
        if (a.isPresent()) {
            return a;
        }
        return b;
    }
}
