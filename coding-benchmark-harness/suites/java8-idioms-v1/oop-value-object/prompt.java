import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

public class Solution {

    /**
     * A medical record number. DO NOT MODIFY this nested class's fields or constructor;
     * implement its equals, hashCode and compareTo.
     *
     * Two Mrn values are equal when their normalized values are equal. The normalized value is
     * the raw value trimmed of leading and trailing whitespace and upper-cased using
     * Locale.ROOT. Equality must be reflexive, symmetric, consistent with hashCode, false for
     * null, and false for objects of any other type.
     *
     * Natural ordering is by normalized value, using String.compareTo. Ordering must be
     * consistent with equals.
     */
    public static final class Mrn implements Comparable<Mrn> {
        private final String raw;

        public Mrn(String raw) {
            if (raw == null) {
                throw new IllegalArgumentException("raw must not be null");
            }
            this.raw = raw;
        }

        /** The value as supplied, unchanged. */
        public String raw() {
            return raw;
        }

        /** The value used for equality and ordering: trimmed and upper-cased with Locale.ROOT. */
        public String normalized() {
            throw new UnsupportedOperationException("TODO");
        }

        @Override
        public boolean equals(Object other) {
            throw new UnsupportedOperationException("TODO");
        }

        @Override
        public int hashCode() {
            throw new UnsupportedOperationException("TODO");
        }

        @Override
        public int compareTo(Mrn other) {
            throw new UnsupportedOperationException("TODO");
        }

        @Override
        public String toString() {
            return normalized();
        }
    }

    /**
     * Returns the number of distinct Mrn values in the input, using Mrn equality.
     *
     * A null collection is treated as empty. Null elements are ignored.
     *
     * Example: ["a1", "A1 ", "b2"] has 2 distinct values.
     *
     * @param values medical record numbers, may be null or contain nulls
     * @return the count of distinct normalized values
     */
    public static int countDistinct(Collection<Mrn> values) {
        throw new UnsupportedOperationException("TODO");
    }

    /**
     * Returns the normalized values of the input sorted in natural Mrn order, with duplicates
     * removed.
     *
     * A null collection is treated as empty. Null elements are ignored.
     *
     * Example: ["b2", "a1", "A1"] returns ["A1", "B2"].
     *
     * @param values medical record numbers, may be null or contain nulls
     * @return an ascending list of distinct normalized values
     */
    public static List<String> sortedDistinct(Collection<Mrn> values) {
        throw new UnsupportedOperationException("TODO");
    }
}
