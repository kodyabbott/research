import java.util.Collection;
import java.util.Optional;

public class Solution {

    /**
     * Returns the largest element of a collection, by natural ordering.
     *
     * The result is empty when the collection is null or has no non-null elements. Null elements
     * are ignored. When several elements compare equal to the maximum, the first such element in
     * iteration order is returned.
     *
     * Example: [3, 9, 7] returns Optional[9].
     *
     * @param values the elements to compare, may be null or contain nulls
     * @param <T>    a type comparable with itself or a supertype
     * @return the maximum, or empty
     */
    public static <T extends Comparable<? super T>> Optional<T> maxOf(Collection<T> values) {
        throw new UnsupportedOperationException("TODO");
    }
}
