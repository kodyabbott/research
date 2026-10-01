import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;

public class Solution {

    public static List<String> flatten(List<List<String>> nested) {
        List<String> kept = new ArrayList<String>();
        if (nested == null) {
            return kept;
        }
        Set<String> seen = new TreeSet<String>(String.CASE_INSENSITIVE_ORDER);
        for (List<String> inner : nested) {
            if (inner == null) {
                continue;
            }
            for (String value : inner) {
                if (value == null) {
                    continue;
                }
                String trimmed = value.trim();
                if (trimmed.isEmpty()) {
                    continue;
                }
                if (seen.add(trimmed)) {
                    kept.add(trimmed);
                }
            }
        }
        List<String> out = new ArrayList<String>(kept);
        out.sort(String.CASE_INSENSITIVE_ORDER);
        return out;
    }
}
