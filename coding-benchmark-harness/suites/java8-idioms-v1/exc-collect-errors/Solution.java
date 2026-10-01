import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class Solution {

    public static class ValidationException extends Exception {
        private static final long serialVersionUID = 1L;
        private final List<String> errors;

        public ValidationException(List<String> errors) {
            super("validation failed with " + errors.size() + " error(s)");
            this.errors = errors;
        }

        public List<String> getErrors() {
            return errors;
        }
    }

    public static TreeMap<String, String> validate(Map<String, String> form, List<String> required)
            throws ValidationException {
        Map<String, String> values = form == null
                ? Collections.<String, String>emptyMap() : form;
        List<String> names = required == null ? Collections.<String>emptyList() : required;
        List<String> sortedNames = new ArrayList<String>(names);
        Collections.sort(sortedNames);
        List<String> errors = new ArrayList<String>();
        for (String field : sortedNames) {
            if (!values.containsKey(field)) {
                errors.add(field + " is required");
                continue;
            }
            String value = values.get(field);
            if (value == null || value.trim().isEmpty()) {
                errors.add(field + " is blank");
            }
        }
        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
        TreeMap<String, String> out = new TreeMap<String, String>();
        for (Map.Entry<String, String> entry : values.entrySet()) {
            out.put(entry.getKey(), entry.getValue() == null ? null : entry.getValue().trim());
        }
        return out;
    }
}
