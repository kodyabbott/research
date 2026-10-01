import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class Solution {

    public static List<String> topWords(String text, int k) {
        List<String> out = new ArrayList<String>();
        if (text == null || k <= 0) {
            return out;
        }
        Map<String, Integer> counts = new LinkedHashMap<String, Integer>();
        StringBuilder word = new StringBuilder();
        for (int i = 0; i <= text.length(); i++) {
            char c = i < text.length() ? text.charAt(i) : ' ';
            if (Character.isLetterOrDigit(c)) {
                word.append(Character.toLowerCase(c));
                continue;
            }
            if (word.length() > 0) {
                String key = word.toString();
                Integer current = counts.get(key);
                counts.put(key, current == null ? 1 : current + 1);
                word.setLength(0);
            }
        }
        List<Map.Entry<String, Integer>> entries =
                new ArrayList<Map.Entry<String, Integer>>(counts.entrySet());
        entries.sort(Comparator
                .<Map.Entry<String, Integer>, Integer>comparing(Map.Entry::getValue).reversed()
                .thenComparing(Map.Entry::getKey));
        for (int i = 0; i < Math.min(k, entries.size()); i++) {
            out.add(entries.get(i).getKey());
        }
        return out;
    }
}
