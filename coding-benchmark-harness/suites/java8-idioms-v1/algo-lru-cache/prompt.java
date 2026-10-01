import java.util.List;

public class Solution {

    /**
     * A fixed-capacity least-recently-used cache. DO NOT MODIFY the constructor signature.
     *
     * get and put both count as uses: the most recently used key is evicted last. When a put would
     * exceed the capacity, the least recently used key is removed. Re-putting an existing key
     * replaces its value and counts as a use.
     */
    public static final class LruCache {
        /**
         * @param capacity the maximum number of entries; at least 1
         * @throws IllegalArgumentException if capacity is below 1
         */
        public LruCache(int capacity) {
            throw new UnsupportedOperationException("TODO");
        }

        /** The value for key, or null if absent. A hit counts as a use. */
        public String get(String key) {
            throw new UnsupportedOperationException("TODO");
        }

        /** Stores a value, evicting the least recently used key if the cache is full. */
        public void put(String key, String value) {
            throw new UnsupportedOperationException("TODO");
        }

        /** The keys currently held, least recently used first. */
        public List<String> keys() {
            throw new UnsupportedOperationException("TODO");
        }

        /** How many entries are held. */
        public int size() {
            throw new UnsupportedOperationException("TODO");
        }
    }
}
