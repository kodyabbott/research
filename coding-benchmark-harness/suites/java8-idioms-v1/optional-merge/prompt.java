import java.util.Optional;
import java.util.function.BinaryOperator;

public class Solution {

    /**
     * Combines two Optionals with a merge function.
     *
     * When both are present, the result is Optional of the merge function applied to the two
     * values, in the order (left, right). When exactly one is present, that one is returned
     * unchanged. When neither is present, the result is empty. A null Optional argument is treated
     * as empty.
     *
     * If the merge function returns null, the result is empty.
     *
     * Example: Optional[2] and Optional[3] with addition returns Optional[5].
     *
     * @param left   the first value, may be null or empty
     * @param right  the second value, may be null or empty
     * @param merger combines two present values; never null
     * @return the combined value, or empty
     * @throws IllegalArgumentException if merger is null
     */
    public static Optional<Integer> merge(Optional<Integer> left, Optional<Integer> right,
                                          BinaryOperator<Integer> merger) {
        throw new UnsupportedOperationException("TODO");
    }
}
