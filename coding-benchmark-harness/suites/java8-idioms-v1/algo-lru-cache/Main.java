import java.util.Arrays;

public class Main {
    public static void main(String[] args) {
        // 1: basic put and get.
        Solution.LruCache cache = new Solution.LruCache(2);
        cache.put("a", "1");
        cache.put("b", "2");
        Check.eqStr("1", cache.get("a"), "get-hit");
        Check.eqStr(null, cache.get("zz"), "get-miss-is-null");
        Check.eqInt(2, cache.size(), "size");

        // 2: get promotes, so the un-got key is evicted (not shown in the Javadoc).
        Solution.LruCache promote = new Solution.LruCache(2);
        promote.put("a", "1");
        promote.put("b", "2");
        promote.get("a");
        promote.put("c", "3");
        Check.eqList(Arrays.asList("a", "c"), promote.keys(), "get-promotes");
        Check.eqStr(null, promote.get("b"), "lru-evicted");

        // 3: without the get, the first key is evicted instead.
        Solution.LruCache noPromote = new Solution.LruCache(2);
        noPromote.put("a", "1");
        noPromote.put("b", "2");
        noPromote.put("c", "3");
        Check.eqList(Arrays.asList("b", "c"), noPromote.keys(), "no-promotion-evicts-first");

        // 4: keys() is least-recently-used first.
        Solution.LruCache order = new Solution.LruCache(3);
        order.put("x", "1");
        order.put("y", "2");
        order.put("z", "3");
        order.get("x");
        Check.eqList(Arrays.asList("y", "z", "x"), order.keys(), "keys-lru-first");

        // 5: re-putting an existing key replaces and promotes.
        Solution.LruCache replace = new Solution.LruCache(2);
        replace.put("a", "1");
        replace.put("b", "2");
        replace.put("a", "9");
        Check.eqStr("9", replace.get("a"), "reput-replaces-value");
        Check.eqInt(2, replace.size(), "reput-does-not-grow");
        replace.put("c", "3");
        Check.eqStr(null, replace.get("b"), "reput-promoted-a-so-b-evicted");

        // 6: capacity 1 holds only the newest key.
        Solution.LruCache one = new Solution.LruCache(1);
        one.put("a", "1");
        one.put("b", "2");
        Check.eqList(Arrays.asList("b"), one.keys(), "capacity-one");
        Check.eqInt(1, one.size(), "capacity-one-size");

        // 7: a miss does not promote anything.
        Solution.LruCache miss = new Solution.LruCache(2);
        miss.put("a", "1");
        miss.put("b", "2");
        miss.get("nope");
        miss.put("c", "3");
        Check.eqList(Arrays.asList("b", "c"), miss.keys(), "miss-does-not-promote");

        // 8: capacity 0 and negative are rejected.
        Check.throwsType(IllegalArgumentException.class,
                () -> new Solution.LruCache(0), "capacity-zero-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> new Solution.LruCache(-3), "capacity-negative-throws");

        // 9: an empty cache.
        Solution.LruCache empty = new Solution.LruCache(4);
        Check.eqInt(0, empty.size(), "empty-size");
        Check.eqList(Arrays.asList(), empty.keys(), "empty-keys");

        Check.report();
    }
}
