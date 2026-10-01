import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class Solution {

    public static final class LruCache {
        private final LinkedHashMap<String, String> entries;

        public LruCache(int capacity) {
            if (capacity < 1) {
                throw new IllegalArgumentException("capacity must be at least 1");
            }
            final int limit = capacity;
            this.entries = new LinkedHashMap<String, String>(16, 0.75f, true) {
                private static final long serialVersionUID = 1L;

                @Override
                protected boolean removeEldestEntry(Map.Entry<String, String> eldest) {
                    return size() > limit;
                }
            };
        }

        public String get(String key) {
            return entries.get(key);
        }

        public void put(String key, String value) {
            entries.put(key, value);
        }

        public List<String> keys() {
            return new ArrayList<String>(entries.keySet());
        }

        public int size() {
            return entries.size();
        }
    }
}
